"""Künyesi olan sayfaları işler: metin -> çıkarım -> (önbellek) -> Neo4j. source_id = künye id.

Kullanım:
  python -m src.graf.ingest --test-seti            # yalnızca dondurulmuş 40 sayfa
  python -m src.graf.ingest --sirket hepsi         # 157 sayfanın tamamı
  python -m src.graf.ingest --test-seti --yaz-yok  # sadece çıkar ve önbelleğe al
Çıkarım sonuçları data/cikarim/<id>.json içinde önbelleğe alınır; yeniden çalıştırmada model çağrılmaz."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .extractor import extract_document, ollama_generate
from .schema import Extraction
from .writer import apply_schema, neo4j_runner, write_extraction

HAM = Path("data/ham")
ONBELLEK = Path("data/cikarim")


def sayfa_listesi(test_seti: bool, sirket: str) -> list[Path]:
    if test_seti:
        manifest = json.loads(Path("data/test_seti/manifest.json").read_text(encoding="utf-8"))["sayfalar"]
        return [next(HAM.glob(f"*/{p['id']}.json")) for p in manifest]
    sirketler = ["THYAO", "PGSUS", "KCHOL", "SAHOL"] if sirket == "hepsi" else [sirket]
    return [j for s in sirketler for j in sorted((HAM / s).glob("*.json"))]


def cikar(kunye: Path, generate, model: str) -> Extraction | None:
    sid = kunye.stem
    onbellek = ONBELLEK / f"{sid}.json"
    if onbellek.exists():
        return Extraction.model_validate_json(onbellek.read_text(encoding="utf-8"))
    txt = kunye.with_suffix(".txt")
    if not txt.exists():
        print(f"[ATLANDI] ham metin yok: {sid}", file=sys.stderr)
        return None
    toplam, hata = Extraction(), 0
    for res in extract_document(txt.read_text(encoding="utf-8"), generate):
        if res.failed:
            hata += 1
            continue
        toplam.entities += res.extraction.entities
        toplam.relations += res.extraction.relations
    if hata:
        print(f"[UYARI] {sid}: {hata} parça işlenemedi", file=sys.stderr)
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    onbellek.write_text(toplam.model_dump_json(indent=1), encoding="utf-8")
    return toplam


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sirket", default="hepsi")
    ap.add_argument("--test-seti", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--yaz-yok", action="store_true", help="Neo4j'ye yazma")
    a = ap.parse_args(argv)
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    generate = lambda p: ollama_generate(p, model, os.getenv("OLLAMA_URL", "http://localhost:11434"))
    run = driver = None
    if not a.yaz_yok:
        run, driver = neo4j_runner(os.getenv("NEO4J_URI", "bolt://localhost:7687"), os.getenv("NEO4J_USER", "neo4j"),
                                   os.getenv("NEO4J_PASSWORD", "paragoz-dev-sifre"))
        apply_schema(driver)
    sayfalar = sayfa_listesi(a.test_seti, a.sirket)[: a.limit]
    t0, nv, nr = time.time(), 0, 0
    for i, k in enumerate(sayfalar, 1):
        ext = cikar(k, generate, model)
        if ext is None:
            continue
        nv, nr = nv + len(ext.entities), nr + len(ext.relations)
        if run:
            write_extraction(run, ext, k.stem, model)
        print(f"[{i}/{len(sayfalar)}] {k.stem}: {len(ext.entities)} varlık, {len(ext.relations)} ilişki", flush=True)
    print(f"Bitti: {nv} varlık, {nr} ilişki, {time.time()-t0:.0f} sn")
    if driver:
        driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
