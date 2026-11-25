"""ParaGöz API. Çalıştırma: uvicorn src.api.main:app --reload   (Swagger: http://localhost:8000/docs)
Ortam: API_KEYS=anahtar1,anahtar2  (istemci X-API-Key başlığıyla gönderir)."""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from .ajan_istemci import AjanHatasi, AjanZamanAsimi
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
    onbellek: bool = Field(default=False, description="Cevap önbellekten geldiyse true (model çağrılmadı)")


def varsayilan_servis() -> SorServisi:
    """AGENT_URL tanımlıysa ajan servisini HTTP ile çağırır (mikro servis modu); yoksa GraphRAG hattı bu süreçte
    çalışır (tek parça mod, Neo4j ve Ollama açık olmalı). İlk istekte kurulur."""
    from src.graphrag.kurulum import gercek_cevapla, model_adi

    from .ajan_istemci import AjanIstemcisi
    from .onbellek import ortamdan as onbellek_ortamdan
    from .telemetri import ortamdan as telemetri_ortamdan

    cevapla_fn = AjanIstemcisi.ortamdan() or gercek_cevapla()
    return SorServisi(cevapla_fn,
                      telemetri=telemetri_ortamdan(),   # DATABASE_URL varsa agent_logs'a yazar
                      onbellek=onbellek_ortamdan(),     # REDIS_URL varsa Redis önbelleği
                      surum=f"{model_adi()}:v1")


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
        except AjanZamanAsimi:
            raise HTTPException(504, "Ajan servisi zamanında cevap vermedi.")
        except AjanHatasi:
            raise HTTPException(502, "Ajan servisine ulaşılamadı.")

    return app


app = uygulama_olustur()
