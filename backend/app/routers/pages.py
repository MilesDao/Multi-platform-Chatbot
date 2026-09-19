from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import (
    effective_page_role,
    get_current_user,
    page_editor,
    page_owner,
    page_viewer,
)
from app.models import KnowledgeItem, Page, PageMembership, User, role_rank
from app.security import encrypt_token

router = APIRouter(prefix="/api/pages", tags=["pages"])

OWNER_ONLY_FIELDS = {"name", "access_token", "is_active"}


class PageCreateIn(BaseModel):
    fb_page_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    access_token: str = ""
    system_prompt: str = ""
    closing_message: str = ""
    llm_model: str = ""


class PageUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    access_token: str | None = None
    system_prompt: str | None = None
    closing_message: str | None = None
    llm_model: str | None = None
    is_active: bool | None = None


class PageOut(BaseModel):
    id: int
    fb_page_id: str
    name: str
    system_prompt: str
    closing_message: str
    llm_model: str
    is_active: bool
    has_access_token: bool
    my_role: str
    knowledge_count: int
    created_at: datetime


def to_page_out(db: Session, page: Page, user: User) -> PageOut:
    knowledge_count = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.page_id == page.id, KnowledgeItem.is_active.is_(True))
        .count()
    )
    return PageOut(
        id=page.id,
        fb_page_id=page.fb_page_id,
        name=page.name,
        system_prompt=page.system_prompt,
        closing_message=page.closing_message,
        llm_model=page.llm_model,
        is_active=page.is_active,
        has_access_token=bool(page.access_token_encrypted),
        my_role=effective_page_role(db, user, page.id),
        knowledge_count=knowledge_count,
        created_at=page.created_at,
    )


@router.get("", response_model=list[PageOut])
def list_pages(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[PageOut]:
    query = db.query(Page)
    if user.role != "admin":
        query = query.join(PageMembership, PageMembership.page_id == Page.id).filter(
            PageMembership.user_id == user.id
        )
    return [to_page_out(db, page, user) for page in query.order_by(Page.id).all()]


@router.post("", response_model=PageOut, status_code=status.HTTP_201_CREATED)
def create_page(
    payload: PageCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PageOut:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    exists = (
        db.query(Page).filter(Page.fb_page_id == payload.fb_page_id).one_or_none()
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A page with this Facebook Page ID already exists",
        )
    page = Page(
        fb_page_id=payload.fb_page_id,
        name=payload.name,
        access_token_encrypted=encrypt_token(payload.access_token),
        system_prompt=payload.system_prompt,
        closing_message=payload.closing_message,
        llm_model=payload.llm_model,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    db.add(PageMembership(page_id=page.id, user_id=user.id, role="owner"))
    db.commit()
    return to_page_out(db, page, user)


@router.get("/{page_id}", response_model=PageOut)
def get_page(
    page: Page = Depends(page_viewer),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PageOut:
    return to_page_out(db, page, user)


@router.patch("/{page_id}", response_model=PageOut)
def update_page(
    payload: PageUpdateIn,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PageOut:
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if OWNER_ONLY_FIELDS & changes.keys():
        if role_rank(effective_page_role(db, user, page.id)) < role_rank("owner"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Requires page role 'owner' to change name, access token or active flag",
            )
    if "access_token" in changes:
        page.access_token_encrypted = encrypt_token(changes.pop("access_token"))
    for field, value in changes.items():
        setattr(page, field, value)
    db.commit()
    db.refresh(page)
    return to_page_out(db, page, user)


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(
    page: Page = Depends(page_owner), db: Session = Depends(get_db)
) -> Response:
    db.delete(page)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
