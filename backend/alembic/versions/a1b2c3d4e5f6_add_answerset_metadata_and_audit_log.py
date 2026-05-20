"""add_answerset_metadata_and_audit_log

Revision ID: a1b2c3d4e5f6
Revises: f2e4a6c7d109
Create Date: 2026-05-19 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str]] = "f2e4a6c7d109"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "answerset_metadata",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), nullable=False, index=True),
        sa.Column("template_name", sa.String(), nullable=False, server_default=""),
        sa.Column("interview_version", sa.String(), nullable=True),
        sa.Column("context", sa.Text(), nullable=False, server_default=""),
        sa.Column("workgroup_id", sa.String(), nullable=True, index=True),
        sa.Column("submitted_by", sa.String(), nullable=False, index=True),
        sa.Column("submitted_by_name", sa.String(), nullable=False, server_default=""),
        sa.Column("submitted_at", sa.String(), nullable=False),
        sa.Column("docx_path", sa.String(), nullable=True),
        sa.Column("pdf_path", sa.String(), nullable=True),
        sa.Column("shared_with", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("tenant_id", sa.String(), nullable=True, index=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.ForeignKeyConstraint(
            ["workgroup_id"],
            ["workgroups.id"],
            name="fk_answerset_metadata_workgroup_id_workgroups",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["users.id"],
            name="fk_answerset_metadata_submitted_by_users",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_answerset_metadata_tenant_id_tenants",
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("answerset_id", sa.String(), nullable=False, index=True),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("user_name", sa.String(), nullable=False, server_default=""),
        sa.Column("tenant_id", sa.String(), nullable=True, index=True),
        sa.Column("ip_address", sa.String(), nullable=False, server_default=""),
        sa.Column("timestamp", sa.String(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("answerset_metadata")
