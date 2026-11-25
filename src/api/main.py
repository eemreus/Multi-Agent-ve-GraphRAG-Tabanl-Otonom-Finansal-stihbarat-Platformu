"""ParaGöz API. Çalıştırma: uvicorn src.api.main:app --reload   (Swagger: http://localhost:8000/docs)
Ortam: API_KEYS=anahtar1,anahtar2  (istemci X-API-Key başlığıyla gönderir)."""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from .guvenlik import ApiAnahtarlari, HizSiniri
from .servis import GecersizSoru, SorServisi


class SoruIstegi(BaseModel):
    soru: str = Field(..., description="Türkçe soru (3-500 karakter)", examples=[
        "Murat Pınar daha önce hangi şirketin CEO'suydu?"])


class Atif(BaseModel):
    source_id: str
    quote: str


class Yanit(BaseModel):
    cevap: str
    atiflar: list[Atif]
    atilan_atif: int = Field(description="Kaynakta doğrulanamayıp elenen atıf sayısı")
    kanit_sayisi: int
    gecikme_ms: int


def varsayilan_servis() -> SorServisi:
    """Gerçek GraphRAG hattı (Neo4j ve Ollama açık olmalı). İlk istekte kurulur."""
    from src.graf.extractor import ollama_generate
    from src.graf.writer import neo4j_reader, neo4j_runner
    from src.graphrag.degerlendir import sayfa_okuyucu
    from src.graphrag.pipeline import cevapla

    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    _, driver = neo4j_runner(os.getenv("NEO4J_URI", "bolt://localhost:7687"), os.getenv("NEO4J_USER", "neo4j"),
                             os.getenv("NEO4J_PASSWORD", "paragoz-dev-sifre"))
    okuyucu, sayfa = neo4j_reader(driver), sayfa_okuyucu()
    return SorServisi(lambda soru: cevapla(okuyucu, soru, lambda p: ollama_generate(p, model, url), sayfa))


def uygulama_olustur(servis: SorServisi | None = None, anahtarlar: ApiAnahtarlari | None = None,
                     sinirlayici: HizSiniri | None = None) -> FastAPI:
    app = FastAPI(title="ParaGöz API", version="0.1.0",
                  description="GraphRAG tabanlı finansal istihbarat: sorulara kaynaklı ve doğrulanmış cevap.")
    durum = {"servis": servis}
    anahtarlar = anahtarlar or ApiAnahtarlari.ortamdan()
    sinirlayici = sinirlayici or HizSiniri(maks=int(os.getenv("RATE_LIMIT_PER_MIN", "30")), pencere_sn=60)

    def kimlik(x_api_key: str | None = Header(default=None)) -> str:
        if not anahtarlar.gecerli(x_api_key):
            raise HTTPException(401, "Geçersiz ya da eksik API anahtarı (X-API-Key başlığı).")
        izinli, bekle = sinirlayici.izin(x_api_key)
        if not izinli:
            raise HTTPException(429, "İstek sınırı aşıldı.", headers={"Retry-After": str(int(bekle) + 1)})
        return x_api_key

    @app.get("/", include_in_schema=False)
    def kok() -> RedirectResponse:
        return RedirectResponse("/docs")

    @app.get("/saglik", tags=["sistem"], summary="Servis ayakta mı?")
    def saglik() -> dict:
        return {"durum": "ok"}

    @app.post("/sor", response_model=Yanit, tags=["soru-cevap"], summary="Soruyu kaynaklı cevapla")
    def sor(istek: SoruIstegi, _: str = Depends(kimlik)) -> Yanit:
        if durum["servis"] is None:
            durum["servis"] = varsayilan_servis()
        try:
            return Yanit(**durum["servis"].sor(istek.soru))
        except GecersizSoru as e:
            raise HTTPException(422, str(e))

    return app


app = uygulama_olustur()
