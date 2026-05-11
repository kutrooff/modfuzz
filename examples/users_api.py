from typing import Dict
import time
import random

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel


app = FastAPI(
    title="ModFuzz Test Users API",
    version="1.0.0",
    description="Problematic API for fuzzing and anomaly detection",
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
    """
    Endpoint intentionally contains problematic logic
    for fuzzing experiments.
    """

    global next_user_id

    # -----------------------------------
    # Hidden error
    # -----------------------------------
    if user.name.lower() == "error":
        return {
            "status": "error",
            "message": "database failure detected"
        }

    # -----------------------------------
    # Simulated crash
    # -----------------------------------
    if user.name.lower() == "crash":
        raise Exception("simulated database crash")

    # -----------------------------------
    # Slow response
    # -----------------------------------
    if user.name.lower() == "slow":
        time.sleep(3)

    # -----------------------------------
    # Empty response anomaly
    # -----------------------------------
    if user.name.lower() == "empty":
        return {}

    # -----------------------------------
    # Invalid JSON / malformed response
    # -----------------------------------
    if user.name.lower() == "invalid":
        return PlainTextResponse(
            content="INVALID_JSON_RESPONSE",
            status_code=200
        )

    # -----------------------------------
    # Random intermittent failure
    # -----------------------------------
    if user.name.lower() == "random":
        if random.choice([True, False]):
            raise HTTPException(
                status_code=503,
                detail="temporary service unavailable"
            )

    # -----------------------------------
    # Extremely large response
    # -----------------------------------
    if user.name.lower() == "large":
        return {
            "payload": "A" * 100000
        }

    # -----------------------------------
    # Normal behavior
    # -----------------------------------
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

    # Negative IDs simulate validation weakness
    if userId < 0:
        return {
            "warning": "negative identifier accepted",
            "userId": userId
        }

    user = users.get(userId)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.patch("/users/{userId}")
def update_user(userId: int, update: UserUpdate):

    # Simulated timeout
    if update.name == "timeout":
        time.sleep(5)

    user = users.get(userId)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Simulated hidden logic error
    if update.name == "hidden":
        return {
            "result": "update failed internally"
        }

    if update.name is not None:
        user["name"] = update.name

    if update.email is not None:
        user["email"] = update.email

    return user


@app.delete("/users/{userId}", status_code=204)
def delete_user(userId: int):

    # Random instability
    if random.randint(1, 10) == 5:
        raise HTTPException(
            status_code=500,
            detail="unexpected delete failure"
        )

    if userId not in users:
        raise HTTPException(status_code=404, detail="User not found")

    del users[userId]

    return None