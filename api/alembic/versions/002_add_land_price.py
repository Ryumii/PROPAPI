"""Add land_price table for 公示地価 (L01) data.

Revision ID: 002
Revises: 001
Create Date: 2026-07-24
"""
from collections.abc import Sequence

import geoalchemy2  # noqa: F401
import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "land_price",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("price_per_sqm", sa.Integer, nullable=False, comment="円/m² 公示価格"),
        sa.Column("year", sa.SmallInteger, nullable=False, comment="調査年"),
        sa.Column("yoy_change_pct", sa.Float, comment="前年変動率 %"),
        sa.Column("land_use", sa.String(100), comment="利用現況 e.g. 住宅,店舗"),
        sa.Column("address", sa.Text, comment="所在地"),
        sa.Column("address_short", sa.String(200), comment="住居表示"),
        sa.Column("area_sqm", sa.Integer, comment="地積 m²"),
        sa.Column("structure", sa.String(20), comment="建物構造 e.g. RC,SRC"),
        sa.Column("nearest_station", sa.String(100), comment="最寄駅"),
        sa.Column("station_distance_m", sa.Integer, comment="駅距離 m"),
        sa.Column("zoning_name", sa.String(50), comment="用途地域名"),
        sa.Column("building_coverage_pct", sa.SmallInteger, comment="建ぺい率 %"),
        sa.Column("floor_area_ratio_pct", sa.SmallInteger, comment="容積率 %"),
        sa.Column("neighborhood_desc", sa.Text, comment="周辺の土地利用状況"),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_source.id")),
        sa.Column("prefecture", sa.String(10), nullable=False),
        sa.Column("city", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_land_price_geom", "land_price", ["geom"], postgresql_using="gist")
    op.create_index("idx_land_price_prefecture", "land_price", ["prefecture"])
    op.create_index("idx_land_price_year", "land_price", ["year"])


def downgrade() -> None:
    op.drop_index("idx_land_price_year", table_name="land_price")
    op.drop_index("idx_land_price_prefecture", table_name="land_price")
    op.drop_index("idx_land_price_geom", table_name="land_price")
    op.drop_table("land_price")
