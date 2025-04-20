from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
import uuid
import time
from datetime import datetime

app = FastAPI()
security = HTTPBearer()

fake_db = {
    "users": {},
    "pvzs": {},
    "receptions": {},
    "products": {},
}


class User(BaseModel):
    id: str
    email: EmailStr
    password: str
    role: str
    token: Optional[str] = None


class Token(BaseModel):
    token: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class DummyLogin(BaseModel):
    role: str


class PVZ(BaseModel):
    id: str
    registrationDate: str
    city: str


# Auth endpoints


@app.post("/dummyLogin", response_model=Token)
def dummy_login(data: DummyLogin):
    if data.role not in ["employee", "moderator"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    token = str(uuid.uuid4())
    return {"token": token}


@app.post("/register", response_model=User)
def register(user: UserRegister):
    if user.role not in ["employee", "moderator"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    if user.email in fake_db["users"]:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    token = str(uuid.uuid4())

    new_user = {
        "id": user_id,
        "email": user.email,
        "password": user.password,
        "role": user.role,
        "token": token,
    }

    fake_db["users"][user.email] = new_user
    return new_user


@app.post("/login", response_model=Token)
def login(user: UserLogin):
    if user.email not in fake_db["users"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    db_user = fake_db["users"][user.email]

    if db_user["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = str(uuid.uuid4())
    db_user["token"] = token
    return {"token": token}


# Helper function to verify tokens
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    for user in fake_db["users"].values():
        if user["token"] == token:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.post("/pvz")
def create_pvz(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] != "moderator":
        raise HTTPException(status_code=403, detail="Only moderators can create PVZs")
    return {"message": "PVZ creation endpoint"}


@app.get("/pvz")
def get_pvz_list(current_user: Dict = Depends(get_current_user)):
    return {"message": "PVZ list endpoint"}


@app.post("/receptions")
def create_reception(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403, detail="Only employees can create receptions"
        )
    return {"message": "Reception creation endpoint"}


@app.post("/products")
def add_product(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] != "employee":
        raise HTTPException(status_code=403, detail="Only employees can add products")
    return {"message": "Product addition endpoint"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
