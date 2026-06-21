from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from models.dto.JwtResponse import JwtResponse
from models.dto.model_pydantic import UserBaseModel, UserResponseBaseModel, UserSigninBaseModel
from models.model import User
from controllers.helpers.auth import __authenticateUser, __create_access_token, __validate_user, db_dependency, pwd_context, user_dependency

router = APIRouter(prefix="/auth") 



@router.get("/login")
async def login(db: db_dependency, login_credentials:UserSigninBaseModel):
  user_data = db.query(User).filter(User.username == login_credentials.username).first()
  if pwd_context.verify(login_credentials.password, user_data.hash_password):
    user_response = UserResponseBaseModel(
      username=user_data.username,
      id=user_data.id,
      first_name=user_data.first_name,
      last_name=user_data.last_name,
      email=user_data.email,
      role=user_data.role,
      is_active=user_data.is_active
    )
    return {"message": "login successful", "data": user_response}
  
  raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect credentials")


@router.post("/create-user", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user:UserBaseModel):
  new_user = User(
    username=user.username,
    email=user.email,
    first_name=user.first_name,
    last_name=user.last_name,
    hash_password=pwd_context.hash(user.password),
    role=user.role,
    is_active=True
  )
  
  db.add(new_user)
  db.commit()
  return {"message": "User created successfully."}


@router.post("/token", response_model=JwtResponse)
async def login_for_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
  authenticated_user = __authenticateUser(form_data.username, form_data.password, db)
  
  if authenticated_user:
    token = __create_access_token(authenticated_user.username, authenticated_user.id, authenticated_user.role, timedelta(minutes=30))
    return {"message": "user authenticated successfully", "access_token": token, "type": "bearer"}
  
  raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User could not be authenticated")


@router.get("/users")
async def get_all_users(user: user_dependency, db:db_dependency):
  __validate_user(user)
  users = db.query(User).filter(User.id == user.get("id")).all()
  return {"users": users if users else []}
  
  
@router.get("/admin/users")
async def get_all_admin_users(user: user_dependency, db:db_dependency):
  __validate_user(user)
  
  if user.get("role") != "admin":
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are unauthorized to access this resource")
  
  users = db.query(User).all()
  return {"users": users if users else []}