"""Gateway ile GraphRAG ajan servisi arasındaki HTTP sözleşmesi. Neo4j, Ollama ve Docker gerektirmez."""
import pytest

httpx = pytest.importorskip("httpx")

from src.api.ajan_istemci import AjanHatasi, AjanIstemcisi, AjanZamanAsimi  # noqa: E402
from src.graphrag.pipeline import Sonuc  # noqa: E402


def istemci(isleyici) -> AjanIstemcisi:
    http = httpx.Client(base_url="http://ajan", transport=httpx.MockTransport(isleyici))
    return AjanIstemcisi("http://ajan", "gizli", istemci=http)


def test_istemci_sonuca_cevirir_ve_token_gonderir():
    gorulen = {}

    def isleyici(istek):
        gorulen["token"] = istek.headers["x-internal-token"]
        gorulen["yol"] = istek.url.path
        return httpx.Response(200, json={"cevap": "Enerjisa", "atiflar": [{"source_id": "s1", "quote": "alıntı"}],
                                         "atilan_atif": 1, "kanit_sayisi": 4, "gecikme_ms": 12.5})
    s = istemci(isleyici)("Enerjisa'nın sahibi kim?")
    assert isinstance(s, Sonuc) and s.cevap == "Enerjisa" and s.atilan_atif == 1 and s.kanit_sayisi == 4
    assert s.atiflar == [{"source_id": "s1", "quote": "alıntı"}]
    assert gorulen == {"token": "gizli", "yol": "/cevapla"}


def test_istemci_hatalari_ayirir():
    def zaman_asimi(istek):
        raise httpx.ReadTimeout("yavaş", request=istek)

    def baglanamadi(istek):
        raise httpx.ConnectError("kapalı", request=istek)
    with pytest.raises(AjanZamanAsimi):
        istemci(zaman_asimi)("soru metni")
    with pytest.raises(AjanHatasi) as e:
        istemci(baglanamadi)("soru metni")
    assert not isinstance(e.value, AjanZamanAsimi)
    with pytest.raises(AjanHatasi):
        istemci(lambda istek: httpx.Response(500))("soru metni")


def test_ortamdan_agent_url_yoksa_none(monkeypatch):
    monkeypatch.delenv("AGENT_URL", raising=False)
    assert AjanIstemcisi.ortamdan() is None
    monkeypatch.setenv("AGENT_URL", "http://graphrag-agent:8001")
    assert AjanIstemcisi.ortamdan() is not None


def test_ajan_servisi_token_ister_ve_cevap_verir():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from src.agent.main import uygulama_olustur

    c = TestClient(uygulama_olustur(lambda soru: Sonuc("Cevap", [{"source_id": "s", "quote": "q"}], 3.0, 2, [], 1), token="gizli"))
    assert c.get("/saglik").json()["durum"] == "ok"
    assert c.post("/cevapla", json={"soru": "test sorusu"}).status_code == 401
    assert c.post("/cevapla", json={"soru": "test sorusu"}, headers={"X-Internal-Token": "yanlis"}).status_code == 401
    ok = c.post("/cevapla", json={"soru": "test sorusu"}, headers={"X-Internal-Token": "gizli"})
    assert ok.status_code == 200 and ok.json()["cevap"] == "Cevap" and ok.json()["atilan_atif"] == 1
    assert c.post("/cevapla", json={"soru": "ab"}, headers={"X-Internal-Token": "gizli"}).status_code == 422


def test_ajan_token_tanimsizsa_kapali():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from src.agent.main import uygulama_olustur

    c = TestClient(uygulama_olustur(lambda soru: Sonuc("x", [], 1.0, 0), token=""))
    assert c.post("/cevapla", json={"soru": "test sorusu"}, headers={"X-Internal-Token": ""}).status_code == 401


def test_gateway_ajan_hatasini_502_504_yapar():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from src.api.guvenlik import ApiAnahtarlari, HizSiniri
    from src.api.main import uygulama_olustur
    from src.api.servis import SorServisi

    def kapali(soru):
        raise AjanHatasi("kapalı")

    def yavas(soru):
        raise AjanZamanAsimi("yavaş")
    h = {"X-API-Key": "a"}
    for fn, kod in ((kapali, 502), (yavas, 504)):
        c = TestClient(uygulama_olustur(SorServisi(fn), ApiAnahtarlari(["a"]), HizSiniri(maks=9, pencere_sn=60)))
        assert c.post("/sor", json={"soru": "test sorusu"}, headers=h).status_code == kod
