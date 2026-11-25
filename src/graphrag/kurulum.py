"""Gerçek GraphRAG hattını (Neo4j + Ollama + sayfa metinleri) kurar. Hem tek parça API hem de ajan servisi kullanır."""
from __future__ import annotations

import os


# Atıf doğrulama, istem ya da arama mantığı değişince bir artırılır: Redis'teki eski cevaplar bu sayede geçersiz olur.
HAT_SURUMU = "2"


def model_adi() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.1:8b")


def gercek_cevapla():
    """soru -> Sonuc çağrılabilirini döndürür (Neo4j ve Ollama açık olmalı)."""
    from src.graf.extractor import ollama_generate_ayrintili
    from src.graf.writer import neo4j_reader, neo4j_runner
    from src.graphrag.degerlendir import sayfa_okuyucu
    from src.graphrag.pipeline import cevapla

    model, url = model_adi(), os.getenv("OLLAMA_URL", "http://localhost:11434")
    _, driver = neo4j_runner(os.getenv("NEO4J_URI", "bolt://localhost:7687"), os.getenv("NEO4J_USER", "neo4j"),
                             os.getenv("NEO4J_PASSWORD", "paragoz-dev-sifre"))
    okuyucu, sayfa = neo4j_reader(driver), sayfa_okuyucu()

    def cevapla_sayarak(soru: str):
        """Bu sorunun tüm model çağrılarının token toplamını sonuca yazar (her istek kendi sayacını kullanır)."""
        sayac = [0, 0]

        def uret(p: str) -> str:
            metin, girdi, cikti = ollama_generate_ayrintili(p, model, url)
            sayac[0] += girdi
            sayac[1] += cikti
            return metin
        s = cevapla(okuyucu, soru, uret, sayfa)
        s.tokens_in, s.tokens_out = sayac
        return s
    return cevapla_sayarak
