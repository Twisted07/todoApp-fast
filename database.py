from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQL_ALCHEMY_DB_URL = "sqlite:///./todo.db"
# sqlalchemy.url = postgresql+psycopg2://user:password@localhost:5432/your_database


engine = create_engine(SQL_ALCHEMY_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()