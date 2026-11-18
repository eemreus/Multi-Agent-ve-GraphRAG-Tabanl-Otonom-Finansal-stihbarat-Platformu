"""Veri kalitesi raporu. Kullanim: python -m src.toplama.kalite [--sil]"""
import argparse
import json
import sys
from collections import defaultdict

from .toplayici import HAM_KLASOR, alan_adi, normalize_url

SOSYAL = {"facebook.com", "x.com", "twitter.com", "instagram.com", "youtube.com",
          "prezi.com", "yandex.com.tr", "tradingview.com", "tr.tradingview.com", "eksisozluk.com"}
ANAHTAR = {
    "THYAO": ["turk hava yollari", "thyao", "thy"],
    "PGSUS": ["pegasus", "pgsus"],
    "KCHOL": ["koc holding", "kchol", "koc grubu"],
    "SAHOL": ["sabanci", "sahol"],
}
MIN_ANMA = 2
_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")


def sade(t):
    return t.translate(_TR).lower()


def puan(k):
    f = HAM_KLASOR / k["sirket"] / f"{k['id']}.txt"
    if not f.exists():
        return 0
    t = sade(f.read_text(encoding="utf-8"))
    return sum(t.count(a) for a in ANAHTAR[k["sirket"]])


def oku():
    kayitlar = []
    for j in sorted(HAM_KLASOR.glob("*/*.json")):
        try:
            k = json.loads(j.read_text(encoding="utf-8"))
        except ValueError:
            continue
        k["puan"] = puan(k)
        kayitlar.append(k)
    return kayitlar


def sil(k):
    for f in (HAM_KLASOR / k["sirket"]).glob(f"{k['id']}.*"):
        f.unlink()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--sil", action="store_true", help="isaretlenenleri gercekten sil")
    a = p.parse_args()
    kayitlar = oku()
    bul = {(k["sirket"], k["id"]): k for k in kayitlar}
    silinecek = {}
    for k in kayitlar:
        if alan_adi(k["url"]) in SOSYAL:
            silinecek[(k["sirket"], k["id"])] = "sosyal/forum"
    for anahtar in (lambda k: normalize_url(k["url"]), lambda k: k.get("metin_sha256") or k["id"]):
        gruplar = defaultdict(list)
        for k in kayitlar:
            gruplar[anahtar(k)].append(k)
        for g in gruplar.values():
            if len(g) > 1:
                g.sort(key=lambda x: -x["puan"])
                for k in g[1:]:
                    silinecek.setdefault((k["sirket"], k["id"]), "sirketler arasi tekrar")
    for k in kayitlar:
        if k["puan"] < MIN_ANMA:
            silinecek.setdefault((k["sirket"], k["id"]), f"ilgisiz? anma={k['puan']}")
    for key, sebep in sorted(silinecek.items()):
        k = bul[key]
        print(f"{key[0]} {key[1]} [{sebep}] {k['url'][:75]}")
    kalan = defaultdict(int)
    for k in kayitlar:
        if (k["sirket"], k["id"]) not in silinecek:
            kalan[k["sirket"]] += 1
    print(f"\nToplam {len(kayitlar)} sayfa | isaretlenen {len(silinecek)} | kalacak {dict(kalan)} = {sum(kalan.values())}")
    if a.sil:
        for key in silinecek:
            sil(bul[key])
        print("Silindi.")
    else:
        print("Rapor modu: hicbir sey silinmedi. Silmek icin --sil ekle.")


if __name__ == "__main__":
    main()