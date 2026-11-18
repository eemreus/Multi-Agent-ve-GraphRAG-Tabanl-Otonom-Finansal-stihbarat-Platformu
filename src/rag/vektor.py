"""Vektör RAG baseline (#23).

Akış: sayfaları parçala -> parçaları Ollama ile vektöre çevir -> soruya en yakın K parçayı bul
(kosinüs benzerliği) -> parçaları yerel modele verip kısa cevap üret.

GraphRAG ile aynı yerel model ve aynı korpus kullanılır; tek fark bilgiyi nasıl bulduğudur
(vektör benzerliği ya da graf gezintisi). Çıktı biçimi src/olcum/run.py ile uyumludur.
Ağ erişimi gerektiren iki işlev (ollama_embed, ollama_generate) dışarıdan verilebilir,
bu yüzden testler Ollama olmadan çalışır.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

from src.graf.extractor import chunk_text

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
GEN_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3")  # çok dilli, Türkçe'de nomic-embed-text'ten iyi
PARCA_BOYU = 1200  # karakter; kısa parça aramayı keskinleştirir
TOP_K = 4
INDEKS_YOLU = Path("results/vektor-indeks.json")

EmbedFn = Callable[[list[str]], list[list[float]]]
GenerateFn = Callable[[str], str]

PROMPT = """Aşağıdaki kaynak parçalarına dayanarak soruyu yanıtla.
Yalnızca parçalardaki bilgiyi kullan. Cevabı en fazla bir cümleyle, gereksiz açıklama olmadan yaz.
Parçalarda cevap yoksa sadece "Bilgi yok" yaz.

KAYNAK PARÇALARI:
{baglam}

SORU: {soru}
CEVAP:"""


@dataclass
class Parca:
    source_id: str
    no: int
    text: str

    @property
    def anahtar(self) -> str:
        return f"{self.source_id}:{self.no}:{hashlib.sha1(self.text.encode('utf-8')).hexdigest()[:12]}"


# ---------- Ollama ----------

def ollama_embed(metinler: list[str], batch: int = 16) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(metinler), batch):
        r = requests.post(f"{OLLAMA_URL}/api/embed",
                          json={"model": EMBED_MODEL, "input": metinler[i:i + batch]}, timeout=180)
        r.raise_for_status()
        out.extend(r.json()["embeddings"])
    return out


def ollama_generate(prompt: str) -> str:
    r = requests.post(f"{OLLAMA_URL}/api/generate",
                      json={"model": GEN_MODEL, "prompt": prompt, "stream": False,
                            "options": {"temperature": 0, "num_predict": 120}}, timeout=300)
    r.raise_for_status()
    return r.json()["response"].strip()


# ---------- Korpus ve indeks ----------

def sayfalari_yukle(klasor: str | Path) -> dict[str, str]:
    """klasor altındaki tüm .txt sayfalarını {sayfa_id: metin} olarak okur (_ ile başlayanlar atlanır)."""
    sayfalar: dict[str, str] = {}
    for p in sorted(Path(klasor).rglob("*.txt")):
        if p.name.startswith("_"):
            continue
        sayfalar[p.stem] = p.read_text(encoding="utf-8")
    return sayfalar


def parcala(sayfalar: dict[str, str], boy: int = PARCA_BOYU) -> list[Parca]:
    return [Parca(sid, n, c) for sid, metin in sayfalar.items() for n, c in enumerate(chunk_text(metin, boy))]


def _normalle(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _nokta(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class Indeks:
    def __init__(self, parcalar: list[Parca], vektorler: list[list[float]], embed: EmbedFn):
        self.parcalar, self.vektorler, self.embed = parcalar, vektorler, embed

    @classmethod
    def kur(cls, sayfalar: dict[str, str], embed: EmbedFn = ollama_embed,
            onbellek: Path | None = INDEKS_YOLU, boy: int = PARCA_BOYU) -> "Indeks":
        """Parçaları vektöre çevirir. Önbellekte olan parçalar yeniden hesaplanmaz."""
        parcalar = parcala(sayfalar, boy)
        eski: dict[str, list[float]] = {}
        if onbellek and Path(onbellek).exists():
            veri = json.loads(Path(onbellek).read_text(encoding="utf-8"))
            if veri.get("model") == EMBED_MODEL:
                eski = veri["vektorler"]
        eksik = [p for p in parcalar if p.anahtar not in eski]
        if eksik:
            for p, v in zip(eksik, embed([p.text for p in eksik])):
                eski[p.anahtar] = _normalle(v)
        if onbellek and eksik:
            Path(onbellek).parent.mkdir(parents=True, exist_ok=True)
            Path(onbellek).write_text(json.dumps({"model": EMBED_MODEL, "vektorler": eski}), encoding="utf-8")
        return cls(parcalar, [eski[p.anahtar] for p in parcalar], embed)

    def ara(self, soru: str, k: int = TOP_K) -> list[Parca]:
        q = _normalle(self.embed([soru])[0])
        skor = sorted(((_nokta(q, v), i) for i, v in enumerate(self.vektorler)), reverse=True)
        return [self.parcalar[i] for _, i in skor[:k]]


# ---------- Soru cevaplama ----------

def cevapla(soru: str, indeks: Indeks, generate: GenerateFn = ollama_generate, k: int = TOP_K) -> dict:
    """Uçtan uca süre (vektörleme + arama + üretim) latency_ms olarak ölçülür."""
    t0 = time.perf_counter()
    bulunan = indeks.ara(soru, k)
    baglam = "\n\n".join(f"[kaynak: {p.source_id}]\n{p.text}" for p in bulunan)
    cevap = generate(PROMPT.format(baglam=baglam, soru=soru))
    ms = round((time.perf_counter() - t0) * 1000, 1)
    return {"answer": cevap, "latency_ms": ms, "citations": [],
            "retrieved": sorted({p.source_id for p in bulunan})}


def sorulari_yukle(yol: str | Path = "data/test_seti/sorular.csv") -> list[dict]:
    with open(yol, encoding="utf-8-sig", newline="") as f:
        satirlar = list(csv.DictReader(f, delimiter=";"))
    sorular = []
    for r in satirlar:
        if not r.get("soru") or not r.get("cevap"):
            continue
        kaynaklar = [r[f"kaynak_{i}"] for i in (1, 2, 3) if r.get(f"kaynak_{i}")]
        sorular.append({"id": r["no"], "tur": r["tur"], "soru": r["soru"], "gold": r["cevap"], "kaynaklar": kaynaklar})
    return sorular


def degerlendir(sorular: list[dict], indeks: Indeks, generate: GenerateFn = ollama_generate,
                k: int = TOP_K) -> dict:
    """src/olcum/run.py'nin beklediği biçimde (yalnızca 'vector' kısmı dolu) sonuç üretir."""
    cikti = []
    for s in sorular:
        v = cevapla(s["soru"], indeks, generate, k)
        isabet = sum(1 for k_ in s["kaynaklar"] if k_ in v["retrieved"])
        cikti.append({"id": s["id"], "tur": s["tur"], "gold": s["gold"], "vector": v,
                      "kaynak_isabeti": f"{isabet}/{len(s['kaynaklar'])}"})
    return {"sources": {}, "questions": cikti}
