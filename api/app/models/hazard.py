"""Hazard data models — flood, landslide, tsunami, liquefaction."""

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.data_source import DataSource  # noqa: F401 – for relationship


class HazardFlood(Base, TimestampMixin):
    __tablename__ = "hazard_flood"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False
    )
    depth_rank: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="0-5 scale")
    depth_range: Mapped[str] = mapped_column(Text, nullable=False)
    return_period: Mapped[int | None] = mapped_column(SmallInteger)
    river_name: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("data_source.id"))
    prefecture: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))

    source = relationship("DataSource", lazy="selectin")

    __table_args__ = (
        Index("idx_hazard_flood_geom", "geom", postgresql_using="gist"),
        Index("idx_hazard_flood_prefecture", "prefecture"),
    )


class HazardLandslide(Base, TimestampMixin):
    __tablename__ = "hazard_landslide"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False
    )
    zone_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="警戒区域 / 特別警戒区域"
    )
    source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("data_source.id"))
    prefecture: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))

    source = relationship("DataSource", lazy="selectin")

    __table_args__ = (
        Index("idx_hazard_landslide_geom", "geom", postgresql_using="gist"),
        Index("idx_hazard_landslide_prefecture", "prefecture"),
    )


class HazardTsunami(Base, TimestampMixin):
    __tablename__ = "hazard_tsunami"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False
    )
    depth_m: Mapped[float | None] = mapped_column(Numeric(6, 2))
    source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("data_source.id"))
    prefecture: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))

    source = relationship("DataSource", lazy="selectin")

    __table_args__ = (
        Index("idx_hazard_tsunami_geom", "geom", postgresql_using="gist"),
        Index("idx_hazard_tsunami_prefecture", "prefecture"),
    )


class HazardLiquefaction(Base, TimestampMixin):
    __tablename__ = "hazard_liquefaction"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False
    )
    pl_value: Mapped[float | None] = mapped_column(Numeric(6, 2))
    risk_rank: Mapped[int | None] = mapped_column(SmallInteger, comment="0-5 scale")
    source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("data_source.id"))
    prefecture: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))

    source = relationship("DataSource", lazy="selectin")

    __table_args__ = (
        Index("idx_hazard_liquefaction_geom", "geom", postgresql_using="gist"),
        Index("idx_hazard_liquefaction_prefecture", "prefecture"),
    )
