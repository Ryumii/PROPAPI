"""Usage tracking & data change log models."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UsageLog(Base):
    __tablename__ = "usage_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    api_key_id: Mapped[int] = mapped_column(Integer, ForeignKey("api_key.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    request_address: Mapped[str | None] = mapped_column(Text)
    response_status: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_usage_log_api_key", "api_key_id"),
        Index("idx_usage_log_created", "created_at"),
    )


class DataChangeLog(Base):
    __tablename__ = "data_change_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("data_source.id"))

    __table_args__ = (
        Index("idx_data_change_table", "table_name", "record_id"),
    )
