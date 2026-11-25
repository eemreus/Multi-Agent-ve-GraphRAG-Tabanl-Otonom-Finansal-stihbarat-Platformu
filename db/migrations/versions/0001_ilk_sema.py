"""İlk şema: 16 tablo, indeksler ve uydurma atıf tetikleyicisi

Revision ID: 0001
Revises:
"""
from alembic import op

from db.sql_calistir import dosya_oku

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _calistir(dosya: str) -> None:
    baglanti = op.get_bind()
    for deyim in dosya_oku(dosya):
        baglanti.exec_driver_sql(deyim)


def upgrade() -> None:
    _calistir("0001_ilk_sema.sql")


def downgrade() -> None:
    _calistir("0001_ilk_sema_geri.sql")
