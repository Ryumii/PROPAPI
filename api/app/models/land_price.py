"""Land price (公示地価) data model — L01 national land price survey points."""

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Float, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.data_source import DataSource  # noqa: F401


class LandPrice(Base, TimestampMixin):
    __tablename__ = "land_price"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    # 公示地価の主要属性
    price_per_sqm: Mapped[int] = mapped_column(Integer, nullable=False, comment="円/m² 公示価格")
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="調査年")
    yoy_change_pct: Mapped[float | None] = mapped_column(Float, comment="前年変動率 %")
    land_use: Mapped[str | None] = mapped_column(String(100), comment="利用現況 e.g. 住宅,店舗")
    address: Mapped[str | None] = mapped_column(Text, comment="所在地")
    address_short: Mapped[str | None] = mapped_column(String(200), comment="住居表示")
    area_sqm: Mapped[int | None] = mapped_column(Integer, comment="地積 m²")
    structure: Mapped[str | None] = mapped_column(String(20), comment="建物構造 e.g. RC,SRC")
    nearest_station: Mapped[str | None] = mapped_column(String(100), comment="最寄駅")
    station_distance_m: Mapped[int | None] = mapped_column(Integer, comment="駅距離 m")
    zoning_name: Mapped[str | None] = mapped_column(String(50), comment="用途地域名")
    building_coverage_pct: Mapped[int | None] = mapped_column(SmallInteger, comment="建ぺい率 %")
    floor_area_ratio_pct: Mapped[int | None] = mapped_column(SmallInteger, comment="容積率 %")
    neighborhood_desc: Mapped[str | None] = mapped_column(Text, comment="周辺の土地利用状況")

    source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("data_source.id"))
    prefecture: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))

    source = relationship("DataSource", lazy="selectin")

    __table_args__ = (
        Index("idx_land_price_geom", "geom", postgresql_using="gist"),
        Index("idx_land_price_prefecture", "prefecture"),
        Index("idx_land_price_year", "year"),
    )
