"""Telemetri (agent_logs) ve soru-cevap önbelleği testleri. Veritabanı ya da Redis gerektirmez."""
import json

import pytest

from src.api.onbellek import BellekOnbellek, RedisOnbellek, onbellek_anahtari
from src.api.servis import SorServisi
from src.api.telemetri import EKLE, AgentLogYazici, rapor
from src.graphrag.pipeline import Sonuc


def sonuc(cevap="Enerjisa"):
    return Sonuc(cevap, [{"source_id": "s1", "quote": "alıntı"}], 5.0, 3, [], 1)


# --- anahtar ---------------------------------------------------------------

def test_anahtar_bosluk_ve_harf_farkini_yok_sayar():
    assert onbellek_anahtari("Murat  Pınar kimdir?") == onbellek_anahtari(" murat pınar kimdir? ")
    assert onbellek_anahtari("soru bir") != onbellek_anahtari("soru iki")
    assert onbellek_anahtari("soru", "llama:v1") != onbellek_anahtari("soru", "qwen:v1")  # sürüm değişince eski cevap geçmez


# --- bellek önbelleği ------------------------------------------------------

def test_bellek_onbellegi_ttl_ve_kopya():
    t = [0.0]
    o = BellekOnbellek(ttl_sn=10, saat=lambda: t[0])
    o.set("a", {"cevap": "x", "atiflar": []})
    ilk = o.get("a")
    ilk["cevap"] = "bozuldu"                      # çağıranın değişikliği önbelleği bozmaz
    assert o.get("a")["cevap"] == "x"
    t[0] = 10
    assert o.get("a") is None                     # süre doldu
    assert o.get("yok") is None


def test_bellek_onbellegi_en_eskiyi_atar():
    t = [0.0]
    o = BellekOnbellek(ttl_sn=100, maks=2, saat=lambda: t[0])
    o.set("a", {"n": 1}); t[0] = 1
    o.set("b", {"n": 2}); t[0] = 2
    o.set("c", {"n": 3})
    assert o.get("a") is None and o.get("b") and o.get("c")


# --- Redis önbelleği (sahte istemci) ---------------------------------------

class SahteRedis:
    def __init__(self):
        self.veri, self.ex = {}, {}

    def get(self, k):
        return self.veri.get(k)

    def set(self, k, v, ex=None):
        self.veri[k], self.ex[k] = v, ex


def test_redis_onbellegi_json_ve_ttl():
    r = SahteRedis()
    o = RedisOnbellek(r, ttl_sn=120)
    o.set("k", {"cevap": "300 milyon Euro", "atiflar": []})
    assert list(r.veri) == ["paragoz:sor:k"] and r.ex["paragoz:sor:k"] == 120
    assert o.get("k") == {"cevap": "300 milyon Euro", "atiflar": []}   # Türkçe karakter sağlam
    assert o.get("yok") is None


def test_redis_hatasi_istegi_bozmaz():
    class Bozuk:
        def get(self, k): raise ConnectionError("redis yok")
        def set(self, k, v, ex=None): raise ConnectionError("redis yok")

    o = RedisOnbellek(Bozuk())
    assert o.get("k") is None          # okuma hatası: önbellek boş sayılır
    o.set("k", {"a": 1})               # yazma hatası: sessizce geçer


# --- servis + önbellek -----------------------------------------------------

def test_ayni_soru_ikinci_kez_modele_gitmez():
    cagri, olaylar = [], []

    def fn(soru):
        cagri.append(soru)
        return sonuc()

    s = SorServisi(fn, telemetri=olaylar.append, onbellek=BellekOnbellek())
    ilk = s.sor("Murat Pınar kimdir?")
    ikinci = s.sor("  murat pınar   kimdir? ")
    assert len(cagri) == 1                                   # model yalnızca bir kez çağrıldı
    assert ilk["onbellek"] is False and ikinci["onbellek"] is True
    assert ikinci["cevap"] == ilk["cevap"] and ikinci["atiflar"] == ilk["atiflar"]
    assert [o["event_type"] for o in olaylar] == ["sor", "sor_onbellek"]
    assert "Murat" not in json.dumps(olaylar, ensure_ascii=False)   # ham soru loga girmez
    assert olaylar[0]["payload"]["soru_ozeti"] == olaylar[1]["payload"]["soru_ozeti"]


def test_hatali_cevap_onbellege_girmez():
    durum = {"hata": True}

    def fn(soru):
        if durum["hata"]:
            raise RuntimeError("model yok")
        return sonuc()

    s = SorServisi(fn, onbellek=BellekOnbellek())
    with pytest.raises(RuntimeError):
        s.sor("geçerli bir soru")
    durum["hata"] = False
    assert s.sor("geçerli bir soru")["onbellek"] is False    # hata saklanmadı, model yeniden çağrıldı


def test_surum_degisince_onbellek_gecmez():
    o = BellekOnbellek()
    s1 = SorServisi(lambda q: sonuc("eski"), onbellek=o, surum="llama:v1")
    s2 = SorServisi(lambda q: sonuc("yeni"), onbellek=o, surum="llama:v2")
    s1.sor("aynı soru burada")
    assert s2.sor("aynı soru burada")["cevap"] == "yeni"


def test_onbellek_yokken_eski_davranis():
    y = SorServisi(lambda q: sonuc()).sor("geçerli bir soru")
    assert y["onbellek"] is False and y["gecikme_ms"] >= 0


# --- telemetri -------------------------------------------------------------

def test_agent_log_yazici_alanlari_esler():
    kayit = []
    AgentLogYazici(lambda sql, p: kayit.append((sql, p)))(
        {"agent_name": "graphrag", "event_type": "sor", "latency_ms": 1234, "error_code": None,
         "payload": {"soru_ozeti": "abc"}})
    sql, p = kayit[0]
    assert sql == EKLE and "agent_logs" in sql and "CAST(:payload AS jsonb)" in sql
    assert p["latency_ms"] == 1234 and p["event_type"] == "sor" and p["error_code"] is None
    assert json.loads(p["payload"]) == {"soru_ozeti": "abc"}


def test_telemetri_hatasi_istegi_bozmaz():
    def bozuk(sql, p):
        raise ConnectionError("veritabanı yok")

    s = SorServisi(lambda q: sonuc(), telemetri=AgentLogYazici(bozuk))
    assert s.sor("geçerli bir soru")["cevap"] == "Enerjisa"   # yazma çöktü ama kullanıcı cevabını aldı


def test_servis_telemetri_olay_alanlari():
    olaylar = []
    SorServisi(lambda q: sonuc(), telemetri=olaylar.append).sor("geçerli bir soru")
    o = olaylar[0]
    assert o["agent_name"] == "graphrag" and o["event_type"] == "sor"
    assert isinstance(o["latency_ms"], int) and o["error_code"] is None


def test_rapor_yuvarlar_ve_sorguyu_parametreyle_calistirir():
    gelen = []

    def sorgula(sql, p):
        gelen.append((sql, p))
        return [{"model_istegi": 40, "onbellek_isabeti": 10, "hata": 1, "p50_ms": 8100.04, "p95_ms": 27123.96}]

    r = rapor(sorgula, saat=6)
    assert r["p95_ms"] == 27124.0 and r["model_istegi"] == 40 and r["onbellek_isabeti"] == 10
    assert gelen[0][1] == {"saat": 6} and "percentile_cont(0.95)" in gelen[0][0]
    assert rapor(lambda s, p: [])  == {}                       # kayıt yoksa boş rapor


def test_atifsiz_ya_da_kanit_yok_cevabi_onbellege_girmez():
    cagri = []

    def fn(q):
        cagri.append(q)
        return Sonuc("Kanıt yok", [], 5.0, 0, [], 0) if len(cagri) == 1 else Sonuc("Enerjisa", [], 5.0, 3, [], 3)
    s = SorServisi(fn, onbellek=BellekOnbellek())
    s.sor("geçerli bir soru"); s.sor("geçerli bir soru"); s.sor("geçerli bir soru")
    assert len(cagri) == 3                     # üçü de modele gitti, kötü cevap saklanmadı
