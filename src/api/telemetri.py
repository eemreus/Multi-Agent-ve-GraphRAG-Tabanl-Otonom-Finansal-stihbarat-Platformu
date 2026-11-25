"""Telemetri: her API isteğinin gecikmesini PostgreSQL `agent_logs` tablosuna yazar (p95 ölçümü).

Ölçüm hatası isteği asla bozmaz: yazma başarısız olursa uyarı loglanır, kullanıcı cevabını alır.
Rapor: python -m src.api.telemetri --saat 24   (DATABASE_URL tanımlı olmalı)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Callable

log = logging.getLogger(__name__)

EKLE = ("INSERT INTO agent_logs (agent_name, event_type, tokens_in, tokens_out, latency_ms, error_code, payload) "
        "VALUES (:agent_name, :event_type, :tokens_in, :tokens_out, :latency_ms, :error_code, "
        "CAST(:payload AS jsonb))")

# p95 yalnızca modele giden, hatasız istekler üzerinden hesaplanır; önbellek isabetleri ayrı sayılır
# (yoksa hızlı önbellek cevapları p95'i olduğundan iyi gösterir).
RAPOR = ("SELECT count(*) FILTER (WHERE event_type = 'sor' AND error_code IS NULL) AS model_istegi, "
         "count(*) FILTER (WHERE event_type = 'sor_onbellek') AS onbellek_isabeti, "
         "count(*) FILTER (WHERE event_type = 'sor' AND error_code IS NOT NULL) AS hata, "
         "percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms) "
         "FILTER (WHERE event_type = 'sor' AND error_code IS NULL) AS p50_ms, "
         "percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) "
         "FILTER (WHERE event_type = 'sor' AND error_code IS NULL) AS p95_ms, "
         "coalesce(sum(tokens_in), 0) AS toplam_girdi_token, coalesce(sum(tokens_out), 0) AS toplam_cikti_token "
         "FROM agent_logs WHERE agent_name = 'graphrag' AND created_at >= now() - make_interval(hours => :saat)")


class AgentLogYazici:
    """SorServisi(telemetri=AgentLogYazici(calistir)). calistir(sql, parametreler) bir SQL çalıştırır."""

    def __init__(self, calistir: Callable[[str, dict], None]):
        self.calistir = calistir

    def __call__(self, olay: dict) -> None:
        try:
            self.calistir(EKLE, {
                "agent_name": olay.get("agent_name", "graphrag"),
                "event_type": olay.get("event_type", "sor"),
                "tokens_in": olay.get("tokens_in"),
                "tokens_out": olay.get("tokens_out"),
                "latency_ms": olay.get("latency_ms"),
                "error_code": olay.get("error_code"),
                "payload": json.dumps(olay.get("payload") or {}, ensure_ascii=False),
            })
        except Exception as e:  # ölçüm hatası isteği bozmaz
            log.warning("agent_logs yazılamadı: %s", type(e).__name__)


class Postgres:
    """SQLAlchemy ile küçük bir sarmalayıcı (SQLAlchemy ve psycopg ilk kullanımda yüklenir)."""

    def __init__(self, url: str):
        from sqlalchemy import create_engine
        self.engine = create_engine(url, pool_pre_ping=True)

    def calistir(self, sql: str, parametreler: dict) -> None:
        from sqlalchemy import text
        with self.engine.begin() as c:
            c.execute(text(sql), parametreler)

    def sorgula(self, sql: str, parametreler: dict) -> list[dict]:
        from sqlalchemy import text
        with self.engine.connect() as c:
            return [dict(r) for r in c.execute(text(sql), parametreler).mappings().all()]


def ortamdan() -> AgentLogYazici | None:
    """DATABASE_URL tanımlıysa yazıcı döner; yoksa telemetri kapalı kalır (geliştirmede veritabanı şart değil)."""
    url = os.getenv("DATABASE_URL")
    return AgentLogYazici(Postgres(url).calistir) if url else None


def rapor(sorgula: Callable[[str, dict], list[dict]], saat: int = 24) -> dict:
    satir = (sorgula(RAPOR, {"saat": int(saat)}) or [{}])[0]
    return {k: (round(float(v), 1) if k.endswith("_ms") and v is not None else v) for k, v in satir.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="agent_logs üzerinden p50/p95 gecikme raporu")
    ap.add_argument("--saat", type=int, default=24, help="son kaç saat (varsayılan 24)")
    a = ap.parse_args(argv)
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL tanımlı değil.")
        return 1
    r = rapor(Postgres(url).sorgula, a.saat)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    p95 = r.get("p95_ms")
    print(f"token: {r.get('toplam_girdi_token', 0)} girdi, {r.get('toplam_cikti_token', 0)} çıktı")
    if p95 is not None:
        print(f"p95 = {p95} ms (hedef 2500 ms): {'hedefte' if p95 < 2500 else 'hedefin üstünde'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
