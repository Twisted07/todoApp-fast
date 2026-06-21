from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from database import Base


class User(Base):
  __tablename__ = "users"
  
  id = Column(Integer, primary_key=True, index=True)
  email = Column(String, unique=True)
  username = Column(String, unique=True)
  first_name = Column(String)
  last_name = Column(String)
  hash_password = Column(String)
  is_active = Column(Boolean, default=True)
  role = Column(String)

class Todo(Base):
  __tablename__ = "todo"
  
  id = Column(Integer, primary_key=True, index=True)
  title = Column(String)
  description = Column(String)
  priority = Column(Integer)
  complete = Column(Boolean, default=False)
  owner = Column(Integer, ForeignKey(User.id))