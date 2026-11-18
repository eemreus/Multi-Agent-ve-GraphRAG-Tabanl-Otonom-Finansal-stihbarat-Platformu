"""Vektör RAG komut satırı.

  python -m src.rag.cli indeks                         # korpusu vektöre çevirir (ilk seferde uzun sürer)
  python -m src.rag.cli sorula "Pegasus'un Esas Holding payı nedir?"
  python -m src.rag.cli degerlendir [--sinir 5]        # sorular.csv'yi çalıştırır, results/vektor-sonuc.json yazar
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from src.olcum.metrics import token_f1

from . import vektor

KORPUS_VARSAYILAN = "data/ham"  # GraphRAG'in işlediği havuzla aynı olmalı


def _indeks(korpus: str) -> vektor.Indeks:
    sayfalar = vektor.sayfalari_yukle(korpus)
    if not sayfalar:
        raise SystemExit(f"{korpus} altında .txt sayfa yok. Ham veri zip'ini data\\ham altına açtın mı?")
    print(f"{len(sayfalar)} sayfa okundu, indeks kuruluyor...")
    idx = vektor.Indeks.kur(sayfalar)
    print(f"{len(idx.parcalar)} parça hazır.")
    return idx


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="src.rag.cli")
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("indeks", "sorula", "degerlendir"):
        p = alt.add_parser(ad)
        p.add_argument("--korpus", default=KORPUS_VARSAYILAN)
        if ad == "sorula":
            p.add_argument("soru")
        if ad == "degerlendir":
            p.add_argument("--cikti", default="results/vektor-sonuc.json")
            p.add_argument("--sinir", type=int, default=0, help="yalnızca ilk N soru (deneme için)")
    a = ap.parse_args(argv)

    idx = _indeks(a.korpus)
    if a.komut == "indeks":
        return
    if a.komut == "sorula":
        v = vektor.cevapla(a.soru, idx)
        print(f"\nCevap: {v['answer']}\nSüre: {v['latency_ms']} ms\nBakılan kaynaklar: {', '.join(v['retrieved'])}")
        return

    sorular = vektor.sorulari_yukle()
    if a.sinir:
        sorular = sorular[: a.sinir]
    sonuc = vektor.degerlendir(sorular, idx)
    Path(a.cikti).parent.mkdir(parents=True, exist_ok=True)
    Path(a.cikti).write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    f1 = defaultdict(list)
    for q in sonuc["questions"]:
        f1[q["tur"]].append(token_f1(q["vector"]["answer"], q["gold"]))
        f1["TUMU"].append(f1[q["tur"]][-1])
    print(f"\n{len(sonuc['questions'])} soru çalıştı -> {a.cikti}\n")
    for tur in ("tek", "iki", "uc", "celiski", "TUMU"):
        if f1[tur]:
            print(f"  F1 {tur:8s} {sum(f1[tur]) / len(f1[tur]):.3f}  ({len(f1[tur])} soru)")
    ms = sorted(q["vector"]["latency_ms"] for q in sonuc["questions"])
    print(f"  p95 gecikme {ms[min(len(ms) - 1, max(0, -(-95 * len(ms) // 100) - 1))]} ms")


if __name__ == "__main__":
    main()
