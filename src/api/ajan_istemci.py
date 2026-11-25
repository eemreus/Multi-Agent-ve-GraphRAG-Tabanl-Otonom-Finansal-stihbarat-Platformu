"""Gateway'in GraphRAG ajan servisini HTTP ile çağıran istemcisi. SorServisi'ne cevapla_fn olarak verilir."""
from __future__ import annotations

import os

import httpx

from src.graphrag.pipeline import Sonuc


class AjanHatasi(RuntimeError):
    """Ajan servisine ulaşılamadı ya da hata döndürdü."""


class AjanZamanAsimi(AjanHatasi):
    pass


class AjanIstemcisi:
    def __init__(self, url: str, token: str, zaman_asimi: float = 300.0, istemci: httpx.Client | None = None):
        self.token = token
        self.http = istemci or httpx.Client(base_url=url.rstrip("/"), timeout=zaman_asimi)

    def __call__(self, soru: str) -> Sonuc:
        try:
            r = self.http.post("/cevapla", json={"soru": soru}, headers={"X-Internal-Token": self.token})
        except httpx.TimeoutException as e:
            raise AjanZamanAsimi("Ajan servisi zamanında cevap vermedi.") from e
        except httpx.HTTPError as e:
            raise AjanHatasi("Ajan servisine ulaşılamadı.") from e
        if r.status_code != 200:
            raise AjanHatasi(f"Ajan servisi {r.status_code} döndürdü.")
        d = r.json()
        return Sonuc(d["cevap"], d["atiflar"], d["gecikme_ms"], d["kanit_sayisi"], [], d["atilan_atif"])

    @classmethod
    def ortamdan(cls) -> "AjanIstemcisi | None":
        """AGENT_URL tanımlıysa uzak ajanı kullanır; yoksa None (tek parça çalışma)."""
        url = os.getenv("AGENT_URL")
        return cls(url, os.getenv("INTERNAL_TOKEN", "")) if url else None
