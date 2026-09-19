import asyncio
import requests
from fastapi import FastAPI, Request, Response, BackgroundTasks
from config import Config
from chatbot_engine import ChatbotEngine
from lead_manager import LeadManager

app = FastAPI(title="Hateco AI Facebook Chatbot")

# Initialize Engine and Manager
chatbot = ChatbotEngine()
lead_manager = LeadManager()

def send_typing_indicator(sender_id: str):
    """Gửi trạng thái 'đang gõ' cho người dùng"""
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={Config.PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": sender_id},
        "sender_action": "typing_on"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending typing indicator: {e}")

def send_message(sender_id: str, text: str):
    """Gửi tin nhắn văn bản về lại Facebook"""
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={Config.PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": sender_id},
        "message": {"text": text}
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

async def process_webhook_event(event: dict):
    """Xử lý sự kiện tin nhắn trong background để không làm timeout Webhook"""
    sender_id = event["sender"]["id"]
    message_data = event.get("message", {})
    
    text = message_data.get("text", "")
    attachments = message_data.get("attachments", [])
    
    # 1. Bật typing indicator lập tức (giống con người)
    send_typing_indicator(sender_id)
    
    # 2. Xử lý Logic thu thập Lead (Success Metrics)
    is_success_now = lead_manager.process_message(sender_id, text, attachments)
    
    # 3. Chạy AI RAG để sinh câu trả lời
    ai_response = chatbot.get_response(text)
    
    # 4. Giả lập thời gian gõ phím của người thật
    # Delay nhỏ tùy theo độ dài câu (ví dụ 1 giây cho mỗi 50 ký tự, tối đa 3 giây)
    delay_time = min(3, len(ai_response) / 50)
    await asyncio.sleep(delay_time)
    
    # 5. Gửi câu trả lời về cho user
    send_message(sender_id, ai_response)
    
    # 6. Nếu phiên này vừa đạt success, gửi thêm tin nhắn chúc mừng/thông báo nhập học
    if is_success_now and lead_manager.user_states[sender_id].get("is_successful"):
        # We only notify once, we can track notified state if needed, 
        # but here we just append if it JUST turned successful
        await asyncio.sleep(2)
        send_typing_indicator(sender_id)
        await asyncio.sleep(1)
        success_msg = ("Tuyệt vời! Nhà trường đã nhận đủ hồ sơ trực tuyến của em "
                       "(CCCD, Học bạ, SĐT, Ngành và Địa chỉ). Giấy báo nhập học sẽ "
                       "được gửi về địa chỉ của em sớm nhất nhé!")
        send_message(sender_id, success_msg)


@app.get("/webhook")
async def verify_webhook(request: Request):
    """Endpoint dùng để Facebook xác thực Webhook"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == Config.VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return Response(content=challenge, status_code=200)
        else:
            return Response(content="Forbidden", status_code=403)
    return Response(content="Bad Request", status_code=400)


@app.post("/webhook")
async def handle_messages(request: Request, background_tasks: BackgroundTasks):
    """Endpoint nhận tin nhắn từ Facebook"""
    body = await request.json()
    
    if body.get("object") == "page":
        for entry in body.get("entry", []):
            for event in entry.get("messaging", []):
                if event.get("message") and not event["message"].get("is_echo"):
                    # Xử lý tin nhắn trong background task
                    background_tasks.add_task(process_webhook_event, event)
                    
        return Response(content="EVENT_RECEIVED", status_code=200)
    
    return Response(content="Not Found", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
