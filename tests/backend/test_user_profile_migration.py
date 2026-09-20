import importlib

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_email_deduplication_records_history_before_nulling(monkeypatch):
    migration = importlib.import_module(
        "database.alembic.versions.9b7d3f4c2a1e_user_profile_columns"
    )
    engine = sa.create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE users ("
            "id VARCHAR PRIMARY KEY, "
            "email VARCHAR, "
            "hashed_password VARCHAR NOT NULL"
            ")"
        )
        connection.execute(
            sa.text(
                "INSERT INTO users (id, email, hashed_password) VALUES "
                "(:first_id, :email, :password), "
                "(:second_id, :email, :password), "
                "(:third_id, :email, :password)"
            ),
            {
                "first_id": "001",
                "second_id": "002",
                "third_id": "003",
                "email": "duplicate@example.com",
                "password": "hashed",
            },
        )
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration, "op", operations)

        migration.upgrade()

        users = connection.execute(
            sa.text("SELECT id, email FROM users ORDER BY id")
        ).all()
        history = connection.execute(
            sa.text(
                "SELECT user_id, original_email, retained_user_id, migration_revision "
                "FROM user_email_deduplication_history ORDER BY user_id"
            )
        ).all()

        migration.downgrade()
        tables_after_downgrade = sa.inspect(connection).get_table_names()
        history_after_downgrade = connection.execute(
            sa.text(
                "SELECT user_id, original_email, retained_user_id, migration_revision "
                "FROM user_email_deduplication_history ORDER BY user_id"
            )
        ).all()

    assert users == [
        ("001", "duplicate@example.com"),
        ("002", None),
        ("003", None),
    ]
    assert history == [
        ("002", "duplicate@example.com", "001", migration.revision),
        ("003", "duplicate@example.com", "001", migration.revision),
    ]
    assert "user_email_deduplication_history" in tables_after_downgrade
    assert history_after_downgrade == history
