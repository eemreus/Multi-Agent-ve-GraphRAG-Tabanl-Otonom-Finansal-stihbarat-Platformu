import json

from src.graphrag.pipeline import cevapla, kanit_metni
from src.olcum.run import birlestir, evaluate

SATIR = {"a": "Koç Holding", "bas": "Koç Holding", "rel": "SUBSIDIARY_OF", "son": "Tüpraş",
         "evidence": "Tüpraş, Koç Holding'in bağlı ortaklığıdır.", "source_ids": ["p1"], "conf": 0.9}


def fake_query(cypher, params=None):
    if "normalized_name" in cypher and "RETURN n.id" in cypher:
        return [{"id": "com_1", "name": "Koç Holding"}]
    if "AS sid" in cypher:
        return [{"sid": "p1", "w": 10}]
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


SAYFA = "Koç Holding hakkında genel bilgi. Tüpraş hissesinin yüzde 51'i Koç Holding'e aittir. Başka bir cümle."


def test_pasaj_graf_ile_bulunur_ve_atif_sayfadan_dogrulanir():
    from src.graphrag.pipeline import pasaj_sec, sayfa_adaylari
    assert sayfa_adaylari(fake_query, ["com_1"]) == ["p1"]
    p = pasaj_sec("Tüpraş hissesinin yüzde kaçı Koç Holding'e aittir?", ["p1"], lambda sid: SAYFA)
    assert p and p[0][0] == "p1"

    def gen(prompt):
        if "varliklar" in prompt:
            return json.dumps({"varliklar": ["Koç Holding"]})
        assert "yüzde 51" in prompt  # pasaj modele gitti
        return json.dumps({"cevap": "%51", "atiflar": [{"source_id": "p1", "quote": "Tüpraş hissesinin yüzde 51'i Koç Holding'e aittir."},
                                                      {"source_id": "p1", "quote": "bu cümle sayfada yok hiç"}]})
    s = cevapla(fake_query, "Tüpraş hissesinin yüzde kaçı Koç Holding'e aittir?", gen, lambda sid: SAYFA)
    assert s.cevap == "%51" and len(s.atiflar) == 1 and s.atilan_atif == 1


def test_iliski_sirala_ilgiliyi_one_alir():
    from src.graphrag.pipeline import iliski_sirala
    a = {**SATIR, "evidence": "Hiç ilgisiz cümle burada.", "bas": "X", "son": "Y", "conf": 0.99}
    b = {**SATIR, "evidence": "Tüpraş hissesinin yüzde 51'i Koç Holding'e aittir."}
    assert iliski_sirala([a, b], "Tüpraş hissesi yüzde kaç?", n=1)[0] is b
