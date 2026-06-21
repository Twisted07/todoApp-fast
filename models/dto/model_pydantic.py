import re
from pydantic import BaseModel, EmailStr, Field, field_validator


class TodoModel(BaseModel):  
  title: str = Field(min_length=3)
  description: str = Field(min_length=1, max_length=100)
  priority: int = Field(gt=0, lt=6)
  complete: bool = Field(default=False)

  model_config = {
    'json_schema_extra': {
      "example" : {
        "title": "Read a book",
        "description": "Read a book that improves me daily",
        "priority": 5
      }
    }
  }


class UserBaseModel(BaseModel):
  first_name: str = Field(min_length=3)
  last_name: str = Field(min_length=3)
  email: EmailStr
  password: str
  username: str = Field(min_length=3)
  role: str
  
  @field_validator('password')
  @classmethod
  def validate_password(cls, pswd: str) -> str:
    # Length validation
    if len(pswd) < 8:
      raise ValueError("Password must be at least 8 characters long.")
    # Uppercase validation
    if not any(char.isupper() for char in pswd):
      raise ValueError("Password must contain at least 1 Uppercase character.")
    # Lowercase validation
    if not any(char.islower() for char in pswd):
      raise ValueError("Password must contain at least 1 lowercase character.")
    # Digit validation
    if not any(char.isdigit() for char in pswd):
      raise ValueError("Password must contain at least 1 digit.")
    # Special character validation
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pswd):
      raise ValueError("Password must contain at least one special character/symbol.")
    # Return the validated password
    return pswd


  model_config = {
    "json_schema_extra": {
      "example": {
        "first_name": "John",
        "last_name": "Doe",
        "username": "john_doe",
        "email": "john.doe@email.com",
        "password": "P@$$word123",
        "role": "owner"
      }
    }
  }
  
  
class UserSigninBaseModel(BaseModel):
  username: str = Field(min_length=3)
  password: str
  
class UserResponseBaseModel(BaseModel):
  username: str = Field(min_length=3)
  first_name: str = Field(min_length=3)
  last_name: str = Field(min_length=3)
  email: str = EmailStr
  role: str
  is_active: bool
  id: int = Field(gt=0)