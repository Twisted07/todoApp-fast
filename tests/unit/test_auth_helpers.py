from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt

from controllers.helpers import auth as auth_helpers
from tests.unit.conftest import TEST_HASH, TEST_PASSWORD


def test_get_db_yields_and_closes_session(monkeypatch):
    mock_session = MagicMock()
    mock_session_local = MagicMock(return_value=mock_session)
    monkeypatch.setattr(auth_helpers, "SessionLocal", mock_session_local)

    db_gen = auth_helpers.get_db()
    db = next(db_gen)

    assert db is mock_session
    db_gen.close()
    mock_session.close.assert_called_once()


def test_authenticate_user_success(mock_db, sample_user):
    mock_db.query.return_value.filter.return_value.first.return_value = sample_user

    with patch.object(auth_helpers.pwd_context, "verify", return_value=True):
        result = auth_helpers.__authenticateUser("testuser", TEST_PASSWORD, mock_db)

    assert result is sample_user


def test_authenticate_user_not_found(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        auth_helpers.__authenticateUser("missing", TEST_PASSWORD, mock_db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User does not exist"


def test_authenticate_user_wrong_password(mock_db, sample_user):
    mock_db.query.return_value.filter.return_value.first.return_value = sample_user

    with patch.object(auth_helpers.pwd_context, "verify", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            auth_helpers.__authenticateUser("testuser", "WrongPass1!", mock_db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Incorrect credentials"


def test_create_access_token_encodes_payload():
    token = auth_helpers.__create_access_token(
        "testuser", 1, "owner", timedelta(minutes=30)
    )

    payload = jwt.decode(
        token,
        "unit-test-secret-key",
        algorithms=["HS256"],
    )
    assert payload["sub"] == "testuser"
    assert payload["id"] == 1
    assert payload["role"] == "owner"
    assert "expires_at" in payload


@pytest.mark.asyncio
async def test_get_current_user_from_token_success():
    token = auth_helpers.__create_access_token(
        "testuser", 1, "owner", timedelta(minutes=30)
    )

    user = await auth_helpers.__get_current_user_from_token(token)

    assert user == {"username": "testuser", "id": 1, "role": "owner"}


@pytest.mark.asyncio
async def test_get_current_user_from_token_missing_fields():
    token = jwt.encode(
        {"sub": "testuser"},
        "unit-test-secret-key",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth_helpers.__get_current_user_from_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_from_token_jwt_error():
    with pytest.raises(HTTPException) as exc_info:
        await auth_helpers.__get_current_user_from_token("not-a-valid-token")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_message"] == "Could not validate user"


def test_validate_user_raises_when_none():
    with pytest.raises(HTTPException) as exc_info:
        auth_helpers.__validate_user(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized to access resource"


def test_validate_user_passes_for_valid_user(user_token_payload):
    auth_helpers.__validate_user(user_token_payload)


def test_validate_admin_raises_when_none():
    with pytest.raises(HTTPException) as exc_info:
        auth_helpers.__validate_admin(None)

    assert exc_info.value.status_code == 401


def test_validate_admin_raises_for_non_admin(user_token_payload):
    with pytest.raises(HTTPException) as exc_info:
        auth_helpers.__validate_admin(user_token_payload)

    assert exc_info.value.status_code == 401


def test_validate_admin_passes_for_admin():
    auth_helpers.__validate_admin({"username": "admin", "id": 2, "role": "admin"})
