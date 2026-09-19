import os
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from config import Config

class ChatbotEngine:
    def __init__(self):
        # Initialize Embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # Initialize FAISS Vector Store
        self.vector_store = self._build_vector_store()
        
        # Initialize LLM via OpenRouter
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            openai_api_key=Config.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.7,
            max_tokens=1000
        )
        
        # Human-like System Prompt
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""Bạn là nhân viên tư vấn tuyển sinh thân thiện, nhiệt tình của trường.
Mục tiêu của bạn là giúp học sinh đăng ký xét tuyển online thành công dựa trên thông tin sau:
{context}

YÊU CẦU QUAN TRỌNG VỀ CÁCH TRẢ LỜI:
- Trả lời ngắn gọn, thân thiện, xưng hô "cô" và "em" hoặc "trường" và "bạn".
- TUYỆT ĐỐI KHÔNG viết một đoạn văn dài dòng.
- BẮT BUỘC ngắt đoạn văn thành các câu ngắn (mỗi đoạn 1-2 câu). Dùng dấu xuống dòng giữa các ý.
- Nếu học sinh hỏi về hồ sơ, hãy nói rõ các loại giấy tờ cần thiết. Khéo léo hỏi thêm thông tin nếu học sinh chưa cung cấp đủ (SĐT, Ảnh CCCD, Ảnh học bạ, Ngành, Địa chỉ).

Câu hỏi của học sinh: {question}
Trả lời:"""
        )

    def _build_vector_store(self):
        # Load documents from DATA_DIR
        loader = DirectoryLoader(str(Config.DATA_DIR), glob="*.txt", loader_cls=TextLoader)
        docs = loader.load()
        
        if not docs:
            # Create a dummy index if no documents found yet
            return FAISS.from_texts(["Trường đang xét tuyển online."], self.embeddings)
            
        return FAISS.from_documents(docs, self.embeddings)

    def get_response(self, question: str) -> str:
        # Retrieve context
        docs = self.vector_store.similarity_search(question, k=3)
        context = "\n".join([doc.page_content for doc in docs])
        
        # Generate response
        prompt_val = self.prompt_template.format(context=context, question=question)
        response = self.llm.invoke(prompt_val)
        return response.content
