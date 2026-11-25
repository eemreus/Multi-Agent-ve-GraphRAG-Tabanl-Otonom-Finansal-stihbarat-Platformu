"""PostgreSQL şeması testleri. İlk üçü veritabanı gerektirmez; sonuncusu DATABASE_URL ister."""
import os
import re
from pathlib import Path

import pytest

from db.sql_calistir import dosya_oku, deyimlere_bol

KOK = Path(__file__).resolve().parent.parent
SQL = (KOK / "db/sql/0001_ilk_sema.sql").read_text(encoding="utf-8")
ANAHTAR = {"PRIMARY", "UNIQUE", "CHECK", "FOREIGN", "CONSTRAINT", "REFERENCES", "DEFAULT", "NOT", "ON"}


def sql_tablolari() -> dict[str, set[str]]:
    sonuc = {}
    for ad, govde in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", SQL, re.S):
        kolonlar = set()
        for satir in govde.splitlines():
            ilk = satir.strip().split(" ")[0].rstrip(",")
            if ilk and ilk.isidentifier() and ilk.upper() not in ANAHTAR and satir.startswith("    ") \
                    and not satir.startswith("     "):
                kolonlar.add(ilk)
        sonuc[ad] = kolonlar
    return sonuc


def er_tablolari() -> set[str]:
    er = (KOK / "docs/05-er-diyagrami.md").read_text(encoding="utf-8")
    return {ad.lower() for ad in re.findall(r"^    ([A-Z_]+) \{", er, re.M)}


def test_sql_er_diyagramiyla_ayni_tablolari_olusturur():
    assert set(sql_tablolari()) == er_tablolari()
    assert len(er_tablolari()) == 16


def test_deyim_bolucu_plpgsql_blogunu_bozmaz():
    deyimler = deyimlere_bol(SQL)
    islev = [d for d in deyimler if d.startswith("CREATE FUNCTION")]
    assert len(islev) == 1 and "END IF;" in islev[0] and islev[0].rstrip().endswith("LANGUAGE plpgsql;")
    assert len(deyimler) == 24  # 16 tablo + 6 indeks + 1 işlev + 1 tetikleyici
    assert len(dosya_oku("0001_ilk_sema_geri.sql")) == 3


def test_modeller_sql_ile_ayni_tablo_ve_kolonlara_sahip():
    pytest.importorskip("sqlalchemy")
    from db.modeller import Base
    sql = sql_tablolari()
    assert set(Base.metadata.tables) == set(sql)
    for ad, tablo in Base.metadata.tables.items():
        assert {c.name for c in tablo.columns} == sql[ad], ad


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL yok (docker compose up -d postgres)")
def test_uydurma_atif_tetikleyicisi_gercek_veritabaninda():
    pytest.importorskip("psycopg")
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import DBAPIError

    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as c:
        tx = c.begin()
        try:
            # Geçici şema: asıl tablolar (alembic upgrade head) zaten kurulu olsa da test onlara dokunmaz,
            # sonunda geri sarılınca geçici şema da silinir.
            c.execute(text("CREATE SCHEMA test_atif"))
            c.execute(text("SET LOCAL search_path TO test_atif, public"))
            for d in dosya_oku("0001_ilk_sema.sql"):
                c.exec_driver_sql(d)
            c.execute(text("INSERT INTO users(email,password_hash) VALUES('a@b.c','x')"))
            c.execute(text("INSERT INTO research_sessions(user_id,query_text) SELECT id,'q' FROM users"))
            c.execute(text("INSERT INTO sources(url) VALUES ('http://s1'),('http://s2')"))
            c.execute(text("INSERT INTO reports(session_id) SELECT id FROM research_sessions"))
            c.execute(text("INSERT INTO claims(report_id,claim_text) SELECT id,'iddia' FROM reports"))
            c.execute(text("INSERT INTO retrievals(session_id,source_id) "
                           "SELECT rs.id,s.id FROM research_sessions rs, sources s WHERE s.url='http://s1'"))
            ekle = ("INSERT INTO citations(claim_id,source_id) "
                    "SELECT c.id,s.id FROM claims c, sources s WHERE s.url=:url")
            c.execute(text(ekle), {"url": "http://s1"})  # getirilmiş kaynak: kabul
            with pytest.raises(DBAPIError):
                c.execute(text(ekle), {"url": "http://s2"})  # getirilmemiş kaynak: reddedilir
        finally:
            tx.rollback()
