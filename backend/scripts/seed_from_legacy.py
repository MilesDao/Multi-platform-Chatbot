"""Import the legacy data/*.txt knowledge base into a page.

Usage:
    python -m scripts.seed_from_legacy \
        --fb-page-id 1234567890 \
        --name "Hateco Tuyen Sinh" \
        --access-token EAAG... \
        [--admin-email boss@hateco.vn --admin-password secret123]
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.db import SessionLocal, init_db
from app.models import KnowledgeItem, Page, PageMembership, User
from app.security import encrypt_token, hash_password
from app.services import vector_store

DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


def seed_page(
    db: Session,
    fb_page_id: str,
    name: str,
    access_token: str,
    data_dir: Path,
) -> tuple[Page, int]:
    """Create the page if needed and import every *.txt file as a knowledge item.

    Returns (page, number of items imported). Files whose title already exists on
    the page are skipped, so re-running the script is safe.
    """
    page = db.query(Page).filter(Page.fb_page_id == fb_page_id).one_or_none()
    if page is None:
        page = Page(
            fb_page_id=fb_page_id,
            name=name,
            access_token_encrypted=encrypt_token(access_token),
        )
        db.add(page)
        db.commit()
        db.refresh(page)

    existing_titles = {
        title
        for (title,) in db.query(KnowledgeItem.title)
        .filter(KnowledgeItem.page_id == page.id)
        .all()
    }

    imported = 0
    if data_dir.is_dir():
        for path in sorted(data_dir.glob("*.txt")):
            title = path.stem
            if title in existing_titles:
                continue
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            db.add(
                KnowledgeItem(
                    page_id=page.id, title=title, content=content, source="imported"
                )
            )
            existing_titles.add(title)
            imported += 1

    if imported:
        db.commit()
    vector_store.build_index(db, page.id)
    return page, imported


def _ensure_admin(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(email=email, password_hash=hash_password(password), role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed a page from the legacy data folder")
    parser.add_argument("--fb-page-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--access-token", default="")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--admin-email", default="")
    parser.add_argument("--admin-password", default="")
    args = parser.parse_args(argv)

    init_db()
    db = SessionLocal()
    try:
        page, imported = seed_page(
            db, args.fb_page_id, args.name, args.access_token, Path(args.data_dir)
        )
        print(f"Page '{page.name}' (id={page.id}): imported {imported} knowledge items")

        if args.admin_email and args.admin_password:
            admin = _ensure_admin(db, args.admin_email, args.admin_password)
            membership = (
                db.query(PageMembership)
                .filter(
                    PageMembership.page_id == page.id,
                    PageMembership.user_id == admin.id,
                )
                .one_or_none()
            )
            if membership is None:
                db.add(
                    PageMembership(page_id=page.id, user_id=admin.id, role="owner")
                )
                db.commit()
            print(f"Admin '{admin.email}' owns page {page.id}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
