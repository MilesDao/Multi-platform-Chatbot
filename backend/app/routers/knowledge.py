from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import page_editor, page_viewer
from app.models import KnowledgeItem, Page
from app.services import vector_store

router = APIRouter(prefix="/api/pages/{page_id}/knowledge", tags=["knowledge"])

VALID_SOURCES = {"manual", "learned", "imported"}


class KnowledgeCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    source: str = "manual"
    is_active: bool = True


class KnowledgeUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class KnowledgeOut(BaseModel):
    id: int
    page_id: int
    title: str
    content: str
    source: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def _get_item(db: Session, page: Page, item_id: int) -> KnowledgeItem:
    item = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.id == item_id, KnowledgeItem.page_id == page.id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found"
        )
    return item


@router.get("", response_model=list[KnowledgeOut])
def list_knowledge(
    page: Page = Depends(page_viewer), db: Session = Depends(get_db)
) -> list[KnowledgeItem]:
    return (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.page_id == page.id)
        .order_by(KnowledgeItem.id)
        .all()
    )


@router.post("", response_model=KnowledgeOut, status_code=status.HTTP_201_CREATED)
def create_knowledge(
    payload: KnowledgeCreateIn,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
) -> KnowledgeItem:
    if payload.source not in VALID_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"source must be one of {sorted(VALID_SOURCES)}",
        )
    item = KnowledgeItem(
        page_id=page.id,
        title=payload.title,
        content=payload.content,
        source=payload.source,
        is_active=payload.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    vector_store.build_index(db, page.id)
    return item


@router.patch("/{item_id}", response_model=KnowledgeOut)
def update_knowledge(
    item_id: int,
    payload: KnowledgeUpdateIn,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
) -> KnowledgeItem:
    item = _get_item(db, page, item_id)
    if payload.title is not None:
        item.title = payload.title
    if payload.content is not None:
        item.content = payload.content
    if payload.is_active is not None:
        item.is_active = payload.is_active
    db.commit()
    db.refresh(item)
    vector_store.build_index(db, page.id)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge(
    item_id: int,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
) -> Response:
    item = _get_item(db, page, item_id)
    db.delete(item)
    db.commit()
    vector_store.build_index(db, page.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
