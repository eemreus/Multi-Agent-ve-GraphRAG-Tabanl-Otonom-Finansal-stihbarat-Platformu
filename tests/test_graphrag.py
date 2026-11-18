import json

from src.graphrag.pipeline import cevapla, kanit_metni
from src.olcum.run import birlestir, evaluate

SATIR = {"a": "Koç Holding", "bas": "Koç Holding", "rel": "SUBSIDIARY_OF", "son": "Tüpraş",
         "evidence": "Tüpraş, Koç Holding'in bağlı ortaklığıdır.", "source_ids": ["p1"], "conf": 0.9}


def fake_query(cypher, params=None):
    if "normalized_name" in cypher and "RETURN n.id" in cypher:
        return [{"id": "com_1", "name": "Koç Holding"}]
    return [SATIR]


def test_cevap_ve_atif():
    def gen(p):
        if "varliklar" in p:
            return json.dumps({"varliklar": ["Koç Holding"]})
        return json.dumps({"cevap": "Tüpraş", "atiflar": [{"source_id": "p1", "quote": SATIR["evidence"]}]})
    s = cevapla(fake_query, "Koç Holding'in bağlı ortaklığı hangisidir?", gen)
    assert s.cevap == "Tüpraş" and len(s.atiflar) == 1 and s.atilan_atif == 0 and s.gecikme_ms >= 0


def test_uydurma_atif_elenir():
    def gen(p):
        if "varliklar" in p:
            return json.dumps({"varliklar": ["Koç Holding"]})
        return json.dumps({"cevap": "Tüpraş", "atiflar": [{"source_id": "p1", "quote": "uydurma cümle"},
                                                          {"source_id": "p9", "quote": SATIR["evidence"]}]})
    s = cevapla(fake_query, "Koç Holding?", gen)
    assert s.atiflar == [] and s.atilan_atif == 2


def test_kanit_yoksa():
    s = cevapla(lambda c, p=None: [], "Bilinmeyen Şirket nedir?", lambda p: json.dumps({"varliklar": ["Bilinmeyen Şirket"]}))
    assert s.cevap == "Kanıt yok" and s.kanit_sayisi == 0


def test_bozuk_json_dayanikli():
    s = cevapla(fake_query, "Koç Holding?", lambda p: "bu json değil")
    assert isinstance(s.cevap, str)


def test_kanit_metni():
    assert "[p1]" in kanit_metni([SATIR])


def test_birlestir_iki_dosya():
    g = {"questions": [{"id": "Q1", "gold": "Tüpraş", "graph": {"answer": "Tüpraş", "latency_ms": 900, "citations": []}}],
         "sources": {"p1": "x"}}
    v = {"questions": [{"id": "Q1", "vector": {"answer": "Arçelik", "latency_ms": 500}}]}
    t = evaluate(birlestir([g, v]))
    assert "Karşılandı" in t
