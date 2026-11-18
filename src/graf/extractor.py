"""Yerel model (Ollama) ile varlık-ilişki çıkarımı.

Akış (docs/flow-varlik-iliski-cikarimi.md): parçala -> JSON iste -> şema doğrula
-> en fazla 2 yeniden deneme -> kanıt cümlesi metinde mi kontrol et.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

import requests
from pydantic import ValidationError

from .schema import REL_RULES, Extraction

MAX_RETRIES = 2

PROMPT = """Sen bir finansal bilgi çıkarım ajanısın. Aşağıdaki Türkçe metinden varlıkları ve ilişkileri çıkar.
SADECE geçerli JSON döndür, başka metin yazma.

Varlık etiketleri: Company, Person, Event, Location, Metric.
İlişki türleri (kaynak -> hedef): {rules}

JSON biçimi:
{{"entities":[{{"label":"Company","name":"...","ticker":null,"aliases":[]}}],
 "relations":[{{"type":"BOARD_MEMBER_OF","source":"<varlık adı>","target":"<varlık adı>",
   "evidence":"metinden BİREBİR alınmış cümle","confidence":0.0-1.0,"props":{{}}}}]}}

Kurallar: Metinde açıkça yazmayan ilişkiyi ekleme. evidence metinde aynen geçmeli.
İlişkideki source/target mutlaka entities listesindeki bir name olmalı.

METİN:
{text}
"""


def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """Paragraf sınırlarında parçalar; çok uzun paragrafı cümle sınırında böler."""
    chunks, cur = [], ""
    for para in re.split(r"\n\s*\n", text.strip()):
        for piece in re.split(r"(?<=[.!?])\s+", para) if len(para) > max_chars else [para]:
            if cur and len(cur) + len(piece) + 2 > max_chars:
                chunks.append(cur)
                cur = ""
            cur = f"{cur}\n\n{piece}" if cur else piece
    if cur:
        chunks.append(cur)
    return chunks


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def evidence_in_text(evidence: str, text: str) -> bool:
    return _norm_ws(evidence) in _norm_ws(text)


def ollama_generate(prompt: str, model: str = "llama3.1:8b", url: str = "http://localhost:11434") -> str:
    r = requests.post(
        f"{url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "format": "json",
              "options": {"temperature": 0}},
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["response"]


@dataclass
class ChunkResult:
    extraction: Extraction
    dropped: list[str] = field(default_factory=list)  # kanıtı metinde bulunmayan ilişkiler
    attempts: int = 1
    failed: bool = False
    error: str | None = None


def extract_chunk(text: str, generate: Callable[[str], str]) -> ChunkResult:
    rules = "; ".join(f"{k}: {'/'.join(sorted(s))} -> {'/'.join(sorted(t))}" for k, (s, t) in REL_RULES.items())
    prompt = PROMPT.format(rules=rules, text=text)
    last_err = None
    for attempt in range(1, MAX_RETRIES + 2):  # ilk deneme + 2 yeniden deneme
        raw = generate(prompt if last_err is None else
                       f"{prompt}\n\nÖnceki cevap geçersizdi ({last_err}). Yalnızca düzeltilmiş JSON ver.")
        try:
            ext = Extraction.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_err = str(e)[:300]
            continue
        kept, dropped = [], []
        for r in ext.relations:
            (kept if evidence_in_text(r.evidence, text) else dropped).append(r)
        ext.relations = kept
        return ChunkResult(ext, [f"{r.type}:{r.source}->{r.target}" for r in dropped], attempt)
    # Bu noktada akış şemasına göre API modeline yükseltme yapılır (Hafta 4+); şimdilik hata kaydı.
    return ChunkResult(Extraction(), attempts=MAX_RETRIES + 1, failed=True, error=last_err)


def extract_document(text: str, generate: Callable[[str], str]) -> list[ChunkResult]:
    return [extract_chunk(c, generate) for c in chunk_text(text)]
