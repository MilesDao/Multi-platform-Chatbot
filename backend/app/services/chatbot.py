from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Page
from app.services import vector_store

DEFAULT_SYSTEM_PROMPT = """Bạn là nhân viên tư vấn tuyển sinh thân thiện, nhiệt tình của trường.
Nhiệm vụ của bạn là trả lời câu hỏi của học sinh và phụ huynh về tuyển sinh, đặc biệt là
ngoài giờ hành chính khi tư vấn viên chưa thể trả lời ngay.

YÊU CẦU QUAN TRỌNG VỀ CÁCH TRẢ LỜI:
- Trả lời ngắn gọn, thân thiện, xưng hô "cô" và "em" hoặc "trường" và "bạn".
- TUYỆT ĐỐI KHÔNG viết một đoạn văn dài dòng.
- BẮT BUỘC ngắt đoạn văn thành các câu ngắn (mỗi đoạn 1-2 câu). Dùng dấu xuống dòng giữa các ý.
- CHỈ trả lời dựa trên thông tin tham khảo được cung cấp, không bịa thêm.
- TUYỆT ĐỐI KHÔNG hỏi hoặc thu thập thông tin cá nhân của học sinh (CCCD, học bạ, số điện
  thoại, ngành, địa chỉ...). Nếu học sinh cần tư vấn sâu hơn hoặc muốn đăng ký, hãy khuyến
  khích các em gọi điện trực tiếp cho trường để được hỗ trợ."""

ANSWER_TEMPLATE = """{system_prompt}

THÔNG TIN THAM KHẢO CỦA TRANG (chỉ dùng thông tin này, không bịa thêm):
{context}

Câu hỏi của khách: {question}
Trả lời:"""


def build_llm(model: str = "", temperature: float = 0.7) -> ChatOpenAI:
    """Build an OpenRouter-backed chat model. Tests monkeypatch this function."""
    return ChatOpenAI(
        model=model or settings.llm_model,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_base_url,
        temperature=temperature,
        max_tokens=1000,
    )


def build_prompt(page: Page, context_chunks: list[str], question: str) -> str:
    system_prompt = (page.system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT
    return ANSWER_TEMPLATE.format(
        system_prompt=system_prompt,
        context="\n---\n".join(context_chunks),
        question=question,
    )


def generate_answer(db: Session, page: Page, question: str) -> tuple[str, list[str]]:
    """Answer one question for one page. Returns (answer, retrieved context chunks)."""
    context_chunks = vector_store.search(db, page.id, question, k=3)
    prompt = build_prompt(page, context_chunks, question)
    llm = build_llm(page.llm_model or "")
    response = llm.invoke(prompt)
    return str(response.content), context_chunks
