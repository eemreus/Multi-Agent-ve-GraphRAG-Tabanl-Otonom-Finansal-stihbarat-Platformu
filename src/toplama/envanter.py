"""Havuz envanteri. Kullanim: python -m src.toplama.envanter"""
import csv
import json
import sys
from pathlib import Path

from .toplayici import HAM_KLASOR

CIKTI = Path("data/test_seti/havuz.csv")
ALANLAR = ["id", "sirket", "alan_adi", "baslik", "metin_uzunlugu", "erisim_tarihi", "sorgu", "url", "secim", "not"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    satirlar = []
    for j in sorted(HAM_KLASOR.glob("*/*.json")):
        k = json.loads(j.read_text(encoding="utf-8"))
        satirlar.append({a: k.get(a, "") for a in ALANLAR} | {"secim": "", "not": ""})
    satirlar.sort(key=lambda s: (s["sirket"], s["alan_adi"]))
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    with CIKTI.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR, delimiter=";")
        w.writeheader()
        w.writerows(satirlar)
    print(f"{len(satirlar)} sayfa yazildi: {CIKTI}")


if __name__ == "__main__":
    main()