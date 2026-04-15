"""Rename plan tiers: starter → free, professional → pro, growth → pro, business → max.

Update column defaults to match Free plan (100 req/mo, 1 req/s).

Revision ID: 004
Revises: 003
"""

from alembic import op

revision = "004"
down_revision = "003"


def upgrade() -> None:
    # Rename plan values in user_account
    op.execute("UPDATE user_account SET plan = 'free' WHERE plan = 'starter'")
    op.execute("UPDATE user_account SET plan = 'pro' WHERE plan IN ('professional', 'growth')")
    op.execute("UPDATE user_account SET plan = 'max' WHERE plan = 'business'")

    # Rename plan values in api_key
    op.execute("UPDATE api_key SET plan = 'free' WHERE plan = 'starter'")
    op.execute("UPDATE api_key SET plan = 'pro' WHERE plan IN ('professional', 'growth')")
    op.execute("UPDATE api_key SET plan = 'max' WHERE plan = 'business'")

    # Update column defaults
    op.execute("ALTER TABLE user_account ALTER COLUMN plan SET DEFAULT 'free'")
    op.execute("ALTER TABLE api_key ALTER COLUMN plan SET DEFAULT 'free'")
    op.execute("ALTER TABLE api_key ALTER COLUMN monthly_limit SET DEFAULT 100")
    op.execute("ALTER TABLE api_key ALTER COLUMN rate_per_sec SET DEFAULT 1")


def downgrade() -> None:
    op.execute("UPDATE user_account SET plan = 'starter' WHERE plan = 'free'")
    op.execute("UPDATE user_account SET plan = 'professional' WHERE plan = 'pro'")
    op.execute("UPDATE user_account SET plan = 'business' WHERE plan = 'max'")

    op.execute("UPDATE api_key SET plan = 'starter' WHERE plan = 'free'")
    op.execute("UPDATE api_key SET plan = 'professional' WHERE plan = 'pro'")
    op.execute("UPDATE api_key SET plan = 'business' WHERE plan = 'max'")

    op.execute("ALTER TABLE user_account ALTER COLUMN plan SET DEFAULT 'starter'")
    op.execute("ALTER TABLE api_key ALTER COLUMN plan SET DEFAULT 'starter'")
    op.execute("ALTER TABLE api_key ALTER COLUMN monthly_limit SET DEFAULT 1000")
    op.execute("ALTER TABLE api_key ALTER COLUMN rate_per_sec SET DEFAULT 10")
