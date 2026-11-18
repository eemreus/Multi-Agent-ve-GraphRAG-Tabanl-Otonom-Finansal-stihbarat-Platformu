"""GraphRAG baseline: soru -> varlık bağlama -> graf komşuluğu (≤2 adım) -> kanıtlı cevap.

Her adım ölçülür; cevaptaki her atıf yalnızca grafın döndürdüğü kanıt cümlelerinden seçilebilir
(uydurma atıf oranını düşük tutmak için doğrulanır)."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable

from src.graf.schema import normalize_name

SORU_VARLIK_PROMPT = """Aşağıdaki Türkçe sorudaki şirket, kişi ve kuruluş adlarını çıkar.
SADECE JSON döndür: {{"varliklar": ["ad1", "ad2"]}}
SORU: {soru}"""

CEVAP_PROMPT = """Sen finansal bir araştırma asistanısın. YALNIZCA aşağıdaki kanıtlara dayanarak soruyu kısa cevapla.
Kanıt yetersizse cevabı "Kanıt yok" yaz. Cevap kısa olsun (bir iki cümle).
Atıf için kanıt cümlesini AYNEN kopyala ve kaynak numarasını yaz.
SADECE JSON döndür: {{"cevap": "...", "atiflar": [{{"source_id": "...", "quote": "..."}}]}}

SORU: {soru}

KANITLAR:
{kanitlar}"""

KOMSU_1 = ("MATCH (a {id: $id})-[r]-(b) RETURN a.name AS a, type(r) AS rel, startNode(r).name AS bas, "
           "endNode(r).name AS son, r.evidence AS evidence, r.source_ids AS source_ids, r.confidence AS conf "
           "ORDER BY r.confidence DESC LIMIT 40")
KOMSU_2 = ("MATCH (a {id: $id})-[]-(b)-[r]-(c) WHERE c.id <> a.id RETURN b.name AS a, type(r) AS rel, "
           "startNode(r).name AS bas, endNode(r).name AS son, r.evidence AS evidence, r.source_ids AS source_ids, "
           "r.confidence AS conf ORDER BY r.confidence DESC LIMIT 60")
BAGLA = ("MATCH (n) WHERE (n:Company OR n:Person OR n:Event OR n:Location) AND n.normalized_name IS NOT NULL "
         "AND (n.normalized_name = $norm OR n.normalized_name CONTAINS $norm OR ($norm CONTAINS n.normalized_name "
         "AND size(n.normalized_name) > 4)) RETURN n.id AS id, n.name AS name LIMIT 5")


@dataclass
class Sonuc:
    cevap: str
    atiflar: list[dict] = field(default_factory=list)
    gecikme_ms: float = 0.0
    kanit_sayisi: int = 0
    gorunen_varliklar: list[str] = field(default_factory=list)
    atilan_atif: int = 0


def _json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else {}


def kanit_topla(query: Callable, soru: str, generate: Callable[[str], str], maks: int = 40) -> tuple[list[dict], list[str]]:
    try:
        adlar = _json(generate(SORU_VARLIK_PROMPT.format(soru=soru))).get("varliklar", [])
    except Exception:
        adlar = []
    # model hiçbir şey vermezse soru metninden büyük harfle başlayan sözcükler denenir
    adlar = adlar or re.findall(r"\b[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ.]+(?:\s+[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ.]+)*", soru)
    ids, adlar_bulunan = [], []
    for ad in adlar:
        norm = normalize_name(str(ad))
        if len(norm) < 3:
            continue
        for r in query(BAGLA, {"norm": norm}):
            if r["id"] not in ids:
                ids.append(r["id"]); adlar_bulunan.append(r["name"])
    satirlar, goruldu = [], set()
    for i in ids:
        for q in (KOMSU_1, KOMSU_2):
            for r in query(q, {"id": i}):
                anahtar = (r["bas"], r["rel"], r["son"], r["evidence"])
                if r.get("evidence") and anahtar not in goruldu:
                    goruldu.add(anahtar); satirlar.append(r)
    satirlar.sort(key=lambda r: -(r.get("conf") or 0))
    return satirlar[:maks], adlar_bulunan


def kanit_metni(satirlar: list[dict]) -> str:
    out = []
    for r in satirlar:
        kaynak = (r.get("source_ids") or ["?"])[0]
        out.append(f"[{kaynak}] ({r['bas']} -{r['rel']}-> {r['son']}) {r['evidence']}")
    return "\n".join(out)


def cevapla(query: Callable, soru: str, generate: Callable[[str], str]) -> Sonuc:
    t0 = time.perf_counter()
    satirlar, adlar = kanit_topla(query, soru, generate)
    if not satirlar:
        return Sonuc("Kanıt yok", [], (time.perf_counter() - t0) * 1000, 0, adlar)
    try:
        j = _json(generate(CEVAP_PROMPT.format(soru=soru, kanitlar=kanit_metni(satirlar))))
    except Exception:
        j = {}
    izinli = {(sid, r["evidence"].strip()) for r in satirlar for sid in (r.get("source_ids") or [])}
    atiflar, atilan = [], 0
    for a in j.get("atiflar", []) or []:
        sid, q = str(a.get("source_id", "")), str(a.get("quote", "")).strip()
        if (sid, q) in izinli:
            atiflar.append({"source_id": sid, "quote": q})
        else:
            atilan += 1  # grafta olmayan atıf: uydurma sayılır ve cevaba girmez
    return Sonuc(str(j.get("cevap", "Kanıt yok")), atiflar, (time.perf_counter() - t0) * 1000, len(satirlar), adlar, atilan)
