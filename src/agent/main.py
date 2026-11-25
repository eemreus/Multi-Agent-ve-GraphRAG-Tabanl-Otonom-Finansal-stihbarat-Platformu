"""GraphRAG ajan servisi (iç servis). Çalıştırma: uvicorn src.agent.main:app --port 8001
Yalnızca gateway çağırır; dışarıya açılmaz. Gateway, X-Internal-Token başlığıyla kimliğini kanıtlar."""
from __future__ import annotations

import hmac
import os
from typing import Callable

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


class AjanIstegi(BaseModel):
    soru: str = Field(..., min_length=3, max_length=500)


class AjanYaniti(BaseModel):
    cevap: str
    atiflar: list[dict]
    atilan_atif: int
    kanit_sayisi: int
    gecikme_ms: float


def uygulama_olustur(cevapla_fn: Callable | None = None, token: str | None = None) -> FastAPI:
    """cevapla_fn(soru) -> Sonuc. Verilmezse ilk istekte gerçek hat kurulur (Neo4j ve Ollama gerekir)."""
    app = FastAPI(title="ParaGöz GraphRAG Ajanı", version="0.1.0", description="İç servis: gateway dışında çağrılmaz.")
    durum = {"fn": cevapla_fn}
    beklenen = token if token is not None else os.getenv("INTERNAL_TOKEN", "")

    def kimlik(x_internal_token: str | None = Header(default=None)) -> None:
        # Token tanımlı değilse servis kapalı sayılır: açık bırakmak yerine reddederiz.
        if not beklenen or not hmac.compare_digest((x_internal_token or "").encode(), beklenen.encode()):
            raise HTTPException(401, "Geçersiz iç servis anahtarı.")

    @app.get("/saglik", tags=["sistem"])
    def saglik() -> dict:
        return {"durum": "ok", "servis": "graphrag-ajan"}

    @app.post("/cevapla", response_model=AjanYaniti, tags=["ajan"], dependencies=[Depends(kimlik)])
    def cevapla(istek: AjanIstegi) -> AjanYaniti:
        if durum["fn"] is None:
            from src.graphrag.kurulum import gercek_cevapla
            durum["fn"] = gercek_cevapla()
        s = durum["fn"](istek.soru)
        return AjanYaniti(cevap=s.cevap, atiflar=s.atiflar, atilan_atif=s.atilan_atif,
                          kanit_sayisi=s.kanit_sayisi, gecikme_ms=s.gecikme_ms)

    return app


app = uygulama_olustur()
