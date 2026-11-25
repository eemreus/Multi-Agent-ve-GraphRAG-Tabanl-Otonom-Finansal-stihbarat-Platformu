"""Soru-cevap servisi: GraphRAG hattını API için sarar. FastAPI gerektirmez, tek başına test edilir."""
from __future__ import annotations

import time
from typing import Callable

MIN_SORU, MAKS_SORU = 3, 500


class GecersizSoru(ValueError):
    pass


def soru_temizle(metin: str | None) -> str:
    t = " ".join((metin or "").split())
    if not (MIN_SORU <= len(t) <= MAKS_SORU):
        raise GecersizSoru(f"Soru {MIN_SORU}-{MAKS_SORU} karakter arasında olmalı.")
    return t


class SorServisi:
    """cevapla_fn(soru) -> src.graphrag.pipeline.Sonuc. telemetri(olay) her istek için çağrılır
    (Sıla: agent_logs tablosuna yazan fonksiyon buraya bağlanacak)."""

    def __init__(self, cevapla_fn: Callable, telemetri: Callable[[dict], None] | None = None):
        self.cevapla_fn = cevapla_fn
        self.telemetri = telemetri or (lambda olay: None)

    def sor(self, metin: str) -> dict:
        soru = soru_temizle(metin)
        t0 = time.perf_counter()
        hata = None
        try:
            s = self.cevapla_fn(soru)
            yanit = {"cevap": s.cevap, "atiflar": s.atiflar, "atilan_atif": s.atilan_atif,
                     "kanit_sayisi": s.kanit_sayisi}
        except Exception as e:  # model ya da graf hatası kullanıcıya ham gitmez
            hata = type(e).__name__
            raise
        finally:
            gecikme = int((time.perf_counter() - t0) * 1000)
            self.telemetri({"agent_name": "graphrag", "event_type": "sor", "latency_ms": gecikme,
                            "error_code": hata})
        yanit["gecikme_ms"] = gecikme
        return yanit
