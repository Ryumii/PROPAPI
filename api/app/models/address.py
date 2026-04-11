"""Address master model."""

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AddressMaster(Base, TimestampMixin):
    __tablename__ = "address_master"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    prefecture: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    town: Mapped[str] = mapped_column(String(100), nullable=False)
    block_number: Mapped[str | None] = mapped_column(String(50))
    building_number: Mapped[str | None] = mapped_column(String(50))
    normalized_addr: Mapped[str] = mapped_column(Text, nullable=False)
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        Index("idx_address_geom", "geom", postgresql_using="gist"),
        Index("idx_address_normalized", "normalized_addr"),
        Index("idx_address_prefecture_city", "prefecture", "city"),
    )
