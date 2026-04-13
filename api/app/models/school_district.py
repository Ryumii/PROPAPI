"""School district models — elementary and junior high school zones."""

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.data_source import DataSource  # noqa: F401 – for relationship


class SchoolDistrict(Base, TimestampMixin):
    """Public school attendance zone polygon.

    Data source: 国土数値情報 A27 (小学校区) / A32 (中学校区).
    """

    __tablename__ = "school_district"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=False,
    )
    school_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="elementary / junior_high",
    )
    school_name: Mapped[str] = mapped_column(Text, nullable=False)
    school_code: Mapped[str | None] = mapped_column(String(20))
    administrator: Mapped[str | None] = mapped_column(Text, comment="設置者名 e.g. 新宿区立")
    address: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("data_source.id"))
    prefecture: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))

    source = relationship("DataSource", lazy="selectin")

    __table_args__ = (
        Index("idx_school_district_geom", "geom", postgresql_using="gist"),
        Index("idx_school_district_prefecture", "prefecture"),
        Index("idx_school_district_type", "school_type"),
    )
