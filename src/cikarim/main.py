"""Bilgi çıkarım ajanı (iç servis). Çalıştırma: uvicorn src.cikarim.main:app --port 8002
Metni alır, varlık ve ilişkileri çıkarır, kaynak id'siyle Neo4j'ye yazar. Gateway ya da orkestratör çağırır."""
from __future__ import annotations

import hmac
import os
from typing import Callable

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .servis import MAKS_METIN, MIN_METIN, GecersizMetin, cikar_ve_yaz


class CikarimIstegi(BaseModel):
    kaynak_id: str = Field(..., min_length=1, max_length=64, description="Kaynağın kimliği (künye id)")
    metin: str = Field(..., description=f"Sayfa metni ({MIN_METIN}-{MAKS_METIN} karakter)")
    yaz: bool = Field(default=True, description="false ise Neo4j'ye yazmaz, yalnızca çıkarır")


class CikarimYaniti(BaseModel):
    kaynak_id: str
    varlik: int
    iliski: int
    atilan_iliski: int = Field(description="Kanıtı metinde bulunmadığı için atılan ilişki sayısı")
    atilan_oge: int
    hatali_parca: int
    yazildi: bool


def gercek_baglanti() -> tuple[Callable, Callable | None, str]:
    """(generate, neo4j_run, model). Ollama ve Neo4j açık olmalı."""
    from src.graf.extractor import ollama_generate
    from src.graf.writer import apply_schema, neo4j_runner

    model, url = os.getenv("OLLAMA_MODEL", "llama3.1:8b"), os.getenv("OLLAMA_URL", "http://localhost:11434")
    run, driver = neo4j_runner(os.getenv("NEO4J_URI", "bolt://localhost:7687"), os.getenv("NEO4J_USER", "neo4j"),
                               os.getenv("NEO4J_PASSWORD", "paragoz-dev-sifre"))
    apply_schema(driver)
    return (lambda p: ollama_generate(p, model, url)), run, model


def uygulama_olustur(baglanti: Callable | None = None, token: str | None = None) -> FastAPI:
    """baglanti() -> (generate, run, model). Verilmezse ilk istekte gerçek bağlantı kurulur."""
    app = FastAPI(title="ParaGöz Çıkarım Ajanı", version="0.1.0", description="İç servis: metinden bilgi grafiği çıkarır.")
    durum = {"baglanti": None}
    beklenen = token if token is not None else os.getenv("INTERNAL_TOKEN", "")

    def kimlik(x_internal_token: str | None = Header(default=None)) -> None:
        if not beklenen or not hmac.compare_digest((x_internal_token or "").encode(), beklenen.encode()):
            raise HTTPException(401, "Geçersiz iç servis anahtarı.")

    @app.get("/saglik", tags=["sistem"])
    def saglik() -> dict:
        return {"durum": "ok", "servis": "cikarim-ajani"}

    @app.post("/cikar", response_model=CikarimYaniti, tags=["ajan"], dependencies=[Depends(kimlik)])
    def cikar(istek: CikarimIstegi) -> CikarimYaniti:
        if durum["baglanti"] is None:
            durum["baglanti"] = (baglanti or gercek_baglanti)()
        generate, run, model = durum["baglanti"]
        try:
            return CikarimYaniti(**cikar_ve_yaz(istek.metin, istek.kaynak_id, generate, run if istek.yaz else None, model))
        except GecersizMetin as e:
            raise HTTPException(422, str(e))

    return app


app = uygulama_olustur()
