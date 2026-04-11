"""Zoning district model."""

from geoalchemy2 import Geometry
from sqlalchemy import CHAR, BigInteger, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ZoningDistrict(Base, TimestampMixin):
    __tablename__ = "zoning_district"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False
    )
    use_district: Mapped[str] = mapped_column(Text, nullable=False)
    use_code: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    coverage_pct: Mapped[int | None] = mapped_column(SmallInteger, comment="建ぺい率 %")
    floor_ratio_pct: Mapped[int | None] = mapped_column(SmallInteger, comment="容積率 %")
    fire_prevention: Mapped[str | None] = mapped_column(Text)
    fire_code: Mapped[str | None] = mapped_column(CHAR(2))
    height_district: Mapped[str | None] = mapped_column(Text)
    scenic_district: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("data_source.id"))
    prefecture: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))

    source = relationship("DataSource", lazy="selectin")

    __table_args__ = (
        Index("idx_zoning_geom", "geom", postgresql_using="gist"),
        Index("idx_zoning_prefecture", "prefecture"),
    )
