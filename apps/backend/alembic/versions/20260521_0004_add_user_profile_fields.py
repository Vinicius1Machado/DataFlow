"""add user profile fields

Revision ID: 20260521_0004
Revises: 20260521_0003
Create Date: 2026-05-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_0004"
down_revision: str | None = "20260521_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("app_users", sa.Column("full_name", sa.String(length=160), nullable=True))
    op.add_column("app_users", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("app_users", sa.Column("organization", sa.String(length=160), nullable=True))
    op.add_column("app_users", sa.Column("role", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("app_users", "role")
    op.drop_column("app_users", "organization")
    op.drop_column("app_users", "email")
    op.drop_column("app_users", "full_name")
