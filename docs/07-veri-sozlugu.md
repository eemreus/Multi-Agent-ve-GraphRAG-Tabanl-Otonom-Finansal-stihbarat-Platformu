# Veri Sözlüğü

Bu belge [05-er-diyagrami.md](05-er-diyagrami.md) içindeki PostgreSQL tablolarının alan açıklamalarını içerir. Neo4j düğüm ve ilişki özellikleri [06-neo4j-graf-semasi.md](06-neo4j-graf-semasi.md) dosyasındadır.

**Genel kurallar:** Tüm `id` alanları UUID'dir. Zamanlar `timestamptz` (UTC) saklanır. `PK` birincil anahtar, `FK` yabancı anahtar, `UK` benzersiz, `NN` boş olamaz demektir.

## users

Sistemi kullanan kişiler.

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Kullanıcı kimliği | `3f2a...` |
| email | varchar(255) | UK, NN | Giriş e-postası | `analist@ornek.com` |
| password_hash | varchar(255) | NN | Parolanın hash'i (düz metin saklanmaz) | `$argon2id$...` |
| full_name | varchar(120) | NN | Ad soyad | `Ayşe Yılmaz` |
| role | varchar(20) | NN | `analyst` veya `admin` | `analyst` |
| is_active | bool | NN, varsayılan true | Hesap aktif mi | `true` |
| created_at | timestamptz | NN | Kayıt zamanı | `2026-11-02T10:00:00Z` |

## api_keys

Harici yazılımların API erişimi (REQ-05).

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Anahtar kimliği | |
| user_id | uuid | FK users.id, NN | Sahibi | |
| key_hash | varchar(255) | UK, NN | Anahtarın hash'i, düz anahtar yalnızca oluşturulurken bir kez gösterilir | |
| name | varchar(80) | NN | Anahtar adı | `ERP entegrasyonu` |
| created_at | timestamptz | NN | Oluşturma zamanı | |
| revoked_at | timestamptz | | İptal zamanı, boşsa geçerli | |

## user_settings

Kullanıcı başına model ve bütçe ayarları.

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| user_id | uuid | PK, FK users.id | Ayarların sahibi | |
| default_token_budget | int | NN, varsayılan 50000 | Yeni araştırmaların varsayılan token bütçesi | `50000` |
| router_model | varchar(80) | | Orkestratör ve rapor için API modeli | |
| local_model | varchar(80) | | Çıkarım için yerel model | `llama3` |
| max_graph_depth | int | NN, varsayılan 3 | GraphRAG sorgu derinlik sınırı (2-3) | `3` |
| extra | jsonb | | Diğer ayarlar | `{}` |

## research_sessions

Kullanıcının başlattığı her araştırma.

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Oturum kimliği | |
| user_id | uuid | FK users.id, NN | Başlatan kullanıcı | |
| query_text | text | NN | Kullanıcının doğal dilde sorusu | `X şirketinin yeni yönetim kurulu üyesi kimlerle ortaklık yaptı?` |
| status | varchar(20) | NN | `queued`, `running`, `done`, `failed`, `cancelled` | `running` |
| token_budget | int | NN | Bu oturum için token üst sınırı | `50000` |
| tokens_used | int | NN, varsayılan 0 | Harcanan token | `18240` |
| stop_reason | varchar(20) | | `info_gain` (bilgi kazancı eşiği), `budget`, `manual`, `error` | `info_gain` |
| started_at | timestamptz | NN | Başlangıç | |
| finished_at | timestamptz | | Bitiş, çalışırken boş | |

## sub_queries

Orkestratörün ürettiği alt sorgular (ReAct döngüsünün her adımı).

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Alt sorgu kimliği | |
| session_id | uuid | FK research_sessions.id, NN | Bağlı oturum | |
| parent_id | uuid | FK sub_queries.id | Bu sorguyu türeten sorgu, kök sorgularda boş | |
| query_text | text | NN | Arama sorgusu | `X şirketi yönetim kurulu atama KAP` |
| iteration_no | int | NN | Döngü sırası | `2` |
| info_gain | float | | Bu adımın bilgi kazancı, 0-1 | `0.12` |
| status | varchar(20) | NN | `pending`, `done`, `failed` | `done` |

## publishers

Yayıncı (site) profili. Güvenilirlik puanının tabanı.

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Yayıncı kimliği | |
| domain | varchar(255) | UK, NN | Alan adı | `kap.org.tr` |
| name | varchar(255) | | Yayıncı adı | `Kamuyu Aydınlatma Platformu` |
| source_type | varchar(20) | NN | `resmi`, `haber`, `blog`, `sosyal` | `resmi` |
| base_reliability | float | NN | Başlangıç güvenilirliği, 0-1 | `0.95` |
| updated_at | timestamptz | NN | Son güncelleme | |

## sources

Çekilen her web sayfası. Aynı URL farklı zamanda çekilirse ayrı satır olur.

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Kaynak kimliği, Neo4j `source_ids` bu alana işaret eder | |
| publisher_id | uuid | FK publishers.id | Yayıncı | |
| url | text | NN | Sayfa adresi (tıklanabilir bağlantı, REQ-03) | `https://...` |
| title | text | | Sayfa başlığı | |
| published_at | timestamptz | | Yayın tarihi (güncellik puanı için) | |
| fetched_at | timestamptz | NN | Erişim tarihi, raporda gösterilir | |
| fetch_method | varchar(20) | NN | `searxng`, `proxy`, `kap_api`, `rss` | `searxng` |
| http_status | int | | Çekim sonucu | `200` |
| content_hash | varchar(64) | | İçerik özeti, kopya tespiti için | |
| snapshot_path | text | | Dondurulmuş sayfa dosyası (test kümesi için) | `snapshots/ab12.html` |
| text_length | int | | Temizlenmiş metin uzunluğu | `4821` |
| reliability_score | float | | Güvenilirlik puanı, 0-1 | `0.82` |
| score_factors | jsonb | | Puanın bileşenleri (kaynak türü, güncellik, yayıncı geçmişi) | `{"tur":0.9,"guncel":0.7}` |

## retrievals

Hangi oturumda hangi alt sorgu hangi kaynağı getirdi. Atıf doğrulamasının dayanağıdır (REQ-06).

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Kayıt kimliği | |
| session_id | uuid | FK research_sessions.id, NN | Oturum | |
| sub_query_id | uuid | FK sub_queries.id, NN | Getiren alt sorgu | |
| source_id | uuid | FK sources.id, NN | Getirilen kaynak | |
| relevance_score | float | | Sorguyla ilgisi, 0-1 | `0.74` |

## extraction_runs

Bir kaynaktan graf çıkarımı denemesinin özeti (REQ-02).

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Çalıştırma kimliği | |
| source_id | uuid | FK sources.id, NN | İşlenen kaynak | |
| model | varchar(80) | NN | Kullanılan model | `llama3` |
| status | varchar(20) | NN | `ok`, `partial`, `failed`, `skipped` | `partial` |
| chunks_total | int | NN | Toplam chunk | `6` |
| chunks_failed | int | NN | Başarısız chunk | `1` |
| nodes_created | int | NN | Yeni düğüm sayısı | `9` |
| relations_created | int | NN | Yeni ilişki sayısı | `14` |
| tokens_in | int | NN | Girdi token | |
| tokens_out | int | NN | Çıktı token | |
| latency_ms | int | NN | Süre | `3400` |
| created_at | timestamptz | NN | Zaman | |

## reports

Bir oturumun ürettiği brifing. Tekrar üretilirse `version` artar.

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Rapor kimliği | |
| session_id | uuid | FK research_sessions.id, NN | Oturum | |
| version | int | NN, varsayılan 1 | Rapor sürümü | `1` |
| summary_text | text | NN | Brifing özeti | |
| overall_confidence | float | | Genel güven, 0-1 | `0.78` |
| created_at | timestamptz | NN | Zaman | |

## claims

Rapordaki her iddia.

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | İddia kimliği | |
| report_id | uuid | FK reports.id, NN | Rapor | |
| order_no | int | NN | Rapordaki sırası | `3` |
| claim_text | text | NN | İddia metni | |
| confidence_score | float | NN | Güven puanı, 0-1 | `0.64` |
| confidence_label | varchar(10) | NN | `yüksek`, `orta`, `düşük` (güven damgası, REQ-04) | `orta` |
| status | varchar(20) | NN | `supported`, `contradicted`, `dropped` | `supported` |

## citations

İddia ile kaynağı bağlayan atıf. Her iddianın en az bir atfı olmalıdır (REQ-03).

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Atıf kimliği | |
| claim_id | uuid | FK claims.id, NN | İddia | |
| source_id | uuid | FK sources.id, NN | Atıf yapılan kaynak. Aynı oturumda `retrievals`'a girmiş olmalı | |
| evidence_text | text | | Kaynaktan ilgili kısa kanıt | |
| similarity_score | float | | İddia ile kaynak metni anlam benzerliği, 0-1 | `0.88` |
| verified | bool | NN | Doğrulama geçti mi. `false` ise uydurma atıf adayıdır | `true` |
| accessed_at | timestamptz | NN | Erişim tarihi | |

## contradictions

Birbiriyle çelişen iki iddia (REQ-04).

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Kayıt kimliği | |
| report_id | uuid | FK reports.id, NN | Rapor | |
| claim_a_id | uuid | FK claims.id, NN | Birinci iddia | |
| claim_b_id | uuid | FK claims.id, NN | Çelişen iddia | |
| description | text | | Çelişkinin kısa açıklaması | |

## circular_groups

Aynı ilk habere dayanan kaynak kümesi (dairesel raporlama).

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Küme kimliği | |
| session_id | uuid | FK research_sessions.id, NN | Oturum | |
| origin_source_id | uuid | FK sources.id | Tespit edilen ilk haber | |
| note | text | | Tespit notu | |
| detected_at | timestamptz | NN | Tespit zamanı | |

## circular_group_members

Kümeye dahil kaynaklar. Bu kaynaklar güven hesabında tek bağımsız kaynak sayılır.

| Alan | Tip | Kısıt | Açıklama |
|------|-----|-------|----------|
| group_id | uuid | PK, FK circular_groups.id | Küme |
| source_id | uuid | PK, FK sources.id | Üye kaynak |

## agent_logs

Ajanların işlem kayıtları. p@95 gecikme, token harcaması ve uydurma atıf oranı buradan hesaplanır.

| Alan | Tip | Kısıt | Açıklama | Örnek |
|------|-----|-------|----------|-------|
| id | uuid | PK | Kayıt kimliği | |
| session_id | uuid | FK research_sessions.id | Oturum | |
| agent_name | varchar(40) | NN | `orchestrator`, `research`, `extraction`, `verification`, `report` | `extraction` |
| event_type | varchar(60) | NN | Olay türü | `extraction_retry`, `fabricated_citation` |
| tokens_in | int | | Girdi token | |
| tokens_out | int | | Çıktı token | |
| latency_ms | int | | Süre | |
| error_code | varchar(60) | | Hata kodu | |
| payload | jsonb | | Ek ayrıntı | |
| created_at | timestamptz | NN | Zaman | |

## Ölçüt eşlemesi

| Hedef | Hesaplandığı yer |
|-------|------------------|
| Uydurma atıf oranı < %5 | `citations.verified = false` sayısı / toplam atıf, ve `agent_logs.event_type = 'fabricated_citation'` |
| p@95 gecikme | `agent_logs.latency_ms` yüzdelik dilimi |
| Token harcaması | `research_sessions.tokens_used`, `agent_logs.tokens_in/out` |
