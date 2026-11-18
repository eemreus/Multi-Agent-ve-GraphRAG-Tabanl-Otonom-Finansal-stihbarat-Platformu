import json

from src.olcum.metrics import Citation, compare_table, f1_gain, fabricated_citation_rate, percentile, token_f1
from src.olcum.run import evaluate


def test_f1_basic():
    assert token_f1("Ahmet Bolat", "ahmet bolat") == 1.0
    assert token_f1("a b", "c d") == 0.0
    assert 0 < token_f1("Ahmet Bolat başkan", "Ahmet Bolat") < 1


def test_f1_turkish_chars():
    assert token_f1("İstanbul", "istanbul") == 1.0


def test_gain():
    assert abs(f1_gain(0.6, 0.5) - 0.2) < 1e-9


def test_fabricated():
    src = {"1": "Ahmet Bolat yönetim kurulu başkanıdır."}
    cs = [Citation("1", "Ahmet Bolat yönetim kurulu"), Citation("1", "yok bu"), Citation("9", "x")]
    assert abs(fabricated_citation_rate(cs, src) - 2 / 3) < 1e-9
    assert fabricated_citation_rate([], src) == 0.0


def test_percentile():
    assert percentile(list(range(1, 101))) == 95
    assert percentile([5.0]) == 5.0


def test_table_and_evaluate():
    data = {"sources": {"1": "Koç Holding Tüpraş'ın ana ortağıdır."},
            "questions": [{"id": 1, "gold": "Koç Holding",
                           "graph": {"answer": "Koç Holding", "latency_ms": 900,
                                     "citations": [{"source_id": "1", "quote": "Koç Holding Tüpraş'ın ana ortağıdır."}]},
                           "vector": {"answer": "Sabancı", "latency_ms": 500}}]}
    t = evaluate(json.loads(json.dumps(data)))
    assert t.count("Karşılandı") == 3
    assert "Karşılanmadı" in compare_table(0.5, 0.5, 0.0, 100)
