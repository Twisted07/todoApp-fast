import os
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("JWT_SECRET", "unit-test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

TEST_PASSWORD = "P@ssw0rd1"
TEST_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def sample_user():
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    user.role = "owner"
    user.is_active = True
    user.hash_password = TEST_HASH
    return user


@pytest.fixture
def admin_user(sample_user):
    sample_user.role = "admin"
    return sample_user


@pytest.fixture
def user_token_payload():
    return {"username": "testuser", "id": 1, "role": "owner"}


@pytest.fixture
def sample_todo():
    todo = MagicMock()
    todo.id = 1
    todo.title = "Test todo"
    todo.description = "A test item"
    todo.priority = 3
    todo.complete = False
    todo.owner = 1
    return todo
