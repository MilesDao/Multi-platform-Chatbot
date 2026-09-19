import json
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from config import Config

class LeadInfo(BaseModel):
    cccd_image: bool = Field(description="True nếu người dùng đã gửi ảnh chụp CCCD, ngược lại False")
    hocba_image: bool = Field(description="True nếu người dùng đã gửi ảnh chụp học bạ, ngược lại False")
    phone_number: str = Field(description="Số điện thoại của người dùng, hoặc rỗng nếu chưa có")
    major: str = Field(description="Ngành học người dùng muốn đăng ký, hoặc rỗng nếu chưa có")
    address: str = Field(description="Địa chỉ cụ thể của người dùng, hoặc rỗng nếu chưa có")

class LeadManager:
    def __init__(self):
        # We will use Gemini with structured output via OpenAI adapter
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            openai_api_key=Config.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0,
        )
        # Use structured output for extraction
        self.extractor = self.llm.with_structured_output(LeadInfo)
        
        # State tracking in-memory (For production, use Redis or DB)
        self.user_states = {}

    def extract_info_from_message(self, message: str, has_cccd_attachment: bool, has_hocba_attachment: bool) -> LeadInfo:
        prompt = f"""
Phân tích tin nhắn của người dùng và trích xuất thông tin xét tuyển (nếu có).
Tin nhắn: "{message}"

Ghi chú về tệp đính kèm:
- Có ảnh CCCD đính kèm: {has_cccd_attachment}
- Có ảnh Học bạ đính kèm: {has_hocba_attachment}
"""
        try:
            extracted = self.extractor.invoke(prompt)
            return extracted
        except Exception as e:
            print(f"Error extracting structured output: {e}")
            # Fallback empty state
            return LeadInfo(
                cccd_image=has_cccd_attachment,
                hocba_image=has_hocba_attachment,
                phone_number="",
                major="",
                address=""
            )

    def process_message(self, sender_id: str, message: str, attachments: list) -> bool:
        """
        Process incoming message, update state, and return True if Lead is successfully acquired.
        """
        # 1. Initialize state if new
        if sender_id not in self.user_states:
            self.user_states[sender_id] = {
                "cccd_image": False,
                "hocba_image": False,
                "phone_number": "",
                "major": "",
                "address": "",
                "is_successful": False
            }
            
        state = self.user_states[sender_id]
        if state["is_successful"]:
            return True # Already successful

        # 2. Heuristics for attachments
        has_cccd_attachment = False
        has_hocba_attachment = False
        
        # Simple heuristic: if there is an image, we can try to guess what it is, 
        # but for simplicity, we let the LLM guess based on the message context (e.g. "Đây là CCCD của em")
        # Since we don't have OCR right now, if there is an attachment and user says "cccd", we mark it.
        if attachments:
            msg_lower = message.lower()
            if "cccd" in msg_lower or "căn cước" in msg_lower or "chứng minh" in msg_lower:
                has_cccd_attachment = True
            elif "học bạ" in msg_lower or "điểm" in msg_lower:
                has_hocba_attachment = True
            else:
                # If they just send an image without text, we might mark CCCD by default if missing
                if not state["cccd_image"]:
                    has_cccd_attachment = True
                elif not state["hocba_image"]:
                    has_hocba_attachment = True

        # 3. Extract info via LLM
        extracted = self.extract_info_from_message(message, has_cccd_attachment, has_hocba_attachment)

        # 4. Merge state
        if extracted.cccd_image:
            state["cccd_image"] = True
        if extracted.hocba_image:
            state["hocba_image"] = True
        if extracted.phone_number:
            state["phone_number"] = extracted.phone_number
        if extracted.major:
            state["major"] = extracted.major
        if extracted.address:
            state["address"] = extracted.address

        # 5. Check success
        if (state["cccd_image"] and 
            state["hocba_image"] and 
            state["phone_number"] and 
            state["major"] and 
            state["address"]):
            state["is_successful"] = True
            self.save_successful_lead(sender_id, state)
            return True
            
        return False

    def save_successful_lead(self, sender_id: str, state: dict):
        file_path = Config.REPORTS_DIR / f"lead_{sender_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        print(f"Lead {sender_id} acquired successfully!")
