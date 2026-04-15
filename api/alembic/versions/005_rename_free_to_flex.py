"""Rename plan free → flex, update limits for new pricing.

Flex: monthly_limit=0 (pure usage-based), Pro: 10K, Max: 100K.

Revision ID: 005
Revises: 004
"""

from alembic import op

revision = "005"
down_revision = "004"


def upgrade() -> None:
    # Rename free → flex
    op.execute("UPDATE user_account SET plan = 'flex' WHERE plan = 'free'")
    op.execute("UPDATE api_key SET plan = 'flex' WHERE plan = 'free'")

    # Update defaults
    op.execute("ALTER TABLE user_account ALTER COLUMN plan SET DEFAULT 'flex'")
    op.execute("ALTER TABLE api_key ALTER COLUMN plan SET DEFAULT 'flex'")
    op.execute("ALTER TABLE api_key ALTER COLUMN monthly_limit SET DEFAULT 0")

    # Update existing plan limits to match new pricing
    # Pro: 50K → 10K
    op.execute(
        "UPDATE api_key SET monthly_limit = 10000 "
        "WHERE plan = 'pro' AND monthly_limit = 50000"
    )
    # Max: 500K → 100K
    op.execute(
        "UPDATE api_key SET monthly_limit = 100000 "
        "WHERE plan = 'max' AND monthly_limit = 500000"
    )
    # Flex: no monthly limit
    op.execute(
        "UPDATE api_key SET monthly_limit = 0 WHERE plan = 'flex'"
    )


def downgrade() -> None:
    op.execute("UPDATE user_account SET plan = 'free' WHERE plan = 'flex'")
    op.execute("UPDATE api_key SET plan = 'free' WHERE plan = 'flex'")
    op.execute("ALTER TABLE user_account ALTER COLUMN plan SET DEFAULT 'free'")
    op.execute("ALTER TABLE api_key ALTER COLUMN plan SET DEFAULT 'free'")
    op.execute("ALTER TABLE api_key ALTER COLUMN monthly_limit SET DEFAULT 100")
    op.execute(
        "UPDATE api_key SET monthly_limit = 50000 WHERE plan = 'pro'"
    )
    op.execute(
        "UPDATE api_key SET monthly_limit = 500000 WHERE plan = 'max'"
    )
