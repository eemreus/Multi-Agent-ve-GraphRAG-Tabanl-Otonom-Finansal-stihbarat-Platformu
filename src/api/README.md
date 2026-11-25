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

## Telemetri ve önbellek (Hafta 4)

| Dosya | İş |
|---|---|
| `telemetri.py` | Her isteğin gecikmesini PostgreSQL `agent_logs` tablosuna yazar; `python -m src.api.telemetri` p50/p95 raporu verir |
| `onbellek.py` | Aynı soru için önbellek: Redis (`REDIS_URL`) ya da bellek; Redis kapalıysa sessizce devre dışı kalır |

Ortam değişkenleri (ikisi de isteğe bağlı; tanımlı değilse ilgili özellik kapalı kalır):

| Değişken | Etkisi |
|---|---|
| `DATABASE_URL` | Tanımlıysa her istek `agent_logs`'a yazılır |
| `REDIS_URL` | Tanımlıysa cevaplar Redis'te saklanır (`REDIS_TTL_SN`, varsayılan 3600 sn) |

```powershell
docker compose up -d postgres redis
alembic upgrade head
$env:DATABASE_URL = "postgresql+psycopg://paragoz:paragoz-dev-sifre@localhost:5432/paragoz"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:API_KEYS = "gelistirme-anahtari"
uvicorn src.api.main:app --reload
```

Kayıtları görmek ve p95'i okumak için:

```powershell
docker exec -it paragoz-postgres psql -U paragoz -d paragoz -c "SELECT event_type, latency_ms, error_code, created_at FROM agent_logs ORDER BY created_at DESC LIMIT 5"
python -m src.api.telemetri --saat 24
```

Kurallar:
- `event_type = 'sor'` modele giden istektir, `sor_onbellek` önbellek isabetidir. **p95 yalnızca `sor` kayıtlarından hesaplanır**; hızlı önbellek cevapları gecikme hedefini olduğundan iyi göstermesin diye ayrı sayılır.
- Yanıttaki `onbellek` alanı cevabın önbellekten gelip gelmediğini söyler.
- Ham soru loga yazılmaz, yalnızca kısa bir özet (`payload.soru_ozeti`) tutulur.
- Hatalı cevaplar önbelleğe girmez. Önbellek anahtarı modeli içerir; `OLLAMA_MODEL` değişince eski cevaplar kullanılmaz. Graf ya da istem değişirse Redis'i temizle: `docker exec paragoz-redis redis-cli FLUSHDB`.
- Telemetri ya da Redis çökse bile kullanıcı cevabını alır (hata loglanır).

## Sonraki adımlar
- Anahtarları `api_keys` tablosundan okumak (şimdilik `API_KEYS` ortam değişkeni)
- `/sor` isteğine `derinlik` alanı eklemek (`pipeline.derinlik_sinirla` hazır, 1-3)

## Mikro servis modu (Hafta 4)

Gateway ile GraphRAG ajanı ayrı süreçler olarak çalışabilir:

```
istemci --X-API-Key--> gateway (:8000) --X-Internal-Token--> graphrag-agent (:8001) --> Neo4j, Ollama
                          |-> Redis (önbellek), PostgreSQL (agent_logs)
```

| Servis | Dosya | Görevi |
|---|---|---|
| gateway | `src/api/main.py` | Kimlik, istek sınırı, önbellek, telemetri. Soruyu ajana iletir. |
| graphrag-agent | `src/agent/main.py` | Graf araması ve cevap üretimi. Yalnızca gateway çağırır (`POST /cevapla`). |

- `AGENT_URL` tanımlıysa gateway ajanı HTTP ile çağırır; tanımlı değilse hat gateway içinde çalışır (eski tek parça mod).
- İç servis `INTERNAL_TOKEN` ister. Token tanımlı değilse ajan her isteği reddeder.
- Ajan kapalıysa gateway `502`, zaman aşımında `504` döner.
- Docker ile hepsi: `docker compose up -d --build` (Ollama ana makinede açık olmalı; ajan ona `host.docker.internal` ile ulaşır).
- Elle: `uvicorn src.agent.main:app --port 8001` ve `$env:AGENT_URL="http://127.0.0.1:8001"; uvicorn src.api.main:app`.
- `data/` klasörü imaja kopyalanmaz, ajana salt okunur bağlanır.
