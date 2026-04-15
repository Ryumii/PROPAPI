"""Add Stripe subscription fields.

Revision ID: 003
Revises: 002
Create Date: 2026-04-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_account", sa.Column("stripe_subscription_id", sa.String(255)))


def downgrade() -> None:
    op.drop_column("user_account", "stripe_subscription_id")
