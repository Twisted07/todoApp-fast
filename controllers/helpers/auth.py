# HELPER FUNCTIONS
from datetime import datetime, timedelta, timezone
from os import getenv
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError

from database import SessionLocal
from models.model import User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
db_dependency = Annotated[Session, Depends(get_db)]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

def __authenticateUser(username: str, password: str, db: db_dependency):
  user = db.query(User).filter(User.username == username.lower()).first()
  
  if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
  
  if not pwd_context.verify(password, user.hash_password):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
  
  return user

def __create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
  expires_at = datetime.now(timezone.utc) + expires_delta
  payload = {
    "sub": username,
    "id": user_id,
    "role": role,
    "expires_at": expires_at.timestamp()
  }
  print(getenv("JWT_ALGORITHM"))
  return jwt.encode(payload, getenv("JWT_SECRET"), algorithm=getenv("JWT_ALGORITHM"))

async def __get_current_user_from_token(token: Annotated[str, Depends(oauth_bearer)]):
  try:
    payload = jwt.decode(token, getenv('JWT_SECRET'), algorithms=getenv('JWT_ALGORITHM'))
    username : str = payload.get('sub')
    user_id : int = payload.get('id')
    role: str = payload.get("role")
    
    if username is None or user_id is None:
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    
    return {"username": username, "id": user_id, "role": role}
  
  except JWTError:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_message": "Could not validate user", "trace": JWTError})

def __validate_user(user):
  if user is None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized to access resource")

def __validate_admin(user):
  if user is None or user.get("role") != "admin":
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized to access resource")

user_dependency = Annotated[dict, Depends(__get_current_user_from_token)]