# ER Diyagramı (PostgreSQL)

Sistem hibrit depolama kullanır: ilişkisel veri (kullanıcı, oturum, kaynak, iddia, log) PostgreSQL'de, bilgi grafiği Neo4j'de tutulur. Bu belge PostgreSQL tarafını gösterir. Neo4j şeması için bkz. [06-neo4j-graf-semasi.md](06-neo4j-graf-semasi.md), alan açıklamaları için bkz. [07-veri-sozlugu.md](07-veri-sozlugu.md).

```mermaid
erDiagram
    USERS ||--o{ API_KEYS : "sahiptir"
    USERS ||--|| USER_SETTINGS : "ayarlar"
    USERS ||--o{ RESEARCH_SESSIONS : "başlatır"
    RESEARCH_SESSIONS ||--o{ SUB_QUERIES : "ayrılır"
    SUB_QUERIES ||--o{ SUB_QUERIES : "türetir"
    RESEARCH_SESSIONS ||--o{ RETRIEVALS : "toplar"
    SUB_QUERIES ||--o{ RETRIEVALS : "getirir"
    SOURCES ||--o{ RETRIEVALS : "getirilir"
    PUBLISHERS ||--o{ SOURCES : "yayımlar"
    SOURCES ||--o{ EXTRACTION_RUNS : "işlenir"
    RESEARCH_SESSIONS ||--o{ REPORTS : "üretir"
    REPORTS ||--o{ CLAIMS : "içerir"
    CLAIMS ||--o{ CITATIONS : "dayanır"
    SOURCES ||--o{ CITATIONS : "atıf alır"
    REPORTS ||--o{ CONTRADICTIONS : "işaretler"
    CLAIMS ||--o{ CONTRADICTIONS : "iddia A"
    CLAIMS ||--o{ CONTRADICTIONS : "iddia B"
    RESEARCH_SESSIONS ||--o{ CIRCULAR_GROUPS : "tespit eder"
    SOURCES ||--o{ CIRCULAR_GROUPS : "ilk haber"
    CIRCULAR_GROUPS ||--o{ CIRCULAR_GROUP_MEMBERS : "kapsar"
    SOURCES ||--o{ CIRCULAR_GROUP_MEMBERS : "üyedir"
    RESEARCH_SESSIONS ||--o{ AGENT_LOGS : "kaydeder"

    USERS {
        uuid id PK
        varchar email UK
        varchar password_hash
        varchar full_name
        varchar role "analyst veya admin"
        bool is_active
        timestamptz created_at
    }
    API_KEYS {
        uuid id PK
        uuid user_id FK
        varchar key_hash UK
        varchar name
        timestamptz created_at
        timestamptz revoked_at
    }
    USER_SETTINGS {
        uuid user_id PK, FK
        int default_token_budget
        varchar router_model
        varchar local_model
        int max_graph_depth
        jsonb extra
    }
    RESEARCH_SESSIONS {
        uuid id PK
        uuid user_id FK
        text query_text
        varchar status "queued running done failed cancelled"
        int token_budget
        int tokens_used
        varchar stop_reason "info_gain budget manual error"
        timestamptz started_at
        timestamptz finished_at
    }
    SUB_QUERIES {
        uuid id PK
        uuid session_id FK
        uuid parent_id FK "boş olabilir"
        text query_text
        int iteration_no
        float info_gain
        varchar status
    }
    PUBLISHERS {
        uuid id PK
        varchar domain UK
        varchar name
        varchar source_type "resmi haber blog sosyal"
        float base_reliability
        timestamptz updated_at
    }
    SOURCES {
        uuid id PK
        uuid publisher_id FK
        text url
        text title
        timestamptz published_at
        timestamptz fetched_at "erişim tarihi"
        varchar fetch_method "searxng proxy kap_api rss"
        int http_status
        varchar content_hash
        text snapshot_path "dondurulmuş sayfa"
        int text_length
        float reliability_score
        jsonb score_factors
    }
    RETRIEVALS {
        uuid id PK
        uuid session_id FK
        uuid sub_query_id FK
        uuid source_id FK
        float relevance_score
    }
    EXTRACTION_RUNS {
        uuid id PK
        uuid source_id FK
        varchar model
        varchar status "ok partial failed skipped"
        int chunks_total
        int chunks_failed
        int nodes_created
        int relations_created
        int tokens_in
        int tokens_out
        int latency_ms
        timestamptz created_at
    }
    REPORTS {
        uuid id PK
        uuid session_id FK
        int version
        text summary_text
        float overall_confidence
        timestamptz created_at
    }
    CLAIMS {
        uuid id PK
        uuid report_id FK
        int order_no
        text claim_text
        float confidence_score
        varchar confidence_label "yüksek orta düşük"
        varchar status "supported contradicted dropped"
    }
    CITATIONS {
        uuid id PK
        uuid claim_id FK
        uuid source_id FK
        text evidence_text
        float similarity_score
        bool verified
        timestamptz accessed_at
    }
    CONTRADICTIONS {
        uuid id PK
        uuid report_id FK
        uuid claim_a_id FK
        uuid claim_b_id FK
        text description
    }
    CIRCULAR_GROUPS {
        uuid id PK
        uuid session_id FK
        uuid origin_source_id FK "ilk haber"
        text note
        timestamptz detected_at
    }
    CIRCULAR_GROUP_MEMBERS {
        uuid group_id PK, FK
        uuid source_id PK, FK
    }
    AGENT_LOGS {
        uuid id PK
        uuid session_id FK
        varchar agent_name
        varchar event_type
        int tokens_in
        int tokens_out
        int latency_ms
        varchar error_code
        jsonb payload
        timestamptz created_at
    }
```

## Tablo grupları

| Grup | Tablolar | Amaç |
|------|----------|------|
| Kullanıcı ve erişim | `users`, `api_keys`, `user_settings` | Kimlik doğrulama, API erişimi (REQ-05), token bütçesi ve model ayarları |
| Araştırma süreci | `research_sessions`, `sub_queries`, `retrievals` | Sorgunun alt sorulara bölünmesi ve toplanan kaynaklar (REQ-01) |
| Kaynak ve güvenilirlik | `publishers`, `sources`, `circular_groups`, `circular_group_members` | Kaynak kaydı, dondurulmuş sayfa, güven puanı, dairesel raporlama tespiti (REQ-04) |
| Graf çıkarımı | `extraction_runs` | Her kaynaktan kaç düğüm ve ilişki çıkarıldığı (REQ-02) |
| Rapor ve atıf | `reports`, `claims`, `citations`, `contradictions` | Her iddianın kaynağı, erişim tarihi, çelişkiler (REQ-03, REQ-04, REQ-06) |
| Ölçüm | `agent_logs` | Token, gecikme ve hata kayıtları (p@95, uydurma atıf oranı) |

## Neo4j ile bağlantı

PostgreSQL ve Neo4j arasındaki köprü `sources.id` alanıdır. Graftaki her ilişkinin `source_ids` listesi, `sources` tablosundaki kayıtlara işaret eder. Böylece bir ilişkiye bakıp "bu bilgi hangi sayfadan, ne zaman çekildi?" sorusu yanıtlanabilir.

## Tasarım kararları

- **Kimlikler UUID:** Servisler arası çakışma olmaz, tahmin edilemez.
- **`sources` tablosu çekim kaydıdır:** Aynı URL farklı zamanlarda çekilirse ayrı satır olur. Aynı içerik `content_hash` ile tespit edilir. `fetched_at` doğrudan raporda gösterilen erişim tarihidir.
- **Uydurma atıf kontrolü (REQ-06):** `citations.source_id`, mutlaka aynı oturumda `retrievals` tablosuna girmiş bir kaynağa işaret etmelidir. Bu koşulu sağlamayan atıf birinci sınıf hata olarak `agent_logs`'a yazılır.
- **Çelişki ve dairesel raporlama:** `contradictions` iki iddiayı, `circular_groups` ise aynı ilk habere dayanan kaynak kümesini kaydeder. Güven puanı hesaplanırken bu kaynaklar tek bağımsız kaynak sayılır.
- **Migration:** Şema Alembic ile yönetilir (Hafta 4 teslimi).
- **İndeksler (öneri):** `sources(url)`, `sources(content_hash)`, `retrievals(session_id)`, `claims(report_id)`, `citations(claim_id)`, `agent_logs(session_id, created_at)`.
