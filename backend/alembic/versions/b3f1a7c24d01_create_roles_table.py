"""create_roles_table

Revision ID: b3f1a7c24d01
Revises: ea9c75d38e59
Create Date: 2026-04-27 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f1a7c24d01'
down_revision: Union[str, Sequence[str], None] = 'ea9c75d38e59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "roles",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("roles")
