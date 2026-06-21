from fastapi import FastAPI
import models.model as model
from database import engine
from controllers import auth
from controllers import todo
from dotenv import load_dotenv

app = FastAPI()
model.Base.metadata.create_all(bind=engine)
app.include_router(auth.router, tags=["Auth"])
app.include_router(todo.router, tags=["Todo"])
load_dotenv()

def main():
    print("Welcome to do!")


if __name__ == "__main__":
    main()
