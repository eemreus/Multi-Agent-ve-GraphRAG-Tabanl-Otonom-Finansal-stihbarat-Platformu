"""Kullanim: python -m src.toplama.cli --sirket THYAO --hedef 5"""
import argparse
import json
import sys

from .toplayici import SIRKETLER, topla


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Sirket basina web sayfasi topla ve dondurulmus kopya olarak sakla")
    p.add_argument("--sirket", choices=list(SIRKETLER) + ["hepsi"], default="hepsi")
    p.add_argument("--hedef", type=int, default=40, help="sirket basina hedef sayfa sayisi")
    a = p.parse_args()
    kodlar = list(SIRKETLER) if a.sirket == "hepsi" else [a.sirket]
    ozet = {}
    for kod in kodlar:
        print(f"== {kod} ==")
        sayac, kayitli = topla(kod, hedef=a.hedef)
        ozet[kod] = {"kayitli_sayfa": kayitli, **sayac}
        print(f"  ozet: {ozet[kod]}")
    print(json.dumps(ozet, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()