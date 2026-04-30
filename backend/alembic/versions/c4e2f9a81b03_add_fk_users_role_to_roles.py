"""add_fk_users_role_to_roles

Revision ID: c4e2f9a81b03
Revises: b3f1a7c24d01
Create Date: 2026-04-30 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c4e2f9a81b03'
down_revision: Union[str, Sequence[str]] = 'b3f1a7c24d01'
branch_labels: Union[str, Sequence[str], None] = None
# depends on both ea9c75d38e59 (users table) and b3f1a7c24d01 (roles table)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key("fk_users_role_roles", "users", "roles", ["role"], ["name"])


def downgrade() -> None:
    op.drop_constraint("fk_users_role_roles", "users", type_="foreignkey")
