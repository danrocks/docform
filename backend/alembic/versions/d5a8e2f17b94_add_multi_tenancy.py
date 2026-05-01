"""add_multi_tenancy

Revision ID: d5a8e2f17b94
Revises: c4e2f9a81b03
Create Date: 2026-05-01 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a8e2f17b94'
down_revision: Union[str, Sequence[str]] = 'c4e2f9a81b03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), unique=True, nullable=False),
        sa.Column("active", sa.String(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.String(), nullable=False),
    )

    # 2. Add tenant_id column to users (nullable for superadmin)
    op.add_column("users", sa.Column("tenant_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_users_tenant_id_tenants", "users", "tenants",
        ["tenant_id"], ["id"],
    )

    # 3. Replace global username unique constraint with per-tenant composite
    op.drop_constraint("users_username_key", "users", type_="unique")
    op.create_unique_constraint(
        "uq_user_tenant_username", "users", ["username", "tenant_id"],
    )


def downgrade() -> None:
    # Reverse: restore global username uniqueness, drop tenant_id, drop tenants
    op.drop_constraint("uq_user_tenant_username", "users", type_="unique")
    op.create_unique_constraint("users_username_key", "users", ["username"])
    op.drop_constraint("fk_users_tenant_id_tenants", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")
    op.drop_table("tenants")
