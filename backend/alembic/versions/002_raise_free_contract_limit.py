"""raise free user contract limit to 50

Revision ID: 002
Revises: 001
Create Date: 2026-08-09
"""
from alembic import op

revision = "002"
down_revision = "001"


def upgrade():
    op.execute("UPDATE users SET contracts_limit = 50 WHERE contracts_limit = 3")
    op.execute("ALTER TABLE users ALTER COLUMN contracts_limit SET DEFAULT 50")


def downgrade():
    op.execute("UPDATE users SET contracts_limit = 3 WHERE contracts_limit = 50")
    op.execute("ALTER TABLE users ALTER COLUMN contracts_limit SET DEFAULT 3")
