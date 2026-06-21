from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from database import SessionLocal
from models.model import Todo
from sqlalchemy.orm import Session

from models.dto.model_pydantic import TodoModel
from controllers.helpers.auth import __validate_admin, __validate_user, db_dependency, user_dependency

router = APIRouter(prefix="/todos")
    
@router.get('/')
async def get_all_todos(user: user_dependency, db: db_dependency):
    __validate_user(user)
    return db.query(Todo).filter(Todo.owner == user.get("id")).all()


@router.get('/admin')
async def get_all_todos_admin(user: user_dependency, db: db_dependency):
    __validate_admin(user)
    return db.query(Todo).all()
    
    

@router.put('/{id}')
async def read_todo(user: user_dependency, db: db_dependency, id: int = Path(gt=0)):
    __validate_user(user)
    todo = db.query(Todo).filter(Todo.id == id and Todo.owner == user.id).first()
    
    if todo is not None:
        db.query(Todo).filter(Todo.id == id).update({Todo.complete: not todo.complete})
        return
    raise HTTPException(status_code=404, detail="No item found")


@router.post('/')
async def create_todo(user: user_dependency, db: db_dependency, TodoItem:TodoModel):
    __validate_user(user)
    if TodoItem is not None:
        db.add(Todo(**TodoItem.model_dump(), owner=user.get("id")))
        db.commit()
        return {"message": "Item created successfully"}

    raise HTTPException(status_code=404, detail="Please fill in the todo item.")