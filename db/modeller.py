"""SQLAlchemy modelleri. Kaynak gerçek: db/sql/0001_ilk_sema.sql (docs/05-er-diyagrami.md ile aynı).
Tablolar Alembic migration'ı ile oluşturulur; bu modeller sorgulama ve sonraki migration'ların
otomatik üretimi içindir."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func,
                        text)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


def _fk(hedef: str, *, null: bool = False, silinince: str = "CASCADE", pk: bool = False):
    return mapped_column(UUID(as_uuid=True), ForeignKey(hedef, ondelete=silinince), nullable=null, primary_key=pk)


def _zaman(null: bool = False, varsayilan: bool = True):
    return mapped_column(DateTime(timezone=True), nullable=null,
                         server_default=func.now() if varsayilan else None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _id()
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), server_default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = _zaman()


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = _fk("users.id")
    key_hash: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = _zaman()
    revoked_at: Mapped[datetime | None] = _zaman(null=True, varsayilan=False)


class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[uuid.UUID] = _fk("users.id", pk=True)
    default_token_budget: Mapped[int] = mapped_column(Integer, server_default="20000")
    router_model: Mapped[str | None] = mapped_column(String(100))
    local_model: Mapped[str | None] = mapped_column(String(100))
    max_graph_depth: Mapped[int] = mapped_column(Integer, server_default="2")
    extra: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class ResearchSession(Base):
    __tablename__ = "research_sessions"
    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = _fk("users.id")
    query_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default="queued")
    token_budget: Mapped[int | None] = mapped_column(Integer)
    tokens_used: Mapped[int] = mapped_column(Integer, server_default="0")
    stop_reason: Mapped[str | None] = mapped_column(String(20))
    started_at: Mapped[datetime] = _zaman()
    finished_at: Mapped[datetime | None] = _zaman(null=True, varsayilan=False)


class SubQuery(Base):
    __tablename__ = "sub_queries"
    id: Mapped[uuid.UUID] = _id()
    session_id: Mapped[uuid.UUID] = _fk("research_sessions.id")
    parent_id: Mapped[uuid.UUID | None] = _fk("sub_queries.id", null=True, silinince="SET NULL")
    query_text: Mapped[str] = mapped_column(Text)
    iteration_no: Mapped[int] = mapped_column(Integer, server_default="0")
    info_gain: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), server_default="pending")


class Publisher(Base):
    __tablename__ = "publishers"
    id: Mapped[uuid.UUID] = _id()
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    source_type: Mapped[str | None] = mapped_column(String(20))
    base_reliability: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = _zaman()


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[uuid.UUID] = _id()
    publisher_id: Mapped[uuid.UUID | None] = _fk("publishers.id", null=True, silinince="SET NULL")
    url: Mapped[str] = mapped_column(Text, index=True)
    title: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = _zaman(null=True, varsayilan=False)
    fetched_at: Mapped[datetime] = _zaman()
    fetch_method: Mapped[str | None] = mapped_column(String(20))
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    snapshot_path: Mapped[str | None] = mapped_column(Text)
    text_length: Mapped[int | None] = mapped_column(Integer)
    reliability_score: Mapped[float | None] = mapped_column(Float)
    score_factors: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class Retrieval(Base):
    __tablename__ = "retrievals"
    id: Mapped[uuid.UUID] = _id()
    session_id: Mapped[uuid.UUID] = _fk("research_sessions.id")
    sub_query_id: Mapped[uuid.UUID | None] = _fk("sub_queries.id", null=True, silinince="SET NULL")
    source_id: Mapped[uuid.UUID] = _fk("sources.id")
    relevance_score: Mapped[float | None] = mapped_column(Float)


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    id: Mapped[uuid.UUID] = _id()
    source_id: Mapped[uuid.UUID] = _fk("sources.id")
    model: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    chunks_total: Mapped[int] = mapped_column(Integer, server_default="0")
    chunks_failed: Mapped[int] = mapped_column(Integer, server_default="0")
    nodes_created: Mapped[int] = mapped_column(Integer, server_default="0")
    relations_created: Mapped[int] = mapped_column(Integer, server_default="0")
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _zaman()


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("session_id", "version"),)
    id: Mapped[uuid.UUID] = _id()
    session_id: Mapped[uuid.UUID] = _fk("research_sessions.id")
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    summary_text: Mapped[str | None] = mapped_column(Text)
    overall_confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = _zaman()


class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[uuid.UUID] = _id()
    report_id: Mapped[uuid.UUID] = _fk("reports.id")
    order_no: Mapped[int] = mapped_column(Integer, server_default="0")
    claim_text: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    confidence_label: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), server_default="supported")


class Citation(Base):
    __tablename__ = "citations"
    id: Mapped[uuid.UUID] = _id()
    claim_id: Mapped[uuid.UUID] = _fk("claims.id")
    source_id: Mapped[uuid.UUID] = _fk("sources.id", silinince="RESTRICT")
    evidence_text: Mapped[str | None] = mapped_column(Text)
    similarity_score: Mapped[float | None] = mapped_column(Float)
    verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    accessed_at: Mapped[datetime] = _zaman()


class Contradiction(Base):
    __tablename__ = "contradictions"
    id: Mapped[uuid.UUID] = _id()
    report_id: Mapped[uuid.UUID] = _fk("reports.id")
    claim_a_id: Mapped[uuid.UUID] = _fk("claims.id")
    claim_b_id: Mapped[uuid.UUID] = _fk("claims.id")
    description: Mapped[str | None] = mapped_column(Text)


class CircularGroup(Base):
    __tablename__ = "circular_groups"
    id: Mapped[uuid.UUID] = _id()
    session_id: Mapped[uuid.UUID] = _fk("research_sessions.id")
    origin_source_id: Mapped[uuid.UUID | None] = _fk("sources.id", null=True, silinince="SET NULL")
    note: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = _zaman()


class CircularGroupMember(Base):
    __tablename__ = "circular_group_members"
    group_id: Mapped[uuid.UUID] = _fk("circular_groups.id", pk=True)
    source_id: Mapped[uuid.UUID] = _fk("sources.id", pk=True)


class AgentLog(Base):
    __tablename__ = "agent_logs"
    id: Mapped[uuid.UUID] = _id()
    session_id: Mapped[uuid.UUID | None] = _fk("research_sessions.id", null=True)
    agent_name: Mapped[str] = mapped_column(String(50))
    event_type: Mapped[str] = mapped_column(String(50))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = _zaman()
