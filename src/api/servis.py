"""Soru-cevap servisi: GraphRAG hattını API için sarar. FastAPI gerektirmez, tek başına test edilir."""
from __future__ import annotations

import time
from typing import Callable

from .onbellek import onbellek_anahtari

MIN_SORU, MAKS_SORU = 3, 500


class GecersizSoru(ValueError):
    pass


def soru_temizle(metin: str | None) -> str:
    t = " ".join((metin or "").split())
    if not (MIN_SORU <= len(t) <= MAKS_SORU):
        raise GecersizSoru(f"Soru {MIN_SORU}-{MAKS_SORU} karakter arasında olmalı.")
    return t


class SorServisi:
    """cevapla_fn(soru) -> src.graphrag.pipeline.Sonuc.
    telemetri(olay): her istek için çağrılır (src.api.telemetri.AgentLogYazici agent_logs'a yazar).
    onbellek: get(anahtar)/set(anahtar, deger) arayüzlü nesne (src.api.onbellek). `surum` değişince
    (model, istem ya da graf güncellenince) eski cevaplar kullanılmaz."""

    def __init__(self, cevapla_fn: Callable, telemetri: Callable[[dict], None] | None = None,
                 onbellek=None, surum: str = "v1"):
        self.cevapla_fn = cevapla_fn
        self.telemetri = telemetri or (lambda olay: None)
        self.onbellek = onbellek
        self.surum = surum

    def sor(self, metin: str) -> dict:
        soru = soru_temizle(metin)
        anahtar = onbellek_anahtari(soru, self.surum)
        ozet = {"soru_ozeti": anahtar[:12]}  # ham soru loga yazılmaz
        t0 = time.perf_counter()
        if self.onbellek is not None:
            kayit = self.onbellek.get(anahtar)
            if kayit is not None:
                gecikme = int((time.perf_counter() - t0) * 1000)
                self.telemetri({"agent_name": "graphrag", "event_type": "sor_onbellek", "latency_ms": gecikme,
                                "error_code": None, "payload": ozet})
                return {**kayit, "gecikme_ms": gecikme, "onbellek": True}
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
                            "error_code": hata, "payload": ozet})
        if self.onbellek is not None:
            self.onbellek.set(anahtar, yanit)  # yalnızca başarılı cevap; hata yukarıda raise ile çıktı
        return {**yanit, "gecikme_ms": gecikme, "onbellek": False}
