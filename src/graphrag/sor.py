"""Demo için tek soru sorar ve cevabı atıflarıyla ekrana yazar.
Kullanım:
  python -m src.graphrag.sor --no K10
  python -m src.graphrag.sor "Soru metni"
"""
from __future__ import annotations

import argparse
import json
import os

from src.graf.extractor import ollama_generate
from src.graf.writer import neo4j_reader, neo4j_runner

from .degerlendir import sayfa_okuyucu, sorular
from .pipeline import cevapla


def soru_metni(soru: str | None, no: str | None, liste: list[dict] | None = None) -> str:
    """--no verilirse test setindeki soruyu, yoksa verilen metni döndürür."""
    if no:
        for r in (liste if liste is not None else sorular()):
            if r["no"] == no:
                return r["soru"]
        raise SystemExit(f"Test setinde {no} numaralı soru yok.")
    if not soru:
        raise SystemExit("Soru metni ya da --no verin.")
    return soru


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("soru", nargs="?")
    ap.add_argument("--no", help="test seti soru numarası, örn. K10")
    a = ap.parse_args(argv)
    metin = soru_metni(a.soru, a.no)
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    gen = lambda p: ollama_generate(p, model, os.getenv("OLLAMA_URL", "http://localhost:11434"))
    _, driver = neo4j_runner(os.getenv("NEO4J_URI", "bolt://localhost:7687"), os.getenv("NEO4J_USER", "neo4j"),
                             os.getenv("NEO4J_PASSWORD", "paragoz-dev-sifre"))
    s = cevapla(neo4j_reader(driver), metin, gen, sayfa_okuyucu())
    print(f"SORU: {metin}\n")
    print(f"CEVAP: {s.cevap}\n")
    print("ATIFLAR:")
    print(json.dumps(s.atiflar, ensure_ascii=False, indent=1))
    print(f"\nSüre: {s.gecikme_ms / 1000:.1f} sn | atılan (doğrulanamayan) atıf: {s.atilan_atif}")
    driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
