"""40 test sorusunu GraphRAG ile cevaplar ve src.olcum.run biçiminde sonuç yazar.
Kullanım: python -m src.graphrag.degerlendir [--limit 5]  ->  results/graphrag.json"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

from src.graf.extractor import ollama_generate
from src.graf.writer import neo4j_reader, neo4j_runner

from .pipeline import cevapla


def sorular() -> list[dict]:
    return list(csv.DictReader(Path("data/test_seti/sorular.csv").open(encoding="utf-8-sig"), delimiter=";"))


def kaynak_metinleri() -> dict[str, str]:
    manifest = json.loads(Path("data/test_seti/manifest.json").read_text(encoding="utf-8"))["sayfalar"]
    return {p["id"]: next(Path("data/ham").glob(f"*/{p['id']}.txt")).read_text(encoding="utf-8") for p in manifest}


def sayfa_okuyucu():
    onbellek: dict = {}

    def oku(sid: str):
        if sid not in onbellek:
            f = next(Path("data/ham").glob(f"*/{sid}.txt"), None)
            onbellek[sid] = f.read_text(encoding="utf-8") if f else None
        return onbellek[sid]
    return oku


def calistir(query, generate, qs: list[dict], sayfa_metni=None) -> dict:
    sonuc = []
    for r in qs:
        s = cevapla(query, r["soru"], generate, sayfa_metni)
        sonuc.append({"id": r["no"], "tur": r["tur"], "gold": r["cevap"],
                      "graph": {"answer": s.cevap, "latency_ms": s.gecikme_ms, "citations": s.atiflar,
                                "kanit_sayisi": s.kanit_sayisi, "atilan_atif": s.atilan_atif}})
    return {"questions": sonuc}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int); a = ap.parse_args(argv)
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    gen = lambda p: ollama_generate(p, model, os.getenv("OLLAMA_URL", "http://localhost:11434"))
    _, driver = neo4j_runner(os.getenv("NEO4J_URI", "bolt://localhost:7687"), os.getenv("NEO4J_USER", "neo4j"),
                             os.getenv("NEO4J_PASSWORD", "paragoz-dev-sifre"))
    out = calistir(neo4j_reader(driver), gen, sorular()[: a.limit], sayfa_okuyucu())
    out["sources"] = kaynak_metinleri()
    Path("results").mkdir(exist_ok=True)
    Path("results/graphrag.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out['questions'])} soru yazıldı: results/graphrag.json")
    driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
