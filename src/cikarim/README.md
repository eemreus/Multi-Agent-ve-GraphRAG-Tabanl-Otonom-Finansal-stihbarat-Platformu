# Bilgi çıkarım ajanı (Hafta 4, REQ-05)

Metinden varlık ve ilişki çıkarır, kaynak id'siyle Neo4j'ye yazar. GraphRAG ajanından bağımsız bir servistir.

| Dosya | İş |
|---|---|
| `servis.py` | `cikar_ve_yaz(metin, kaynak_id, generate, run, model)`: parçala, çıkar, kanıtı metinde olmayan ilişkiyi at, yaz |
| `main.py` | FastAPI: `GET /saglik`, `POST /cikar` (`X-Internal-Token` ister) |

Çıkarım mantığı `src/graf/extractor.py` içinde, burası onu servis haline getirir.

## Çalıştırma
- Docker: `docker compose up -d --build`, sonra http://127.0.0.1:8002/docs (yalnızca bu bilgisayardan erişilir).
- Elle: `uvicorn src.cikarim.main:app --port 8002` (Neo4j ve Ollama açık olmalı).
- Swagger'da `X-Internal-Token` alanına `.env` içindeki `INTERNAL_TOKEN` değerini yaz (varsayılan `gelistirme-ic-anahtar`).

## İstek
```json
{"kaynak_id": "deneme1", "metin": "Koç Holding, Tüpraş şirketinin yüzde 51 hissesine sahiptir.", "yaz": false}
```
`yaz: false` yalnızca çıkarır, Neo4j'ye yazmaz. Yanıt: varlık, ilişki, atılan (kanıtsız) ilişki, hatalı parça sayıları ve `yazildi`.
Büyük metinde Ollama dakikalar sürebilir; metin sınırı 200000 karakter.
