import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

class AIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    def summarize_contract(self, contract_detail: str) -> str:
        if not self.client:
            return "Lỗi: Chưa cấu hình GEMINI_API_KEY trong file .env!"
        try:
            prompt = f"Tóm tắt hợp đồng sau ngắn gọn:\n{contract_detail}"
            response = self.client.models.generate_content(
                model='models/gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            return f"Lỗi gọi Gemini API: {str(e)}"

    def generate_payment_reminder(self, tenant_name: str, apartment: str, amount: str, due_date: str) -> str:
        if not self.client:
            return "Lỗi: Chưa cấu hình GEMINI_API_KEY!"
        try:
            prompt = f"Soạn thông báo nhắc đóng tiền nhà lịch sự gửi khách thuê: {tenant_name}, Phòng: {apartment}, Số tiền: {amount} VNĐ, Hạn đóng: {due_date}."
            response = self.client.models.generate_content(
                model='models/gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            return f"Lỗi gọi Gemini API: {str(e)}"

    def answer_regulation(self, question: str) -> str:
        if not self.client:
            return "Lỗi: Chưa cấu hình GEMINI_API_KEY!"
        try:
            knowledge_base = """
            QUY ĐỊNH TÒA NHÀ:
            1. Thú cưng: Được nuôi chó/mèo nhỏ dưới 10kg nhưng phải giữ vệ sinh.
            2. Giờ giấc: Yên tĩnh từ 22:00 đến 06:00 sáng.
            3. Thanh toán: Tiền nhà đóng từ ngày 01 đến ngày 05 hằng tháng.
            """
            prompt = f"{knowledge_base}\n\nTrả lời câu hỏi dựa vào quy định trên: {question}"
            response = self.client.models.generate_content(
                model='models/gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            return f"Lỗi gọi Gemini API: {str(e)}"