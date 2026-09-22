"""FastAPI app cho hệ thống quản lý căn hộ ICTU Tower (bản sửa AI).

Thay đổi so với bản cũ:
- Mọi endpoint AI đều nhận thêm `role` (admin | accountant | staff).
- Trả về source ("gemini" / "offline" / "validation") để giao diện báo trung thực.
- Thêm /api/v1/ai/health để kiểm tra API key ngay trên trình duyệt.
- Thêm /api/v1/ai/chat có ngữ cảnh dữ liệu thật của tòa nhà.
- Bật CORS để mở index.html bằng Live Server vẫn gọi được API.
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.ai_service import ROLE_PROFILES, AIService

app = FastAPI(
    title="ICTU Tower - Enterprise AI Apartment Management",
    description="Hệ thống quản trị căn hộ thông minh tích hợp Google Gemini AI",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_service = AIService()

VALID_ROLES = set(ROLE_PROFILES.keys())


def normalize_role(role: Optional[str]) -> str:
    """Chuẩn hóa role gửi từ giao diện về 3 giá trị hợp lệ."""
    r = (role or "").strip().lower()
    alias = {
        "ketoan": "accountant", "ke_toan": "accountant", "kt": "accountant",
        "nhanvien": "staff", "nhan_vien": "staff", "ky_thuat": "staff",
        "quantri": "admin", "quan_tri": "admin",
    }
    r = alias.get(r, r)
    return r if r in VALID_ROLES else "admin"


# ==========================================
# SCHEMAS
# ==========================================
class NoticeRequest(BaseModel):
    tenant_name: str = Field(..., description="Họ tên người thuê")
    apartment: str = Field(..., description="Mã số căn hộ")
    notice_type: str = Field(default="debt", description="debt | expiring | maintenance | violation")
    amount: str = Field(default="", description="Số tiền cần thanh toán")
    due_date: str = Field(default="", description="Hạn chót / ngày hết hạn")
    tone: str = Field(default="lich_su", description="lich_su | than_thien | quyet_liet")
    role: str = Field(default="accountant", description="admin | accountant | staff")
    extra: str = Field(default="", description="Ghi chú thêm đưa vào thông báo")


class ContractRequest(BaseModel):
    contract_text: str = Field(..., description="Toàn văn hợp đồng thuê nhà")
    role: str = Field(default="admin", description="admin | accountant | staff")


class QuestionRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi của cán bộ")
    role: str = Field(default="admin", description="admin | accountant | staff")
    context: str = Field(default="", description="Dữ liệu thời gian thực gửi kèm từ giao diện")


class AIResponse(BaseModel):
    ok: bool
    source: str           # gemini | offline | validation
    role: str
    data: str
    error: Optional[str] = None


# ==========================================
# ENDPOINTS
# ==========================================
@app.get("/api/v1/ai/health")
async def api_health() -> dict:
    """Kiểm tra API key và thử gọi Gemini một lần."""
    status_info = ai_service.key_status()
    if not status_info["ok"]:
        return {"connected": False, "reason": status_info["reason"]}
    text, err = ai_service._call_gemini("Trả lời đúng một từ: OK", "Bạn là bộ kiểm tra kết nối.")
    return {
        "connected": bool(text),
        "reason": err or "Kết nối Gemini thành công",
        "sample": (text or "")[:80],
    }


@app.post("/api/v1/ai/summarize-contract", response_model=AIResponse,
          status_code=status.HTTP_200_OK)
async def api_summarize_contract(req: ContractRequest) -> AIResponse:
    """Tóm tắt & bóc tách hợp đồng theo góc nhìn từng actor."""
    result = ai_service.summarize_contract(req.contract_text, normalize_role(req.role))
    return AIResponse(**result)


@app.post("/api/v1/ai/generate-notice", response_model=AIResponse,
          status_code=status.HTTP_200_OK)
async def api_generate_notice(req: NoticeRequest) -> AIResponse:
    """Sinh thông báo gửi khách hàng (thu tiền, hết hạn HĐ, bảo trì, vi phạm)."""
    result = ai_service.generate_notice(
        tenant_name=req.tenant_name,
        apartment=req.apartment,
        notice_type=req.notice_type,
        amount=req.amount,
        due_date=req.due_date,
        tone=req.tone,
        role=normalize_role(req.role),
        extra=req.extra,
    )
    return AIResponse(**result)


# Giữ đường dẫn cũ để code cũ không vỡ
@app.post("/api/v1/ai/generate-reminder", response_model=AIResponse)
async def api_generate_reminder(req: NoticeRequest) -> AIResponse:
    return await api_generate_notice(req)


@app.post("/api/v1/ai/chat", response_model=AIResponse, status_code=status.HTTP_200_OK)
async def api_chat(req: QuestionRequest) -> AIResponse:
    """Chatbot có ngữ cảnh dữ liệu thật của tòa nhà."""
    result = ai_service.answer_question(req.question, normalize_role(req.role), req.context)
    return AIResponse(**result)


@app.post("/api/v1/ai/ask-regulation", response_model=AIResponse)
async def api_ask_regulation(req: QuestionRequest) -> AIResponse:
    return await api_chat(req)


# ==========================================
# STATIC
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")