from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Page, PageMembership, User, role_rank
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise CREDENTIALS_ERROR
    subject = decode_access_token(credentials.credentials)
    if subject is None:
        raise CREDENTIALS_ERROR
    user = db.get(User, int(subject)) if subject.isdigit() else None
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    return user


def authorize_page(db: Session, user: User, page_id: int, min_role: str) -> Page:
    """Return the page if the user holds at least `min_role` on it.

    A global admin is treated as `owner` on every page. Raises 404 when the page
    does not exist and 403 when the user's role is not high enough.
    """
    page = db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    if user.role == "admin":
        return page
    membership = (
        db.query(PageMembership)
        .filter(PageMembership.page_id == page_id, PageMembership.user_id == user.id)
        .one_or_none()
    )
    if membership is None or role_rank(membership.role) < role_rank(min_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires page role '{min_role}'",
        )
    return page


def effective_page_role(db: Session, user: User, page_id: int) -> str:
    """The role string to show in the UI: 'owner' for admins, else the membership role."""
    if user.role == "admin":
        return "owner"
    membership = (
        db.query(PageMembership)
        .filter(PageMembership.page_id == page_id, PageMembership.user_id == user.id)
        .one_or_none()
    )
    return membership.role if membership else "none"


def _page_dependency(min_role: str) -> Callable[..., Page]:
    def dependency(
        page_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> Page:
        return authorize_page(db, user, page_id, min_role)

    return dependency


page_viewer = _page_dependency("viewer")
page_editor = _page_dependency("editor")
page_owner = _page_dependency("owner")
