"""
Pytest configuration and shared fixtures for the test suite.
"""

import sys
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Add the backend directory to Python path so 'app' module can be imported
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine that persists for the entire test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


# Configure pytest-asyncio if async tests are added in the future
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
