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

from .schema import REL_RULES, Entity, Extraction, Relation, normalize_name

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
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


_LABELS = {l.lower(): l for l in ("Company", "Person", "Event", "Location", "Metric")}


def salvage_json(raw: str):
    """Çıktı token sınırında kesildiyse son tam nesneye kadar kırpıp parantezleri kapatır."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    pos = len(raw)
    for _ in range(60):
        pos = raw.rfind("}", 0, pos)
        if pos < 0:
            break
        for kapanis in ("", "]}", "}]}", "]}]}"):
            try:
                return json.loads(raw[: pos + 1] + kapanis)
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("kurtarılamadı", raw, 0)


def parse_lenient(data: dict) -> tuple[Extraction, list[str]]:
    """Küçük modeller kusurlu JSON üretir: tüm çıktıyı atmak yerine geçerli varlık ve ilişkileri
    tek tek alır, geçersizleri nedenleriyle birlikte döndürür."""
    notlar: list[str] = []
    ents, by_norm = [], {}
    for e in data.get("entities") or []:
        try:
            e = dict(e)
            e["label"] = _LABELS.get(str(e.get("label", "")).strip().lower(), e.get("label"))
            e["aliases"] = [a for a in (e.get("aliases") or []) if isinstance(a, str)]
            if not isinstance(e.get("ticker"), str):
                e["ticker"] = None
            ent = Entity.model_validate(e)
        except Exception as ex:
            notlar.append(f"varlık atıldı: {str(ex)[:60]}")
            continue
        if normalize_name(ent.name) not in by_norm:
            ents.append(ent)
            by_norm[normalize_name(ent.name)] = ent
    rels = []
    for r in data.get("relations") or []:
        try:
            r = dict(r)
            r["type"] = str(r.get("type", "")).strip().upper()
            src, tgt = by_norm.get(normalize_name(str(r.get("source", "")))), by_norm.get(normalize_name(str(r.get("target", ""))))
            if src is None or tgt is None:
                raise ValueError("ilişki tanımsız varlığa bağlı")
            if r["type"] not in REL_RULES:
                raise ValueError(f"bilinmeyen ilişki türü {r['type']}")
            ok_s, ok_t = REL_RULES[r["type"]]
            if src.label not in ok_s or tgt.label not in ok_t:
                raise ValueError(f"{r['type']} için etiketler uyumsuz")
            r["source"], r["target"] = src.name, tgt.name
            try:
                r["confidence"] = min(1.0, max(0.0, float(r.get("confidence", 0.5))))
            except (TypeError, ValueError):
                r["confidence"] = 0.5
            r["props"] = {k: v for k, v in (r.get("props") or {}).items() if isinstance(v, (str, int, float)) or v is None}
            rels.append(Relation.model_validate(r))
        except Exception as ex:
            notlar.append(f"ilişki atıldı: {str(ex)[:60]}")
    return Extraction(entities=ents, relations=rels), notlar


def evidence_in_text(evidence: str, text: str) -> bool:
    return _norm_ws(evidence) in _norm_ws(text)


def ollama_generate(prompt: str, model: str = "llama3.1:8b", url: str = "http://localhost:11434") -> str:
    r = requests.post(
        f"{url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "format": "json",
              "options": {"temperature": 0, "num_predict": 1500, "num_ctx": 4096, "repeat_penalty": 1.1}},
        timeout=240,
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
    notlar: list[str] = field(default_factory=list)  # tolerans nedeniyle atılan öğeler


def extract_chunk(text: str, generate: Callable[[str], str]) -> ChunkResult:
    rules = "; ".join(f"{k}: {'/'.join(sorted(s))} -> {'/'.join(sorted(t))}" for k, (s, t) in REL_RULES.items())
    prompt = PROMPT.format(rules=rules, text=text)
    last_err = None
    for attempt in range(1, MAX_RETRIES + 2):  # ilk deneme + 2 yeniden deneme
        try:
            raw = generate(prompt if last_err is None else
                           f"{prompt}\n\nÖnceki cevap geçersizdi ({last_err}). Yalnızca düzeltilmiş JSON ver.")
        except requests.exceptions.Timeout:
            last_err = "model zaman aşımı"
            continue
        try:
            data = salvage_json(raw)
            if not isinstance(data, dict):
                raise ValueError("JSON nesne değil")
            ext, notlar = parse_lenient(data)
            if not ext.entities:
                raise ValueError("geçerli varlık yok: " + "; ".join(notlar[:3]))
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as e:
            last_err = str(e)[:300]
            continue
        kept, dropped = [], []
        for r in ext.relations:
            (kept if evidence_in_text(r.evidence, text) else dropped).append(r)
        ext.relations = kept
        return ChunkResult(ext, [f"{r.type}:{r.source}->{r.target}" for r in dropped], attempt, notlar=notlar)
    # Bu noktada akış şemasına göre API modeline yükseltme yapılır (Hafta 4+); şimdilik hata kaydı.
    return ChunkResult(Extraction(), attempts=MAX_RETRIES + 1, failed=True, error=last_err)


def extract_document(text: str, generate: Callable[[str], str]) -> list[ChunkResult]:
    return [extract_chunk(c, generate) for c in chunk_text(text, 1800)]
