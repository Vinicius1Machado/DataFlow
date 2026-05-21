"""create data jobs table

Revision ID: 20260520_0001
Revises:
Create Date: 2026-05-20 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260520_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("raw_file_url", sa.Text(), nullable=False),
        sa.Column("result_package_url", sa.Text(), nullable=True),
        sa.Column("analysis_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_script", sa.Text(), nullable=True),
        sa.Column("generated_manual", sa.Text(), nullable=True),
        sa.Column("requirements_txt", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_jobs_status", "data_jobs", ["status"], unique=False)
    op.create_index("ix_data_jobs_user_id", "data_jobs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_data_jobs_user_id", table_name="data_jobs")
    op.drop_index("ix_data_jobs_status", table_name="data_jobs")
    op.drop_table("data_jobs")
