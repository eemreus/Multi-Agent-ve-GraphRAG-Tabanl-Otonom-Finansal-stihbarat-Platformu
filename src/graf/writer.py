"""Neo4j'ye MERGE ile yazma. Aynı ilişki tekrar gelirse yalnızca source_ids genişler."""
from __future__ import annotations

import hashlib
import time
from typing import Callable

from .schema import REL_RULES, Entity, Extraction, normalize_name

LABELS = {"Company", "Person", "Event", "Location", "Metric"}


def node_id(label: str, name: str) -> str:
    return f"{label[:3].lower()}_{hashlib.sha1(normalize_name(name).encode()).hexdigest()[:12]}"


def entity_params(e: Entity) -> dict:
    return {"id": node_id(e.label, e.name), "name": e.name, "norm": normalize_name(e.name),
            "ticker": e.ticker, "aliases": e.aliases}


def node_query(label: str) -> str:
    assert label in LABELS
    extra = "n.ticker = coalesce($ticker, n.ticker)," if label == "Company" else ""
    norm = "n.normalized_name = $norm," if label in {"Company", "Person"} else ""
    alias = "n.aliases = coalesce(n.aliases, []) + [a IN $aliases WHERE NOT a IN coalesce(n.aliases, [])]," \
        if label in {"Company", "Person"} else ""
    return (f"MERGE (n:{label} {{id: $id}}) "
            f"ON CREATE SET n.name = $name, n.created_at = datetime(), n.source_ids = [] "
            f"SET {extra} {norm} {alias} n.updated_at = datetime(), "
            f"n.source_ids = n.source_ids + CASE WHEN $source_id IN n.source_ids THEN [] ELSE [$source_id] END")


def rel_query(rel_type: str, src_label: str, tgt_label: str) -> str:
    assert rel_type in REL_RULES and src_label in LABELS and tgt_label in LABELS
    return (f"MATCH (a:{src_label} {{id: $src}}), (b:{tgt_label} {{id: $tgt}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"ON CREATE SET r.first_seen = datetime(), r.source_ids = [$source_id], r.evidence = $evidence, "
            f"r.confidence = $confidence, r.extractor_model = $model "
            f"SET r += $props, r.last_seen = datetime() "
            f"SET r.source_ids = r.source_ids + CASE WHEN $source_id IN r.source_ids THEN [] ELSE [$source_id] END, "
            f"r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END")


def write_extraction(run: Callable[[str, dict], None], ext: Extraction, source_id: str, model: str,
                     retries: int = 3, sleep=time.sleep) -> None:
    """`run(query, params)` bir Neo4j yazma çağrısıdır. Hata olursa üssel bekleme ile ≤3 deneme;
    hâlâ olmazsa istisna yükselir (üst katman Redis hata kuyruğuna atar)."""
    labels = {e.name: e.label for e in ext.entities}

    def attempt(q, p):
        for i in range(retries):
            try:
                return run(q, p)
            except Exception:
                if i == retries - 1:
                    raise
                sleep(2 ** i)

    for e in ext.entities:
        attempt(node_query(e.label), {**entity_params(e), "source_id": source_id})
    for r in ext.relations:
        sl, tl = labels[r.source], labels[r.target]
        attempt(rel_query(r.type, sl, tl), {
            "src": node_id(sl, r.source), "tgt": node_id(tl, r.target), "source_id": source_id,
            "evidence": r.evidence, "confidence": r.confidence, "model": model,
            "props": {k: v for k, v in r.props.items() if v is not None}})


def neo4j_runner(uri: str, user: str, password: str):
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(uri, auth=(user, password))

    def run(query: str, params: dict) -> None:
        with driver.session() as s:
            s.run(query, **params).consume()
    return run, driver


def apply_schema(driver, path: str = "cypher/schema.cypher") -> None:
    stmts = [s.strip() for s in open(path, encoding="utf-8").read().split(";") if s.strip() and not s.strip().startswith("//") or ("CREATE" in s)]
    with driver.session() as s:
        for st in stmts:
            st = "\n".join(l for l in st.splitlines() if not l.strip().startswith("//")).strip()
            if st:
                s.run(st).consume()
