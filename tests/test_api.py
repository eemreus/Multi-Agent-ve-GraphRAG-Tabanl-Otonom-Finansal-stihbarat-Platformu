import pytest

from src.api.guvenlik import ApiAnahtarlari, HizSiniri
from src.api.servis import GecersizSoru, SorServisi, soru_temizle
from src.graphrag.pipeline import Sonuc


def test_anahtar_dogrulama():
    a = ApiAnahtarlari(["gizli1", "gizli2"])
    assert a.gecerli("gizli1") and a.gecerli("gizli2")
    assert not a.gecerli("yanlis") and not a.gecerli("") and not a.gecerli(None)
    assert not ApiAnahtarlari([]).gecerli("gizli1")  # anahtar tanımlı değilse kimse giremez


def test_anahtarlar_ortamdan(monkeypatch):
    monkeypatch.setenv("API_KEYS", " a1 , b2 ,")
    a = ApiAnahtarlari.ortamdan()
    assert a.gecerli("a1") and a.gecerli("b2") and not a.gecerli("c3")


def test_hiz_siniri_kayan_pencere():
    t = [0.0]
    s = HizSiniri(maks=2, pencere_sn=10, saat=lambda: t[0])
    assert s.izin("k") == (True, 0.0)
    t[0] = 1
    assert s.izin("k")[0]
    t[0] = 2
    izinli, bekle = s.izin("k")
    assert not izinli and 8 <= bekle <= 8.1       # ilk istek 10. saniyede pencereden çıkar
    assert s.izin("baska")[0]                      # sınır anahtar başınadır
    t[0] = 10.5
    assert s.izin("k")[0]                          # pencere kaydı, yeniden izin


def test_soru_temizle():
    assert soru_temizle("  merhaba \n dünya ") == "merhaba dünya"
    for kotu in ("", "  ", "ab", "x" * 501, None):
        with pytest.raises(GecersizSoru):
            soru_temizle(kotu)


def test_servis_cevap_ve_telemetri():
    olaylar = []
    servis = SorServisi(lambda soru: Sonuc("Enerjisa", [{"source_id": "s1", "quote": "alıntı"}], 5.0, 3, [], 1),
                        telemetri=olaylar.append)
    y = servis.sor("Murat Pınar kimdir?")
    assert y["cevap"] == "Enerjisa" and y["atilan_atif"] == 1 and y["kanit_sayisi"] == 3
    assert y["gecikme_ms"] >= 0
    assert olaylar[0]["event_type"] == "sor" and olaylar[0]["error_code"] is None


def test_servis_hata_telemetriye_yazilir():
    olaylar = []

    def bozuk(soru):
        raise RuntimeError("model yok")

    with pytest.raises(RuntimeError):
        SorServisi(bozuk, telemetri=olaylar.append).sor("geçerli bir soru")
    assert olaylar[0]["error_code"] == "RuntimeError"


def test_fastapi_uc_noktalari():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from src.api.main import uygulama_olustur

    servis = SorServisi(lambda soru: Sonuc("Cevap", [], 1.0, 1))
    app = uygulama_olustur(servis, ApiAnahtarlari(["anahtar"]), HizSiniri(maks=2, pencere_sn=60))
    c = TestClient(app)
    assert c.get("/saglik").json() == {"durum": "ok"}
    assert c.post("/sor", json={"soru": "test sorusu"}).status_code == 401
    assert c.post("/sor", json={"soru": "test sorusu"}, headers={"X-API-Key": "yanlis"}).status_code == 401
    ok = c.post("/sor", json={"soru": "test sorusu"}, headers={"X-API-Key": "anahtar"})
    assert ok.status_code == 200 and ok.json()["cevap"] == "Cevap"
    assert c.post("/sor", json={"soru": "ab"}, headers={"X-API-Key": "anahtar"}).status_code == 422
    assert c.post("/sor", json={"soru": "test sorusu"}, headers={"X-API-Key": "anahtar"}).status_code == 429
    assert "/sor" in c.get("/openapi.json").json()["paths"]
