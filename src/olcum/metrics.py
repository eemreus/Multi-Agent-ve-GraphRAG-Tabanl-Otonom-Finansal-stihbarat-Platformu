"""Metrikler. Hedefler: docs/10-hafta3-plan.md (öneri formundaki nicel hedefler)."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from src.graf.schema import normalize_name

TARGETS = {"f1_gain": 0.20, "fabricated_citation_rate": 0.05, "p95_latency_ms": 2500.0}


def _tokens(s: str) -> list[str]:
    return normalize_name(re.sub(r"[^\w\s]", " ", s)).split()


def token_f1(pred: str, gold: str) -> float:
    """SQuAD tarzı kelime düzeyinde F1 (Türkçe karakterler normalleştirilir)."""
    p, g = _tokens(pred), _tokens(gold)
    if not p or not g:
        return float(p == g)
    common = sum((Counter(p) & Counter(g)).values())
    if common == 0:
        return 0.0
    prec, rec = common / len(p), common / len(g)
    return 2 * prec * rec / (prec + rec)


def mean_f1(preds: list[str], golds: list[str]) -> float:
    assert len(preds) == len(golds) and preds
    return sum(token_f1(p, g) for p, g in zip(preds, golds)) / len(preds)


def f1_gain(graph_f1: float, vector_f1: float) -> float:
    """Göreli artış: (graph - vector) / vector."""
    if vector_f1 == 0:
        return math.inf if graph_f1 > 0 else 0.0
    return (graph_f1 - vector_f1) / vector_f1


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


@dataclass
class Citation:
    source_id: str
    quote: str  # cevapta atıf yapılan kanıt cümlesi


def fabricated_citation_rate(citations: list[Citation], sources: dict[str, str]) -> float:
    """Uydurma atıf: kaynak yok ya da alıntı o kaynağın metninde geçmiyor."""
    if not citations:
        return 0.0
    bad = sum(1 for c in citations if c.source_id not in sources or _ws(c.quote) not in _ws(sources[c.source_id]))
    return bad / len(citations)


def percentile(values: list[float], q: float = 95.0) -> float:
    """En yakın sıra (nearest-rank) yüzdelik."""
    assert values
    s = sorted(values)
    k = max(1, math.ceil(q / 100 * len(s)))
    return s[k - 1]


def compare_table(graph_f1: float, vector_f1: float, fab_rate: float, p95_ms: float) -> str:
    gain = f1_gain(graph_f1, vector_f1)
    rows = [
        ("Yanıt doğruluğu (F1), GraphRAG vs vektör RAG", (f"+%{gain*100:.1f}" if math.isfinite(gain) else "tanımsız (vektör F1 = 0)") + f" (graf {graph_f1:.3f}, vektör {vector_f1:.3f})",
         "≥ +%20", gain >= TARGETS["f1_gain"]),
        ("Uydurma atıf oranı", f"%{fab_rate*100:.1f}", "< %5", fab_rate < TARGETS["fabricated_citation_rate"]),
        ("p@95 gecikme", f"{p95_ms:.0f} ms", "< 2500 ms", p95_ms < TARGETS["p95_latency_ms"]),
    ]
    out = ["| Metrik | Ölçülen | Hedef | Durum |", "|---|---|---|---|"]
    out += [f"| {a} | {b} | {c} | {'Karşılandı' if ok else 'Karşılanmadı'} |" for a, b, c, ok in rows]
    return "\n".join(out)
