from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import page_owner, page_viewer
from app.models import ROLE_ORDER, Page, PageMembership, User

router = APIRouter(prefix="/api/pages/{page_id}/members", tags=["members"])


class MemberIn(BaseModel):
    user_id: int
    role: str


class MemberOut(BaseModel):
    user_id: int
    email: str
    role: str


@router.get("", response_model=list[MemberOut])
def list_members(
    page: Page = Depends(page_viewer), db: Session = Depends(get_db)
) -> list[MemberOut]:
    rows = (
        db.query(PageMembership, User)
        .join(User, User.id == PageMembership.user_id)
        .filter(PageMembership.page_id == page.id)
        .order_by(User.email)
        .all()
    )
    return [
        MemberOut(user_id=user.id, email=user.email, role=membership.role)
        for membership, user in rows
    ]


@router.put("", response_model=MemberOut)
def upsert_member(
    payload: MemberIn,
    page: Page = Depends(page_owner),
    db: Session = Depends(get_db),
) -> MemberOut:
    if payload.role not in ROLE_ORDER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role must be one of {sorted(ROLE_ORDER)}",
        )
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    membership = (
        db.query(PageMembership)
        .filter(
            PageMembership.page_id == page.id,
            PageMembership.user_id == payload.user_id,
        )
        .one_or_none()
    )
    if membership is None:
        membership = PageMembership(
            page_id=page.id, user_id=payload.user_id, role=payload.role
        )
        db.add(membership)
    else:
        membership.role = payload.role
    db.commit()
    return MemberOut(user_id=user.id, email=user.email, role=payload.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: int,
    page: Page = Depends(page_owner),
    db: Session = Depends(get_db),
) -> Response:
    membership = (
        db.query(PageMembership)
        .filter(PageMembership.page_id == page.id, PageMembership.user_id == user_id)
        .one_or_none()
    )
    if membership is not None:
        db.delete(membership)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
