from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from controllers import auth as auth_controller
from models.dto.model_pydantic import UserBaseModel, UserSigninBaseModel
from tests.unit.conftest import TEST_HASH, TEST_PASSWORD


@pytest.mark.asyncio
async def test_login_success(mock_db, sample_user):
    mock_db.query.return_value.filter.return_value.first.return_value = sample_user
    credentials = UserSigninBaseModel(username="testuser", password=TEST_PASSWORD)

    with patch.object(auth_controller.pwd_context, "verify", return_value=True):
        response = await auth_controller.login(mock_db, credentials)

    assert response["message"] == "login successful"
    assert response["data"].username == "testuser"
    assert response["data"].id == 1


@pytest.mark.asyncio
async def test_login_incorrect_credentials(mock_db, sample_user):
    mock_db.query.return_value.filter.return_value.first.return_value = sample_user
    credentials = UserSigninBaseModel(username="testuser", password="WrongPass1!")

    with patch.object(auth_controller.pwd_context, "verify", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await auth_controller.login(mock_db, credentials)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Incorrect credentials"


@pytest.mark.asyncio
async def test_create_user(mock_db):
    user = UserBaseModel(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        password=TEST_PASSWORD,
        username="janedoe",
        role="owner",
    )

    with patch.object(auth_controller.pwd_context, "hash", return_value="hashed-password"):
        response = await auth_controller.create_user(mock_db, user)

    assert response == {"message": "User created successfully."}
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_login_for_token_success(mock_db, sample_user):
    form_data = OAuth2PasswordRequestForm(
        username="testuser",
        password=TEST_PASSWORD,
        scope="",
        client_id=None,
        client_secret=None,
    )

    with patch.object(
        auth_controller, "__authenticateUser", return_value=sample_user
    ), patch.object(
        auth_controller, "__create_access_token", return_value="signed-token"
    ):
        response = await auth_controller.login_for_token(form_data, mock_db)

    assert response["message"] == "user authenticated successfully"
    assert response["access_token"] == "signed-token"
    assert response["type"] == "bearer"


@pytest.mark.asyncio
async def test_login_for_token_authentication_failure(mock_db):
    form_data = OAuth2PasswordRequestForm(
        username="testuser",
        password="WrongPass1!",
        scope="",
        client_id=None,
        client_secret=None,
    )

    with patch.object(auth_controller, "__authenticateUser", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await auth_controller.login_for_token(form_data, mock_db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "User could not be authenticated"


@pytest.mark.asyncio
async def test_get_all_users_returns_matching_users(mock_db, sample_user, user_token_payload):
    mock_db.query.return_value.filter.return_value.all.return_value = [sample_user]

    response = await auth_controller.get_all_users(user_token_payload, mock_db)

    assert response == {"users": [sample_user]}


@pytest.mark.asyncio
async def test_get_all_users_returns_empty_list(mock_db, user_token_payload):
    mock_db.query.return_value.filter.return_value.all.return_value = []

    response = await auth_controller.get_all_users(user_token_payload, mock_db)

    assert response == {"users": []}


@pytest.mark.asyncio
async def test_get_all_users_unauthorized(mock_db):
    with pytest.raises(HTTPException) as exc_info:
        await auth_controller.get_all_users(None, mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_all_admin_users_success(mock_db, admin_user):
    admin_payload = {"username": "admin", "id": 1, "role": "admin"}
    mock_db.query.return_value.all.return_value = [admin_user]

    response = await auth_controller.get_all_admin_users(admin_payload, mock_db)

    assert response == {"users": [admin_user]}


@pytest.mark.asyncio
async def test_get_all_admin_users_empty(mock_db):
    admin_payload = {"username": "admin", "id": 1, "role": "admin"}
    mock_db.query.return_value.all.return_value = []

    response = await auth_controller.get_all_admin_users(admin_payload, mock_db)

    assert response == {"users": []}


@pytest.mark.asyncio
async def test_get_all_admin_users_unauthorized_role(mock_db, user_token_payload):
    with pytest.raises(HTTPException) as exc_info:
        await auth_controller.get_all_admin_users(user_token_payload, mock_db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "You are unauthorized to access this resource"
