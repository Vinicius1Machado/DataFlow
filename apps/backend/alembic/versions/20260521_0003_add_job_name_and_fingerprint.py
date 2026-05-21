"""add job name and file fingerprint

Revision ID: 20260521_0003
Revises: 20260521_0002
Create Date: 2026-05-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_0003"
down_revision: str | None = "20260521_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("data_jobs", sa.Column("job_name", sa.String(length=255), nullable=True))
    op.add_column("data_jobs", sa.Column("file_fingerprint", sa.String(length=64), nullable=True))

    op.execute("UPDATE data_jobs SET job_name = file_name WHERE job_name IS NULL")
    op.execute(
        """
        UPDATE data_jobs
        SET file_fingerprint =
            md5(user_id || ':' || file_name || ':' || file_size::text || ':' || id::text) ||
            md5(user_id || ':' || file_name || ':' || file_size::text || ':' || id::text || '-legacy')
        WHERE file_fingerprint IS NULL
        """
    )

    op.alter_column("data_jobs", "job_name", nullable=False)
    op.alter_column("data_jobs", "file_fingerprint", nullable=False)
    op.create_index("ix_data_jobs_file_fingerprint", "data_jobs", ["file_fingerprint"], unique=False)
    op.create_index(
        "ux_data_jobs_user_fingerprint",
        "data_jobs",
        ["user_id", "file_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_data_jobs_user_fingerprint", table_name="data_jobs")
    op.drop_index("ix_data_jobs_file_fingerprint", table_name="data_jobs")
    op.drop_column("data_jobs", "file_fingerprint")
    op.drop_column("data_jobs", "job_name")
