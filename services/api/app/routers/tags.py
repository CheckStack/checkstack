from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tag import Tag

router = APIRouter(prefix="/tags", tags=["tags"])


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str | None = Field(default=None, max_length=32)


class TagRead(BaseModel):
    id: int
    name: str
    color: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=TagRead)
def create_tag(body: TagCreate, db: Session = Depends(get_db)) -> Tag:
    exists = db.query(Tag).filter(Tag.name == body.name).first()
    if exists:
        raise HTTPException(400, "tag with this name exists")
    t = Tag(name=body.name, color=body.color)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.get("", response_model=list[TagRead])
def list_tags(db: Session = Depends(get_db)) -> list[Tag]:
    return db.query(Tag).order_by(Tag.name).all()
