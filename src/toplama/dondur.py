"""Test setini dondurur. Kullanim: python -m src.toplama.dondur
havuz.csv'de secim=X olan sayfalari data/test_seti/sayfalar/ altina kopyalar ve manifest.json yazar."""
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .toplayici import HAM_KLASOR

HAVUZ = Path("data/test_seti/havuz.csv")
HEDEF = Path("data/test_seti/sayfalar")
MANIFEST = Path("data/test_seti/manifest.json")


def sha(yol):
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with HAVUZ.open(encoding="utf-8-sig", newline="") as f:
        secilen = [s for s in csv.DictReader(f, delimiter=";") if s["secim"].strip().upper() == "X"]
    HEDEF.mkdir(parents=True, exist_ok=True)
    kayitlar, eksik = [], []
    for s in secilen:
        kaynak = HAM_KLASOR / s["sirket"]
        kunye = json.loads((kaynak / f"{s['id']}.json").read_text(encoding="utf-8"))
        for ek in ("html", "txt", "json"):
            if not (kaynak / f"{s['id']}.{ek}").exists():
                eksik.append(f"{s['sirket']}/{s['id']}.{ek}")
        if eksik:
            continue
        for ek in ("html", "txt", "json"):
            shutil.copy2(kaynak / f"{s['id']}.{ek}", HEDEF / f"{s['id']}.{ek}")
        kayitlar.append({
            "id": s["id"], "sirket": s["sirket"], "url": kunye["url"], "alan_adi": kunye.get("alan_adi"),
            "kaynak_turu": kunye.get("kaynak_turu"), "erisim_tarihi": kunye["erisim_tarihi"],
            "grup_notu": s["not"], "metin_uzunlugu": kunye["metin_uzunlugu"],
            "sha256_html": sha(HEDEF / f"{s['id']}.html"), "sha256_metin": sha(HEDEF / f"{s['id']}.txt"),
        })
    if eksik:
        print("EKSIK DOSYA, dondurma yapilmadi:", *eksik, sep="\n  ")
        sys.exit(1)
    manifest = {"donduruldu": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "sayfa_sayisi": len(kayitlar), "sayfalar": kayitlar}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(kayitlar)} sayfa donduruldu -> {HEDEF}")
    print(f"Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()