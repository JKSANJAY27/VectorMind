"""Main test configuration and fixtures."""

import os
import pytest
from testcontainers.postgres import PostgresContainer
from src.db.interfaces.postgresql import PostgreSQLDatabase, PostgreSQLSettings


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for tests."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        # Set environment variable so settings can pick it up if needed
        os.environ["POSTGRES_DATABASE_URL"] = postgres.get_connection_url()
        yield postgres


@pytest.fixture(scope="session")
def database(postgres_container):
    """Create a database instance connected to the test container."""
    config = PostgreSQLSettings(
        database_url=postgres_container.get_connection_url(),
        echo_sql=False,
    )
    db = PostgreSQLDatabase(config=config)
    db.startup()
    yield db
    db.teardown()


@pytest.fixture(scope="function")
def db_session(database):
    """Provide a transactional scope around a series of operations."""
    with database.get_session() as session:
        yield session
