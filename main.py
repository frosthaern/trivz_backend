import uvicorn
from fastapi import FastAPI

from src.database import Base, engine
from src.routers import auth

app = FastAPI(title="trivz backend server")

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
# app.include_router(room.router)
# app.include_router(session.router)
# app.include_router(ws.router)


@app.get("/")
def root():
    return {"message": "API is running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
