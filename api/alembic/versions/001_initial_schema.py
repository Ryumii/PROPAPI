"""Initial schema — all MVP tables.

Revision ID: 001
Revises: None
Create Date: 2026-04-12
"""
from collections.abc import Sequence

import geoalchemy2  # noqa: F401
import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable PostGIS
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # --- data_source ---
    op.create_table(
        "data_source",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("url", sa.Text),
        sa.Column("license_type", sa.String(100)),
        sa.Column("last_checked_at", sa.String(50)),
        sa.Column("last_updated_at", sa.String(50)),
        sa.Column("coverage_area", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- hazard_flood ---
    op.create_table(
        "hazard_flood",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("depth_rank", sa.SmallInteger, nullable=False),
        sa.Column("depth_range", sa.Text, nullable=False),
        sa.Column("return_period", sa.SmallInteger),
        sa.Column("river_name", sa.Text),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_source.id")),
        sa.Column("prefecture", sa.String(10), nullable=False),
        sa.Column("city", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_hazard_flood_geom", "hazard_flood", ["geom"], postgresql_using="gist")
    op.create_index("idx_hazard_flood_prefecture", "hazard_flood", ["prefecture"])

    # --- hazard_landslide ---
    op.create_table(
        "hazard_landslide",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("zone_type", sa.String(20), nullable=False),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_source.id")),
        sa.Column("prefecture", sa.String(10), nullable=False),
        sa.Column("city", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_hazard_landslide_geom", "hazard_landslide", ["geom"], postgresql_using="gist")
    op.create_index("idx_hazard_landslide_prefecture", "hazard_landslide", ["prefecture"])

    # --- hazard_tsunami ---
    op.create_table(
        "hazard_tsunami",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("depth_m", sa.Numeric(6, 2)),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_source.id")),
        sa.Column("prefecture", sa.String(10), nullable=False),
        sa.Column("city", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_hazard_tsunami_geom", "hazard_tsunami", ["geom"], postgresql_using="gist")
    op.create_index("idx_hazard_tsunami_prefecture", "hazard_tsunami", ["prefecture"])

    # --- hazard_liquefaction ---
    op.create_table(
        "hazard_liquefaction",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("pl_value", sa.Numeric(6, 2)),
        sa.Column("risk_rank", sa.SmallInteger),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_source.id")),
        sa.Column("prefecture", sa.String(10), nullable=False),
        sa.Column("city", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_hazard_liquefaction_geom", "hazard_liquefaction", ["geom"], postgresql_using="gist")
    op.create_index("idx_hazard_liquefaction_prefecture", "hazard_liquefaction", ["prefecture"])

    # --- zoning_district ---
    op.create_table(
        "zoning_district",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("use_district", sa.Text, nullable=False),
        sa.Column("use_code", sa.CHAR(2), nullable=False),
        sa.Column("coverage_pct", sa.SmallInteger),
        sa.Column("floor_ratio_pct", sa.SmallInteger),
        sa.Column("fire_prevention", sa.Text),
        sa.Column("fire_code", sa.CHAR(2)),
        sa.Column("height_district", sa.Text),
        sa.Column("scenic_district", sa.Text),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_source.id")),
        sa.Column("prefecture", sa.String(10), nullable=False),
        sa.Column("city", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_zoning_geom", "zoning_district", ["geom"], postgresql_using="gist")
    op.create_index("idx_zoning_prefecture", "zoning_district", ["prefecture"])

    # --- address_master ---
    op.create_table(
        "address_master",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("prefecture", sa.String(10), nullable=False),
        sa.Column("city", sa.String(50), nullable=False),
        sa.Column("town", sa.String(100), nullable=False),
        sa.Column("block_number", sa.String(50)),
        sa.Column("building_number", sa.String(50)),
        sa.Column("normalized_addr", sa.Text, nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_address_geom", "address_master", ["geom"], postgresql_using="gist")
    op.create_index("idx_address_normalized", "address_master", ["normalized_addr"])
    op.create_index("idx_address_prefecture_city", "address_master", ["prefecture", "city"])

    # --- user_account ---
    op.create_table(
        "user_account",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default="starter"),
        sa.Column("company_name", sa.String(255)),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- api_key ---
    op.create_table(
        "api_key",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("key_hash", sa.Text, unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default="starter"),
        sa.Column("monthly_limit", sa.Integer, nullable=False, server_default="1000"),
        sa.Column("rate_per_sec", sa.Integer, nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_api_key_hash", "api_key", ["key_hash"])

    # --- usage_log ---
    op.create_table(
        "usage_log",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("api_key_id", sa.Integer, sa.ForeignKey("api_key.id"), nullable=False),
        sa.Column("endpoint", sa.String(100), nullable=False),
        sa.Column("request_address", sa.Text),
        sa.Column("response_status", sa.SmallInteger, nullable=False),
        sa.Column("processing_time_ms", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_usage_log_api_key", "usage_log", ["api_key_id"])
    op.create_index("idx_usage_log_created", "usage_log", ["created_at"])

    # --- data_change_log ---
    op.create_table(
        "data_change_log",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", sa.BigInteger, nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("old_value", sa.Text),
        sa.Column("new_value", sa.Text),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("data_source.id")),
    )
    op.create_index("idx_data_change_table", "data_change_log", ["table_name", "record_id"])


def downgrade() -> None:
    op.drop_table("data_change_log")
    op.drop_table("usage_log")
    op.drop_table("api_key")
    op.drop_table("user_account")
    op.drop_table("address_master")
    op.drop_table("zoning_district")
    op.drop_table("hazard_liquefaction")
    op.drop_table("hazard_tsunami")
    op.drop_table("hazard_landslide")
    op.drop_table("hazard_flood")
    op.drop_table("data_source")
    op.execute("DROP EXTENSION IF EXISTS postgis")
