"""Alan adindan kaynak turu cikarir. Kullanim: python -m src.toplama.kaynak_turu  (mevcut kunyeleri gunceller)"""
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

RESMI = {"kap.org.tr", "investor.turkishairlines.com", "koc.com.tr", "sabanci.com", "flypgs.com",
         "m.enerjisa.com.tr", "esas.com.tr", "yapikredi.com.tr", "anadolubursiyerleri.ku.edu.tr"}
AJANS = {"aa.com.tr"}
ANSIKLOPEDI = {"tr.wikipedia.org"}
FINANS = {"fintables.com", "fvt.com.tr", "getmidas.com", "borsacoo.com", "paratic.com", "tacirler.com.tr",
          "gcmyatirim.com.tr", "hisse.net", "foreks.com", "analizyatirim.com", "endeks24.com", "finanshatti.com",
          "borsatek.com", "rotaborsa.com", "artifinx.com", "yatirimlar.com", "hocaileborsa.com",
          "borsaningundemi.com", "yatirimx.com.tr", "finansanlik.com", "finansaktuel.com", "gedik.com",
          "arastirma.isyatirim.com.tr"}


def tur(alan):
    """resmi | ajans | finans_portali | ansiklopedi | haber"""
    if alan in RESMI:
        return "resmi"
    if alan in AJANS:
        return "ajans"
    if alan in ANSIKLOPEDI:
        return "ansiklopedi"
    if alan in FINANS:
        return "finans_portali"
    return "haber"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sayac = Counter()
    for j in sorted(Path("data/ham").glob("*/*.json")):
        k = json.loads(j.read_text(encoding="utf-8"))
        alan = k.get("alan_adi") or urlparse(k["url"]).netloc.replace("www.", "")
        k["kaynak_turu"] = tur(alan)
        j.write_text(json.dumps(k, ensure_ascii=False, indent=2), encoding="utf-8")
        sayac[(k["sirket"], k["kaynak_turu"])] += 1
    for (s, t), n in sorted(sayac.items()):
        print(f"{s} {t}: {n}")
    print(f"Toplam {sum(sayac.values())} kunye guncellendi")


if __name__ == "__main__":
    main()