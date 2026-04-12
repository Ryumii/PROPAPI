"""Synchronous database helpers for ETL batch processing."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from etl.config import BATCH_SIZE, DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=2,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a DB session with automatic commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_postgis(session: Session) -> None:
    """Ensure PostGIS extension is enabled."""
    session.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    session.commit()


def register_data_source(
    session: Session,
    *,
    name: str,
    provider: str,
    url: str | None = None,
    license_type: str = "政府標準利用規約 2.0",
    coverage_area: str | None = None,
) -> int:
    """Register or update a data_source record. Returns source_id."""
    now = datetime.now(timezone.utc).isoformat()
    # Check if already exists
    row = session.execute(
        text("SELECT id FROM data_source WHERE name = :name"),
        {"name": name},
    ).first()

    if row:
        session.execute(
            text(
                "UPDATE data_source SET last_checked_at = :now, updated_at = NOW() "
                "WHERE id = :id"
            ),
            {"now": now, "id": row[0]},
        )
        session.commit()
        logger.info("Data source updated: %s (id=%d)", name, row[0])
        return row[0]

    result = session.execute(
        text(
            "INSERT INTO data_source "
            "(name, provider, url, license_type, last_checked_at, coverage_area, "
            " created_at, updated_at) "
            "VALUES (:name, :provider, :url, :license_type, :now, :coverage_area, "
            " NOW(), NOW()) "
            "RETURNING id"
        ),
        {
            "name": name,
            "provider": provider,
            "url": url,
            "license_type": license_type,
            "now": now,
            "coverage_area": coverage_area,
        },
    )
    source_id: int = result.scalar_one()
    session.commit()
    logger.info("Data source registered: %s (id=%d)", name, source_id)
    return source_id


def clear_table_for_prefecture(
    session: Session, table_name: str, prefecture: str
) -> int:
    """Delete rows matching a prefecture. Returns rows deleted."""
    # Parameterised WHERE — table name is trusted (hardcoded in each loader).
    result = session.execute(
        text(f"DELETE FROM {table_name} WHERE prefecture = :pref"),  # noqa: S608
        {"pref": prefecture},
    )
    count: int = result.rowcount  # type: ignore[assignment]
    session.commit()
    logger.info("Cleared %d rows from %s (prefecture=%s)", count, table_name, prefecture)
    return count


def batch_execute(
    session: Session,
    sql: str,
    rows: list[dict[str, Any]],
    *,
    batch_size: int = BATCH_SIZE,
    label: str = "",
) -> int:
    """Execute parameterised SQL in batches. Returns total row count."""
    if not rows:
        return 0

    stmt = text(sql)
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        session.execute(stmt, batch)
        session.commit()
        total += len(batch)
        if label:
            logger.info("  [%s] %d / %d rows", label, total, len(rows))

    return total
