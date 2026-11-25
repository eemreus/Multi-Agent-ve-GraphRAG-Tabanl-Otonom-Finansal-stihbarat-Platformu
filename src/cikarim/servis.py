"""Bilgi çıkarım ajanının işi: metinden varlık ve ilişki çıkarır, Neo4j'ye yazar. FastAPI gerektirmez."""
from __future__ import annotations

from typing import Callable

from src.graf.extractor import extract_document
from src.graf.schema import Extraction
from src.graf.writer import write_extraction

MIN_METIN, MAKS_METIN = 20, 200_000


class GecersizMetin(ValueError):
    pass


def metin_temizle(metin: str | None) -> str:
    t = (metin or "").strip()
    if not (MIN_METIN <= len(t) <= MAKS_METIN):
        raise GecersizMetin(f"Metin {MIN_METIN}-{MAKS_METIN} karakter arasında olmalı.")
    return t


def cikar_ve_yaz(metin: str, kaynak_id: str, generate: Callable[[str], str], run: Callable[[str, dict], None] | None,
                 model: str) -> dict:
    """Metni parçalara bölüp çıkarım yapar. Kanıtı metinde olmayan ilişkiler atılır (uydurma koruması).
    Tüm parçalar başarısızsa `yazildi` false kalır; run None ise yalnızca çıkarır (kuru çalıştırma)."""
    toplam, hatali, atilan_iliski, atilan_oge = Extraction(), 0, 0, 0
    for res in extract_document(metin_temizle(metin), generate):
        if res.failed:
            hatali += 1
            continue
        atilan_iliski += len(res.dropped)
        atilan_oge += len(res.notlar)
        toplam.entities += res.extraction.entities
        toplam.relations += res.extraction.relations
    yazildi = bool(run) and bool(toplam.entities)
    if yazildi:
        write_extraction(run, toplam, kaynak_id, model)
    return {"kaynak_id": kaynak_id, "varlik": len(toplam.entities), "iliski": len(toplam.relations),
            "atilan_iliski": atilan_iliski, "atilan_oge": atilan_oge, "hatali_parca": hatali, "yazildi": yazildi}
