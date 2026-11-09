"""Komut satırı: python -m src.graf.cli <metin.txt> --source-id 1 [--dry-run]"""
from __future__ import annotations

import argparse
import os
import sys

from .extractor import extract_document, ollama_generate
from .schema import Extraction
from .writer import apply_schema, neo4j_runner, write_extraction


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--source-id", default=None, help="PostgreSQL sources.id; verilmezse dosya adı kullanılır")
    ap.add_argument("--dry-run", action="store_true", help="Neo4j'ye yazma, sonucu yazdır")
    ap.add_argument("--init-schema", action="store_true")
    a = ap.parse_args(argv)

    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    gen = lambda p: ollama_generate(p, model, url)

    run = driver = None
    if not a.dry_run:
        run, driver = neo4j_runner(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                                   os.getenv("NEO4J_USER", "neo4j"),
                                   os.getenv("NEO4J_PASSWORD", "paragoz-dev-sifre"))
        if a.init_schema:
            apply_schema(driver)

    for f in a.files:
        sid = a.source_id or os.path.basename(f)
        text = open(f, encoding="utf-8").read()
        total = Extraction()
        for res in extract_document(text, gen):
            if res.failed:
                print(f"[HATA] {f}: parça işlenemedi ({res.error})", file=sys.stderr)
                continue
            for d in res.dropped:
                print(f"[ATLANDI] kanıt metinde yok: {d}", file=sys.stderr)
            total.entities += res.extraction.entities
            total.relations += res.extraction.relations
            if run:
                write_extraction(run, res.extraction, sid, model)
        print(f"{f}: {len(total.entities)} varlık, {len(total.relations)} ilişki")
        if a.dry_run:
            print(total.model_dump_json(indent=2))
    if driver:
        driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
