"""Test seti sorularını doğrular. Kullanım: python -m src.toplama.sorulari_dogrula

Kontroller: her kanıt cümlesi kaynak sayfa metninde birebir geçiyor mu, 25 kelimeyi aşıyor mu,
kaynak sayfa dondurulmuş 40 sayfa içinde mi, tür dağılımı hedefle (10/15/10/5) uyuşuyor mu.
Ham .txt dosyaları repoda yok; data/ham/<ŞİRKET>/ altında bulunmalı."""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

HEDEF = {"tek": 10, "iki": 15, "uc": 10, "celiski": 5}


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def dogrula(kok: Path = Path(".")) -> list[str]:
    hatalar = []
    manifest = json.loads((kok / "data/test_seti/manifest.json").read_text(encoding="utf-8"))["sayfalar"]
    ids = {p["id"] for p in manifest}
    satirlar = list(csv.DictReader((kok / "data/test_seti/sorular.csv").open(encoding="utf-8-sig"), delimiter=";"))
    for r in satirlar:
        for n in "123":
            kanit, kaynak = r[f"kanit_{n}"], r[f"kaynak_{n}"]
            if not kanit:
                continue
            if kaynak not in ids:
                hatalar.append(f"{r['no']}: kaynak test setinde değil ({kaynak})")
                continue
            if len(kanit.split()) > 25:
                hatalar.append(f"{r['no']}: kanıt 25 kelimeden uzun")
            dosya = next((kok / "data/ham").glob(f"*/{kaynak}.txt"), None)
            if dosya is None:
                hatalar.append(f"{r['no']}: ham metin yok ({kaynak}), kanıt denetlenemedi")
            elif _ws(kanit) not in _ws(dosya.read_text(encoding="utf-8")):
                hatalar.append(f"{r['no']}: kanıt metinde birebir geçmiyor ({kaynak})")
    sayim = Counter(r["tur"] for r in satirlar)
    if len(satirlar) == sum(HEDEF.values()) and sayim != Counter(HEDEF):
        hatalar.append(f"tür dağılımı hedefle uyuşmuyor: {dict(sayim)}")
    return hatalar


if __name__ == "__main__":
    h = dogrula()
    print("\n".join(h) if h else "Tüm kontroller geçti")
    sys.exit(1 if h else 0)
