from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> dict:
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(400, "email already registered")
    u = User(email=payload.email.lower(), hashed_password=hash_password(payload.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"id": u.id, "email": u.email}


@router.post('/login')
def login(payload: LoginIn, db: Session = Depends(get_db)) -> dict:
    u = db.query(User).filter(User.email == payload.email.lower()).first()
    if not u or not verify_password(payload.password, u.hashed_password):
        raise HTTPException(401, "invalid credentials")
    return {"access_token": create_access_token(u.id), "token_type": "bearer"}
