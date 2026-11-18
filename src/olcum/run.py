"""Sonuç dosyalarından tablo üretir.

Girdi (JSON): {"questions":[{"id","gold","graph":{"answer","latency_ms","citations":[{"source_id","quote"}]},
"vector":{...aynı...}}], "sources":{"<source_id>":"<sayfa metni>"}}
Kullanım: python -m src.olcum.run results/graphrag.json results/vektor.json
(birden çok dosya id'ye göre birleştirilir; her dosya yalnızca kendi tarafını içerebilir)
"""
from __future__ import annotations

import json
import sys

from .metrics import Citation, compare_table, fabricated_citation_rate, mean_f1, percentile


def evaluate(data: dict) -> str:
    qs, sources = data["questions"], data["sources"]
    golds = [q["gold"] for q in qs]
    g_f1 = mean_f1([q["graph"]["answer"] for q in qs], golds)
    v_f1 = mean_f1([q["vector"]["answer"] for q in qs], golds)
    cites = [Citation(**c) for q in qs for c in q["graph"].get("citations", [])]
    fab = fabricated_citation_rate(cites, sources)
    p95 = percentile([q["graph"]["latency_ms"] for q in qs])
    return compare_table(g_f1, v_f1, fab, p95)


def birlestir(dosyalar: list[dict]) -> dict:
    qs: dict = {}
    kaynaklar: dict = {}
    for d in dosyalar:
        kaynaklar.update(d.get("sources", {}))
        for q in d["questions"]:
            qs.setdefault(q["id"], {}).update(q)
    return {"questions": list(qs.values()), "sources": kaynaklar}


if __name__ == "__main__":
    print(evaluate(birlestir([json.load(open(f, encoding="utf-8")) for f in sys.argv[1:]])))
