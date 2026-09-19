import shutil
import threading

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeItem

EMPTY_PLACEHOLDER = "Chưa có thông tin nào được cấu hình cho trang này."

_lock = threading.Lock()
_embeddings: Embeddings | None = None
_cache: dict[int, FAISS] = {}


def get_embeddings() -> Embeddings:
    """Lazily build the sentence-transformers embedder. Tests monkeypatch this."""
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        _embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
    return _embeddings


def _index_path(page_id: int) -> str:
    return str(settings.index_dir / f"page_{page_id}")


def _knowledge_texts(db: Session, page_id: int) -> list[str]:
    items = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.page_id == page_id, KnowledgeItem.is_active.is_(True))
        .order_by(KnowledgeItem.id)
        .all()
    )
    texts = [f"{item.title}\n{item.content}".strip() for item in items if item.content.strip()]
    return texts or [EMPTY_PLACEHOLDER]


def build_index(db: Session, page_id: int) -> FAISS:
    """Rebuild a page's index from the database and persist it to disk."""
    store = FAISS.from_texts(_knowledge_texts(db, page_id), get_embeddings())
    store.save_local(_index_path(page_id))
    with _lock:
        _cache[page_id] = store
    return store


def get_index(db: Session, page_id: int) -> FAISS:
    with _lock:
        cached = _cache.get(page_id)
    if cached is not None:
        return cached

    path = settings.index_dir / f"page_{page_id}"
    if path.exists():
        store = FAISS.load_local(
            str(path), get_embeddings(), allow_dangerous_deserialization=True
        )
        with _lock:
            _cache[page_id] = store
        return store

    return build_index(db, page_id)


def search(db: Session, page_id: int, query: str, k: int = 3) -> list[str]:
    store = get_index(db, page_id)
    return [doc.page_content for doc in store.similarity_search(query, k=k)]


def invalidate(page_id: int) -> None:
    """Drop the in-memory index and the on-disk copy so the next read rebuilds."""
    with _lock:
        _cache.pop(page_id, None)
    path = settings.index_dir / f"page_{page_id}"
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def clear_cache() -> None:
    """Test helper: forget every cached index without touching disk."""
    with _lock:
        _cache.clear()
