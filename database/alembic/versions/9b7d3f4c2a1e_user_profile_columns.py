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


def _column_names(bind, table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _set_hashed_password_nullable(bind, nullable: bool) -> None:
    columns = {column["name"]: column for column in sa.inspect(bind).get_columns("users")}
    password_column = columns.get("hashed_password")
    if password_column is None or password_column["nullable"] == nullable:
        return
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("users", recreate="always") as batch_op:
            batch_op.alter_column(
                "hashed_password",
                existing_type=password_column["type"],
                nullable=nullable,
            )
    else:
        op.alter_column(
            "users",
            "hashed_password",
            existing_type=password_column["type"],
            nullable=nullable,
        )


def _deduplicate_emails(bind) -> None:
    duplicate_emails = bind.execute(
        sa.text(
            "SELECT email FROM users WHERE email IS NOT NULL "
            "GROUP BY email HAVING COUNT(*) > 1"
        )
    ).scalars().all()
    for email in duplicate_emails:
        user_ids = bind.execute(
            sa.text("SELECT id FROM users WHERE email = :email ORDER BY id"),
            {"email": email},
        ).scalars().all()
        if len(user_ids) > 1:
            bind.execute(
                sa.text("UPDATE users SET email = NULL WHERE id IN :user_ids").bindparams(
                    sa.bindparam("user_ids", expanding=True)
                ),
                {"user_ids": user_ids[1:]},
            )


def upgrade() -> None:
    bind = op.get_bind()
    columns = _column_names(bind, "users")
    if "email" not in columns:
        op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    if "auth_provider" not in columns:
        op.add_column("users", sa.Column("auth_provider", sa.String(), nullable=True, server_default="local"))
    if "avatar_url" not in columns:
        op.add_column("users", sa.Column("avatar_url", sa.String(), nullable=True))

    _set_hashed_password_nullable(bind, True)
    _deduplicate_emails(bind)
    if "ix_users_email" not in _index_names(bind, "users"):
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "external_identity" not in sa.inspect(bind).get_table_names():
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
    if "ix_external_identity_user_id" not in _index_names(bind, "external_identity"):
        op.create_index("ix_external_identity_user_id", "external_identity", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if "external_identity" in sa.inspect(bind).get_table_names():
        if "ix_external_identity_user_id" in _index_names(bind, "external_identity"):
            op.drop_index("ix_external_identity_user_id", table_name="external_identity")
        op.drop_table("external_identity")

    if "ix_users_email" in _index_names(bind, "users"):
        op.drop_index("ix_users_email", table_name="users")

    if "hashed_password" in _column_names(bind, "users"):
        bind.execute(
            sa.text(
                "UPDATE users SET hashed_password = :disabled_password "
                "WHERE hashed_password IS NULL"
            ),
            {"disabled_password": "!oauth-only-account-no-password!"},
        )
        _set_hashed_password_nullable(bind, False)

    columns = _column_names(bind, "users")
    managed_columns = [name for name in ("avatar_url", "auth_provider", "email") if name in columns]
    if bind.dialect.name == "sqlite" and managed_columns:
        with op.batch_alter_table("users", recreate="always") as batch_op:
            for column_name in managed_columns:
                batch_op.drop_column(column_name)
    else:
        for column_name in managed_columns:
            op.drop_column("users", column_name)
