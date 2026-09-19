from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, page_editor, page_viewer
from app.models import Page, Suggestion, User
from app.services import learning

router = APIRouter(prefix="/api/pages/{page_id}", tags=["learning"])

VALID_STATUSES = {"pending", "approved", "rejected"}


class SuggestionOut(BaseModel):
    id: int
    page_id: int
    question: str
    answer: str
    occurrences: int
    status: str
    created_at: datetime
    reviewed_at: datetime | None
    knowledge_item_id: int | None

    model_config = {"from_attributes": True}


class MineOut(BaseModel):
    created: int
    suggestions: list[SuggestionOut]


class ApproveIn(BaseModel):
    title: str | None = None
    answer: str | None = None


def _get_suggestion(db: Session, page: Page, suggestion_id: int) -> Suggestion:
    suggestion = (
        db.query(Suggestion)
        .filter(Suggestion.id == suggestion_id, Suggestion.page_id == page.id)
        .one_or_none()
    )
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found"
        )
    return suggestion


@router.post("/learning/mine", response_model=MineOut)
def mine(
    page: Page = Depends(page_editor), db: Session = Depends(get_db)
) -> MineOut:
    created = learning.mine_suggestions(db, page.id)
    return MineOut(
        created=len(created),
        suggestions=[SuggestionOut.model_validate(item) for item in created],
    )


@router.get("/suggestions", response_model=list[SuggestionOut])
def list_suggestions(
    status_filter: str = Query(default="pending", alias="status"),
    page: Page = Depends(page_viewer),
    db: Session = Depends(get_db),
) -> list[Suggestion]:
    query = db.query(Suggestion).filter(Suggestion.page_id == page.id)
    if status_filter != "all":
        if status_filter not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"status must be 'all' or one of {sorted(VALID_STATUSES)}",
            )
        query = query.filter(Suggestion.status == status_filter)
    return query.order_by(Suggestion.occurrences.desc(), Suggestion.id.desc()).all()


@router.post("/suggestions/{suggestion_id}/approve", response_model=SuggestionOut)
def approve(
    suggestion_id: int,
    payload: ApproveIn,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Suggestion:
    suggestion = _get_suggestion(db, page, suggestion_id)
    if suggestion.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Suggestion is already {suggestion.status}",
        )
    learning.approve_suggestion(
        db, suggestion, user, title=payload.title, answer=payload.answer
    )
    db.refresh(suggestion)
    return suggestion


@router.post("/suggestions/{suggestion_id}/reject", response_model=SuggestionOut)
def reject(
    suggestion_id: int,
    page: Page = Depends(page_editor),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Suggestion:
    suggestion = _get_suggestion(db, page, suggestion_id)
    if suggestion.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Suggestion is already {suggestion.status}",
        )
    return learning.reject_suggestion(db, suggestion, user)
