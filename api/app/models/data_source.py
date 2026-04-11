"""Data source tracking model."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    license_type: Mapped[str | None] = mapped_column(String(100))
    last_checked_at: Mapped[str | None] = mapped_column(String(50))
    last_updated_at: Mapped[str | None] = mapped_column(String(50))
    coverage_area: Mapped[str | None] = mapped_column(Text)
