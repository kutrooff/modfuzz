from typing import Dict

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel


app = FastAPI(
    title="ModFuzz Test Users API",
    version="1.0.0",
    description="Simple API for testing stateless and stateful fuzzing",
)

users: Dict[int, dict] = {}
next_user_id = 1


class UserCreate(BaseModel):
    name: str
    email: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/users", status_code=201)
def create_user(user: UserCreate, response: Response):
    global next_user_id

    user_id = next_user_id
    next_user_id += 1

    created_user = {
        "id": user_id,
        "name": user.name,
        "email": user.email,
    }

    users[user_id] = created_user

    response.headers["Location"] = f"/users/{user_id}"

    return created_user


@app.get("/users/{userId}")
def get_user(userId: int):
    user = users.get(userId)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.patch("/users/{userId}")
def update_user(userId: int, update: UserUpdate):
    user = users.get(userId)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if update.name is not None:
        user["name"] = update.name

    if update.email is not None:
        user["email"] = update.email

    return user


@app.delete("/users/{userId}", status_code=204)
def delete_user(userId: int):
    if userId not in users:
        raise HTTPException(status_code=404, detail="User not found")

    del users[userId]
    return None