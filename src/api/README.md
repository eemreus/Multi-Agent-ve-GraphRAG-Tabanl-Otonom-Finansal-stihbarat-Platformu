# ParaGöz API (Hafta 4, REQ-05)

GraphRAG hattını HTTP üzerinden sunar. Swagger (OpenAPI) belgesi otomatik üretilir.

| Dosya | İş |
|---|---|
| `main.py` | FastAPI uygulaması: `GET /saglik`, `POST /sor` |
| `guvenlik.py` | API anahtarı doğrulama (`X-API-Key`) ve kayan pencereli istek sınırı |
| `servis.py` | Soru temizleme, GraphRAG çağrısı, telemetri kancası (`telemetri(olay)`) |

## Çalıştırma (Neo4j ve Ollama açıkken)

```powershell
pip install -r requirements.txt
$env:API_KEYS = "gelistirme-anahtari"
uvicorn src.api.main:app --reload
```

- Swagger: http://localhost:8000/docs  ("Authorize" yerine her istekte `X-API-Key` başlığını doldurun)
- Deneme: `curl -X POST http://localhost:8000/sor -H "X-API-Key: gelistirme-anahtari" -H "Content-Type: application/json" -d "{\"soru\":\"Murat Pınar daha önce hangi şirketin CEO'suydu?\"}"`

## Hata kodları
- `401`: anahtar yok ya da geçersiz
- `422`: soru 3-500 karakter dışında
- `429`: dakikadaki istek sınırı aşıldı (`Retry-After` başlığı bekleme süresini verir)

## Sonraki adımlar (Sıla)
- `SorServisi(telemetri=...)`: her isteğin gecikmesini PostgreSQL `agent_logs` tablosuna yaz (p95 ölçümü)
- Redis cache: aynı soruyu tekrar modele göndermemek için `SorServisi` önüne
- Anahtarları `api_keys` tablosundan okumak (şimdilik `API_KEYS` ortam değişkeni)
