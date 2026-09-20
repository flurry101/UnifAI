"""Add user profile and OAuth columns.

Revision ID: 9b7d3f4c2a1e
Revises: 66d4427ed1ae
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9b7d3f4c2a1e"
down_revision: Union[str, Sequence[str], None] = "66d4427ed1ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("auth_provider", sa.String(), nullable=True, server_default="local"))
    op.add_column("users", sa.Column("avatar_url", sa.String(), nullable=True))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "external_identity",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_id", name="uq_external_identity_provider_id"),
    )
    op.create_index("ix_external_identity_user_id", "external_identity", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_external_identity_user_id", table_name="external_identity")
    op.drop_table("external_identity")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "email")
