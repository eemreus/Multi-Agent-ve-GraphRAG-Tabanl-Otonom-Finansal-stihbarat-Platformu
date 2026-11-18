"""Vektör RAG testleri: Ollama gerekmez, sahte embed ve generate kullanılır."""
import json
import re
import zlib

from src.olcum.run import evaluate
from src.rag import vektor


def sahte_embed(metinler):
    """Kelime torbası vektörü: ortak kelimesi çok olan metinler birbirine yakın çıkar."""
    out = []
    for m in metinler:
        v = [0.0] * 256
        for kelime in re.findall(r"\w+", m.lower()):
            v[zlib.crc32(kelime.encode()) % 256] += 1.0
        out.append(v)
    return out


SAYFALAR = {
    "a1": "Pegasus Hava Yolları'nın çoğunluk hissedarı Esas Holding'dir. Pay oranı yüzde 52,81'dir.",
    "b2": "Türk Hava Yolları yönetim kurulu başkanlığına Murat Şeker atandı.",
    "c3": "Koç Holding Tüpraş hissesini sattı.",
}


def kur(tmp_path):
    return vektor.Indeks.kur(SAYFALAR, embed=sahte_embed, onbellek=tmp_path / "indeks.json")


def test_parcala_kaynak_numarasi_tutar():
    p = vektor.parcala({"x": "Birinci paragraf.\n\nİkinci paragraf."}, boy=20)
    assert {q.source_id for q in p} == {"x"}
    assert [q.no for q in p] == list(range(len(p)))


def test_ara_ilgili_sayfayi_getirir(tmp_path):
    idx = kur(tmp_path)
    assert idx.ara("Pegasus çoğunluk hissedarı kimdir", k=1)[0].source_id == "a1"
    assert idx.ara("THY yönetim kurulu başkanı Şeker", k=1)[0].source_id == "b2"


def test_onbellek_ikinci_seferde_embed_cagirmaz(tmp_path):
    kur(tmp_path)
    cagri = []

    def sayan(m):
        cagri.append(len(m))
        return sahte_embed(m)

    vektor.Indeks.kur(SAYFALAR, embed=sayan, onbellek=tmp_path / "indeks.json")
    assert cagri == []


def test_cevapla_sure_ve_kaynak_doner(tmp_path):
    idx = kur(tmp_path)
    v = vektor.cevapla("Esas Holding payı nedir", idx, generate=lambda p: "yüzde 52,81", k=2)
    assert v["answer"] == "yüzde 52,81" and v["latency_ms"] >= 0 and "a1" in v["retrieved"]


def test_sorulari_yukle_bom_ve_kaynaklar(tmp_path):
    f = tmp_path / "s.csv"
    f.write_text("﻿no;yazar;tur;soru;cevap;kanit_1;kaynak_1;kanit_2;kaynak_2;kanit_3;kaynak_3;grup;kontrol_eden;kontrol_sonucu;not\n"
                 "S01;Sıla;iki;Soru?;Cevap;k1;a1;k2;b2;;;g;;;\n", encoding="utf-8")
    s = vektor.sorulari_yukle(f)
    assert s == [{"id": "S01", "tur": "iki", "soru": "Soru?", "gold": "Cevap", "kaynaklar": ["a1", "b2"]}]


def test_degerlendir_olcum_koduyla_uyumlu(tmp_path):
    idx = kur(tmp_path)
    sorular = [{"id": "S01", "tur": "tek", "soru": "Pegasus çoğunluk hissedarı", "gold": "Esas Holding", "kaynaklar": ["a1"]}]
    sonuc = vektor.degerlendir(sorular, idx, generate=lambda p: "Esas Holding", k=2)
    assert sonuc["questions"][0]["kaynak_isabeti"] == "1/1"
    # Emre'nin ölçüm kodu graph+vector bekler: graph yerine vector'ü kopyalayıp çalıştır
    q = sonuc["questions"][0]
    q["graph"] = json.loads(json.dumps(q["vector"]))
    sonuc["sources"] = SAYFALAR
    assert "F1" in evaluate(sonuc)
