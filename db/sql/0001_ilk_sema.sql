-- ParaGöz PostgreSQL ilk şema (docs/05-er-diyagrami.md ile birebir).
-- gen_random_uuid() PostgreSQL 13+ içinde yerleşiktir.

CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email         varchar(255) NOT NULL UNIQUE,
    password_hash varchar(255) NOT NULL,
    full_name     varchar(255),
    role          varchar(20)  NOT NULL DEFAULT 'analyst' CHECK (role IN ('analyst', 'admin')),
    is_active     boolean      NOT NULL DEFAULT true,
    created_at    timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE api_keys (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash   varchar(128) NOT NULL UNIQUE,
    name       varchar(100),
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz
);

CREATE TABLE user_settings (
    user_id              uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    default_token_budget integer NOT NULL DEFAULT 20000,
    router_model         varchar(100),
    local_model          varchar(100),
    max_graph_depth      integer NOT NULL DEFAULT 2 CHECK (max_graph_depth BETWEEN 1 AND 3),
    extra                jsonb   NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE research_sessions (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_text  text NOT NULL,
    status      varchar(20) NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'running', 'done', 'failed', 'cancelled')),
    token_budget integer,
    tokens_used  integer NOT NULL DEFAULT 0,
    stop_reason  varchar(20) CHECK (stop_reason IN ('info_gain', 'budget', 'manual', 'error')),
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz
);

CREATE TABLE sub_queries (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  uuid NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    parent_id   uuid REFERENCES sub_queries(id) ON DELETE SET NULL,
    query_text  text NOT NULL,
    iteration_no integer NOT NULL DEFAULT 0,
    info_gain   double precision,
    status      varchar(20) NOT NULL DEFAULT 'pending'
);

CREATE TABLE publishers (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    domain           varchar(255) NOT NULL UNIQUE,
    name             varchar(255),
    source_type      varchar(20) CHECK (source_type IN ('resmi', 'haber', 'blog', 'sosyal')),
    base_reliability double precision CHECK (base_reliability BETWEEN 0 AND 1),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sources (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    publisher_id      uuid REFERENCES publishers(id) ON DELETE SET NULL,
    url               text NOT NULL,
    title             text,
    published_at      timestamptz,
    fetched_at        timestamptz NOT NULL DEFAULT now(),
    fetch_method      varchar(20) CHECK (fetch_method IN ('searxng', 'proxy', 'kap_api', 'rss')),
    http_status       integer,
    content_hash      varchar(64),
    snapshot_path     text,
    text_length       integer,
    reliability_score double precision CHECK (reliability_score BETWEEN 0 AND 1),
    score_factors     jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE retrievals (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      uuid NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    sub_query_id    uuid REFERENCES sub_queries(id) ON DELETE SET NULL,
    source_id       uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    relevance_score double precision
);

CREATE TABLE extraction_runs (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id         uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    model             varchar(100),
    status            varchar(20) NOT NULL CHECK (status IN ('ok', 'partial', 'failed', 'skipped')),
    chunks_total      integer NOT NULL DEFAULT 0,
    chunks_failed     integer NOT NULL DEFAULT 0,
    nodes_created     integer NOT NULL DEFAULT 0,
    relations_created integer NOT NULL DEFAULT 0,
    tokens_in         integer,
    tokens_out        integer,
    latency_ms        integer,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reports (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id         uuid NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    version            integer NOT NULL DEFAULT 1,
    summary_text       text,
    overall_confidence double precision CHECK (overall_confidence BETWEEN 0 AND 1),
    created_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (session_id, version)
);

CREATE TABLE claims (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id        uuid NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    order_no         integer NOT NULL DEFAULT 0,
    claim_text       text NOT NULL,
    confidence_score double precision CHECK (confidence_score BETWEEN 0 AND 1),
    confidence_label varchar(10) CHECK (confidence_label IN ('yüksek', 'orta', 'düşük')),
    status           varchar(20) NOT NULL DEFAULT 'supported'
                     CHECK (status IN ('supported', 'contradicted', 'dropped'))
);

CREATE TABLE citations (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id         uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    source_id        uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    evidence_text    text,
    similarity_score double precision,
    verified         boolean NOT NULL DEFAULT false,
    accessed_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE contradictions (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id   uuid NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    claim_a_id  uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    claim_b_id  uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    description text,
    CHECK (claim_a_id <> claim_b_id)
);

CREATE TABLE circular_groups (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       uuid NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    origin_source_id uuid REFERENCES sources(id) ON DELETE SET NULL,
    note             text,
    detected_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE circular_group_members (
    group_id  uuid NOT NULL REFERENCES circular_groups(id) ON DELETE CASCADE,
    source_id uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, source_id)
);

CREATE TABLE agent_logs (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid REFERENCES research_sessions(id) ON DELETE CASCADE,
    agent_name varchar(50) NOT NULL,
    event_type varchar(50) NOT NULL,
    tokens_in  integer,
    tokens_out integer,
    latency_ms integer,
    error_code varchar(50),
    payload    jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- İndeksler (docs/05-er-diyagrami.md önerisi)
CREATE INDEX ix_sources_url           ON sources (url);
CREATE INDEX ix_sources_content_hash  ON sources (content_hash);
CREATE INDEX ix_retrievals_session    ON retrievals (session_id);
CREATE INDEX ix_claims_report         ON claims (report_id);
CREATE INDEX ix_citations_claim       ON citations (claim_id);
CREATE INDEX ix_agent_logs_session_ts ON agent_logs (session_id, created_at);

-- Uydurma atıf kuralı (REQ-06): bir atıfın kaynağı, aynı oturumda getirilmiş (retrievals) olmalı.
CREATE FUNCTION citation_source_retrieved() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM claims c
        JOIN reports r      ON r.id = c.report_id
        JOIN retrievals rt  ON rt.session_id = r.session_id
        WHERE c.id = NEW.claim_id AND rt.source_id = NEW.source_id
    ) THEN
        RAISE EXCEPTION 'Atıf kaynağı bu oturumda getirilmemiş'
            USING ERRCODE = 'check_violation', DETAIL = NEW.source_id::text;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_citation_source_retrieved
    BEFORE INSERT OR UPDATE OF claim_id, source_id ON citations
    FOR EACH ROW EXECUTE FUNCTION citation_source_retrieved();
