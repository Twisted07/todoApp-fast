from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from controllers import todo as todo_controller
from models.dto.model_pydantic import TodoModel


@pytest.mark.asyncio
async def test_get_all_todos(mock_db, user_token_payload, sample_todo):
    mock_db.query.return_value.filter.return_value.all.return_value = [sample_todo]

    result = await todo_controller.get_all_todos(user_token_payload, mock_db)

    assert result == [sample_todo]


@pytest.mark.asyncio
async def test_get_all_todos_unauthorized(mock_db):
    with pytest.raises(HTTPException) as exc_info:
        await todo_controller.get_all_todos(None, mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_all_todos_admin(mock_db, sample_todo):
    admin_payload = {"username": "admin", "id": 1, "role": "admin"}
    mock_db.query.return_value.all.return_value = [sample_todo]

    result = await todo_controller.get_all_todos_admin(admin_payload, mock_db)

    assert result == [sample_todo]


@pytest.mark.asyncio
async def test_get_all_todos_admin_unauthorized(mock_db, user_token_payload):
    with pytest.raises(HTTPException) as exc_info:
        await todo_controller.get_all_todos_admin(user_token_payload, mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_read_todo_toggles_complete(mock_db, sample_todo):
    user = MagicMock()
    user.id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = sample_todo

    result = await todo_controller.read_todo(user, mock_db, id=1)

    assert result is None
    mock_db.query.return_value.filter.return_value.update.assert_called_once()


@pytest.mark.asyncio
async def test_read_todo_not_found(mock_db):
    user = MagicMock()
    user.id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await todo_controller.read_todo(user, mock_db, id=99)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No item found"


@pytest.mark.asyncio
async def test_create_todo_success(mock_db, user_token_payload):
    todo_item = TodoModel(
        title="Read a book",
        description="Improve daily",
        priority=3,
        complete=False,
    )

    response = await todo_controller.create_todo(
        user_token_payload, mock_db, TodoItem=todo_item
    )

    assert response == {"message": "Item created successfully"}
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_todo_missing_item(mock_db, user_token_payload):
    with pytest.raises(HTTPException) as exc_info:
        await todo_controller.create_todo(
            user_token_payload, mock_db, TodoItem=None
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Please fill in the todo item."
