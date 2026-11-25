"""Çıkarım ajanı testleri. Ollama, Neo4j ve Docker gerektirmez."""
import json

import pytest

from src.cikarim.servis import GecersizMetin, cikar_ve_yaz, metin_temizle

METIN = "Koç Holding, Tüpraş şirketinin yüzde 51 hissesine sahiptir ve şirketi yönetir."
CEVAP = {"entities": [{"label": "Company", "name": "Koç Holding"}, {"label": "Company", "name": "Tüpraş"}],
         "relations": [{"type": "SUBSIDIARY_OF", "source": "Tüpraş", "target": "Koç Holding",
                        "evidence": "Koç Holding, Tüpraş şirketinin yüzde 51 hissesine sahiptir", "confidence": 0.9},
                       {"type": "SUBSIDIARY_OF", "source": "Tüpraş", "target": "Koç Holding",
                        "evidence": "bu cümle metinde hiç yok", "confidence": 0.9}]}


def gen_dogru(prompt):
    return json.dumps(CEVAP)


def test_metin_siniri():
    with pytest.raises(GecersizMetin):
        metin_temizle("kısa")
    with pytest.raises(GecersizMetin):
        metin_temizle("x" * 200_001)
    assert metin_temizle("  " + METIN + "  ") == METIN


def test_cikar_ve_yaz_kanitsiz_iliskiyi_atar_ve_yazar():
    yazilan = []
    s = cikar_ve_yaz(METIN, "k1", gen_dogru, lambda q, p: yazilan.append(p), "llama3.1:8b")
    assert s["varlik"] == 2 and s["iliski"] == 1 and s["atilan_iliski"] == 1
    assert s["yazildi"] is True and s["hatali_parca"] == 0 and yazilan
    assert any(p.get("source_id") == "k1" for p in yazilan)


def test_kuru_calistirma_yazmaz():
    yazilan = []
    s = cikar_ve_yaz(METIN, "k1", gen_dogru, None, "m")
    assert s["yazildi"] is False and s["varlik"] == 2 and yazilan == []


def test_model_hep_bozuk_donerse_yazmaz_ve_hatayi_sayar():
    yazilan = []
    s = cikar_ve_yaz(METIN, "k2", lambda p: "json değil", lambda q, p: yazilan.append(p), "m")
    assert s["yazildi"] is False and s["hatali_parca"] >= 1 and s["varlik"] == 0 and yazilan == []


def test_cikarim_servisi_uc_noktalari():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from src.cikarim.main import uygulama_olustur

    yazilan = []
    c = TestClient(uygulama_olustur(lambda: (gen_dogru, lambda q, p: yazilan.append(p), "m"), token="gizli"))
    govde = {"kaynak_id": "k1", "metin": METIN}
    assert c.get("/saglik").json()["durum"] == "ok"
    assert c.post("/cikar", json=govde).status_code == 401
    assert c.post("/cikar", json=govde, headers={"X-Internal-Token": "yanlis"}).status_code == 401
    ok = c.post("/cikar", json=govde, headers={"X-Internal-Token": "gizli"})
    assert ok.status_code == 200 and ok.json()["iliski"] == 1 and ok.json()["yazildi"] is True and yazilan
    n = len(yazilan)
    kuru = c.post("/cikar", json={**govde, "yaz": False}, headers={"X-Internal-Token": "gizli"})
    assert kuru.json()["yazildi"] is False and len(yazilan) == n
    assert c.post("/cikar", json={"kaynak_id": "k", "metin": "kısa"}, headers={"X-Internal-Token": "gizli"}).status_code == 422
