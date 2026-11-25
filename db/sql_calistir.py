"""SQL dosyalarını tek tek deyimlere böler (PL/pgSQL $$ blokları bölünmez)."""
from __future__ import annotations

from pathlib import Path

SQL_DIZIN = Path(__file__).parent / "sql"


def deyimlere_bol(sql: str) -> list[str]:
    """Noktalı virgülle biten deyimleri ayırır; $$ ... $$ içindeki noktalı virgüller korunur.
    '--' ile başlayan satır yorumları atılır."""
    satirlar = [s for s in sql.splitlines() if not s.lstrip().startswith("--")]
    deyimler, parca, blok_icinde = [], [], False
    for satir in satirlar:
        parca.append(satir)
        if satir.count("$$") % 2 == 1:
            blok_icinde = not blok_icinde
        if not blok_icinde and satir.rstrip().endswith(";"):
            d = "\n".join(parca).strip()
            if d:
                deyimler.append(d)
            parca = []
    kalan = "\n".join(parca).strip()
    if kalan:
        deyimler.append(kalan)
    return deyimler


def dosya_oku(ad: str) -> list[str]:
    return deyimlere_bol((SQL_DIZIN / ad).read_text(encoding="utf-8"))
