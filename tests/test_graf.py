import json

import pytest

from src.graf.extractor import chunk_text, evidence_in_text, extract_chunk
from src.graf.schema import Extraction, normalize_name
from src.graf.writer import node_id, write_extraction

TEXT = "Ahmet Bolat, Türk Hava Yolları Yönetim Kurulu Başkanı olarak görev yapıyor."
GOOD = {
    "entities": [{"label": "Person", "name": "Ahmet Bolat"}, {"label": "Company", "name": "Türk Hava Yolları"}],
    "relations": [{"type": "BOARD_MEMBER_OF", "source": "Ahmet Bolat", "target": "Türk Hava Yolları",
                   "evidence": "Ahmet Bolat, Türk Hava Yolları Yönetim Kurulu Başkanı olarak görev yapıyor.",
                   "confidence": 0.9, "props": {"role": "Başkan"}}],
}


def test_normalize():
    assert normalize_name("Türk Hava Yolları A.O.") == normalize_name("TÜRK HAVA YOLLARI")
    assert normalize_name("Koç Holding A.Ş.") == "koc holding"


def test_schema_rejects_bad_label_pair():
    bad = json.loads(json.dumps(GOOD))
    bad["relations"][0]["type"] = "HEADQUARTERED_IN"
    with pytest.raises(ValueError):
        Extraction.model_validate(bad)


def test_schema_rejects_unknown_entity():
    bad = json.loads(json.dumps(GOOD))
    bad["relations"][0]["target"] = "Yok"
    with pytest.raises(ValueError):
        Extraction.model_validate(bad)


def test_extract_ok():
    r = extract_chunk(TEXT, lambda p: json.dumps(GOOD))
    assert not r.failed and len(r.extraction.relations) == 1 and r.attempts == 1


def test_retry_then_success():
    outs = iter(["bozuk json", json.dumps(GOOD)])
    r = extract_chunk(TEXT, lambda p: next(outs))
    assert not r.failed and r.attempts == 2


def test_fails_after_two_retries():
    calls = []
    r = extract_chunk(TEXT, lambda p: calls.append(1) or "{")
    assert r.failed and len(calls) == 3


def test_fabricated_evidence_dropped():
    fake = json.loads(json.dumps(GOOD))
    fake["relations"][0]["evidence"] = "Bu cümle metinde yok."
    r = extract_chunk(TEXT, lambda p: json.dumps(fake))
    assert r.extraction.relations == [] and len(r.dropped) == 1


def test_evidence_whitespace_insensitive():
    assert evidence_in_text("a   b", "A b c")


def test_chunking():
    t = "\n\n".join(["x" * 100] * 10)
    cs = chunk_text(t, 250)
    assert len(cs) > 1 and all(len(c) <= 250 for c in cs)


def test_writer_merge_and_source_ids():
    calls = []
    ext = Extraction.model_validate(GOOD)
    write_extraction(lambda q, p: calls.append((q, p)), ext, "src1", "llama3.1:8b")
    assert len(calls) == 3
    rel_q, rel_p = calls[-1]
    assert "MERGE (a)-[r:BOARD_MEMBER_OF]->(b)" in rel_q and "source_ids" in rel_q
    assert rel_p["source_id"] == "src1" and rel_p["src"] == node_id("Person", "Ahmet Bolat")


def test_writer_retries_then_raises():
    n = {"c": 0}

    def boom(q, p):
        n["c"] += 1
        raise RuntimeError("db")
    with pytest.raises(RuntimeError):
        write_extraction(boom, Extraction.model_validate(GOOD), "s", "m", sleep=lambda s: None)
    assert n["c"] == 3
