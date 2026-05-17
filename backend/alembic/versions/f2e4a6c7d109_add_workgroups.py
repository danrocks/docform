"""add_workgroups

Revision ID: f2e4a6c7d109
Revises: d5a8e2f17b94
Create Date: 2026-05-13 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2e4a6c7d109"
down_revision: Union[str, Sequence[str]] = "d5a8e2f17b94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workgroups",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_workgroups_tenant_id_tenants"
        ),
    )

    op.create_table(
        "template_settings",
        sa.Column("template_id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "restricted_to_workgroups",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_template_settings_tenant_id_tenants"
        ),
    )

    op.create_table(
        "workgroup_templates",
        sa.Column("workgroup_id", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("workgroup_id", "template_id"),
        sa.ForeignKeyConstraint(
            ["workgroup_id"],
            ["workgroups.id"],
            name="fk_workgroup_templates_workgroup_id_workgroups",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["template_settings.template_id"],
            name="fk_workgroup_templates_template_id_template_settings",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "workgroup_users",
        sa.Column("workgroup_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("workgroup_id", "user_id"),
        sa.ForeignKeyConstraint(
            ["workgroup_id"],
            ["workgroups.id"],
            name="fk_workgroup_users_workgroup_id_workgroups",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_workgroup_users_user_id_users",
        ),
    )


def downgrade() -> None:
    op.drop_table("workgroup_users")
    op.drop_table("workgroup_templates")
    op.drop_table("template_settings")
    op.drop_table("workgroups")
