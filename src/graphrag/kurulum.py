"""Gerçek GraphRAG hattını (Neo4j + Ollama + sayfa metinleri) kurar. Hem tek parça API hem de ajan servisi kullanır."""
from __future__ import annotations

import os


def model_adi() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.1:8b")


def gercek_cevapla():
    """soru -> Sonuc çağrılabilirini döndürür (Neo4j ve Ollama açık olmalı)."""
    from src.graf.extractor import ollama_generate
    from src.graf.writer import neo4j_reader, neo4j_runner
    from src.graphrag.degerlendir import sayfa_okuyucu
    from src.graphrag.pipeline import cevapla

    model, url = model_adi(), os.getenv("OLLAMA_URL", "http://localhost:11434")
    _, driver = neo4j_runner(os.getenv("NEO4J_URI", "bolt://localhost:7687"), os.getenv("NEO4J_USER", "neo4j"),
                             os.getenv("NEO4J_PASSWORD", "paragoz-dev-sifre"))
    okuyucu, sayfa = neo4j_reader(driver), sayfa_okuyucu()
    return lambda soru: cevapla(okuyucu, soru, lambda p: ollama_generate(p, model, url), sayfa)
