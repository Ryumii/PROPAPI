"""Fix user_account and api_key sequences after manual inserts.

Revision ID: 006
Revises: 005
"""
from alembic import op

revision = "006_fix_sequences"
down_revision = "005_rename_free_to_flex"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SELECT setval('user_account_id_seq', (SELECT COALESCE(MAX(id), 0) FROM user_account))")
    op.execute("SELECT setval('api_key_id_seq', (SELECT COALESCE(MAX(id), 0) FROM api_key))")


def downgrade() -> None:
    pass  # sequences are fine as-is
