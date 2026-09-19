from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models import User
from app.routers.auth import UserOut
from app.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])

VALID_GLOBAL_ROLES = {"admin", "member"}


class UserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = "member"


class UserUpdateIn(BaseModel):
    role: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None


def _validate_role(role: str) -> None:
    if role not in VALID_GLOBAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role must be one of {sorted(VALID_GLOBAL_ROLES)}",
        )


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    _validate_role(payload.role)
    exists = db.query(User).filter(User.email == payload.email).one_or_none()
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.role is not None:
        _validate_role(payload.role)
        user.role = payload.role
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=UserOut)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
