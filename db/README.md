# PostgreSQL şeması ve migration (Hafta 4)

Tablolar [docs/05-er-diyagrami.md](../docs/05-er-diyagrami.md) ile birebir aynıdır (16 tablo). Şema Alembic ile yönetilir.

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `sql/0001_ilk_sema.sql` | Tablolar, kısıtlar, indeksler ve uydurma atıf tetikleyicisi (kaynak gerçek bu dosya) |
| `sql/0001_ilk_sema_geri.sql` | Geri alma (tabloları siler) |
| `migrations/versions/0001_ilk_sema.py` | Alembic migration'ı, SQL dosyalarını çalıştırır |
| `modeller.py` | SQLAlchemy modelleri (sorgulama için) |
| `sql_calistir.py` | SQL dosyasını deyimlere bölen küçük yardımcı |

## Çalıştırma (Docker açıkken)

```powershell
git checkout main
git pull
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d postgres
$env:DATABASE_URL = "postgresql+psycopg://paragoz:paragoz-dev-sifre@localhost:5432/paragoz"
alembic upgrade head          # 16 tabloyu kurar
alembic downgrade base        # geri alır
python -m pytest -q           # veritabanı testi de çalışır (DATABASE_URL tanımlıyken)
```

Tabloları görmek için: `docker exec -it paragoz-postgres psql -U paragoz -d paragoz -c "\dt"`

## Uydurma atıf kuralı (REQ-06)

`citations` tablosuna eklenen her atıfın kaynağı, aynı araştırma oturumunda `retrievals` tablosuna girmiş olmalıdır.
Olmayan kaynağa atıf eklenirse veritabanı `check_violation` hatası verir. Bu kural bir tetikleyici (trigger) ile uygulanır.
