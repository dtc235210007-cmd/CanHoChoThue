"""Main FastAPI application for ICTU Tower AI Management System.

Provides REST endpoints for AI operations: payment reminders,
contract summarization, and building regulation Q&A.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.ai_service import AIService

app = FastAPI(
    title="ICTU Tower - Enterprise AI Apartment Management",
    description="Hệ thống quản trị căn hộ thông minh tích hợp Google Gemini AI",
    version="2.0.0",
)

ai_service = AIService()


# ==========================================
# PYDANTIC SCHEMAS (CHUẨN DỮ LIỆU ĐẦU VÀO/RA)
# ==========================================
class ReminderRequest(BaseModel):
    """Schema for payment reminder request."""

    tenant_name: str = Field(..., description="Họ tên người thuê")
    apartment: str = Field(..., description="Mã số căn hộ")
    amount: str = Field(..., description="Số tiền cần thanh toán")
    due_date: str = Field(..., description="Hạn chót thanh toán")
    tone: str = Field(
        default="lich_su",
        description="Phong cách: lich_su | than_thien | quyet_liet",
    )


class ContractRequest(BaseModel):
    """Schema for contract summarization request."""

    contract_text: str = Field(..., description="Toàn văn hợp đồng thuê nhà")


class QuestionRequest(BaseModel):
    """Schema for building regulations inquiry."""

    question: str = Field(..., description="Câu hỏi của cư dân hoặc quản lý")


class StandardAIResponse(BaseModel):
    """Standardized response schema for AI actions."""

    status: str
    data: str


# ==========================================
# CÁC ENDPOINT REST API DÀNH CHO AI
# ==========================================
@app.post(
    "/api/v1/ai/generate-reminder",
    response_model=StandardAIResponse,
    status_code=status.HTTP_200_OK,
)
async def api_generate_reminder(req: ReminderRequest) -> StandardAIResponse:
    """Soạn tin nhắn nhắc nợ thông minh qua Gemini AI."""
    try:
        content = ai_service.generate_payment_reminder(
            tenant_name=req.tenant_name,
            apartment=req.apartment,
            amount=req.amount,
            due_date=req.due_date,
            tone=req.tone,
        )
        return StandardAIResponse(status="success", data=content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi AI: {str(exc)}",
        ) from exc


@app.post(
    "/api/v1/ai/summarize-contract",
    response_model=StandardAIResponse,
    status_code=status.HTTP_200_OK,
)
async def api_summarize_contract(req: ContractRequest) -> StandardAIResponse:
    """Tóm tắt và bóc tách các điều khoản quan trọng trong hợp đồng."""
    try:
        summary = ai_service.summarize_contract(req.contract_text)
        return StandardAIResponse(status="success", data=summary)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi phân tích hợp đồng: {str(exc)}",
        ) from exc


@app.post(
    "/api/v1/ai/ask-regulation",
    response_model=StandardAIResponse,
    status_code=status.HTTP_200_OK,
)
async def api_ask_regulation(req: QuestionRequest) -> StandardAIResponse:
    """Chatbot giải đáp nội quy tòa nhà 24/7 theo cơ sở dữ liệu tri thức."""
    try:
        answer = ai_service.answer_regulation(req.question)
        return StandardAIResponse(status="success", data=answer)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi chatbot: {str(exc)}",
        ) from exc


# ==========================================
# MOUNT THƯ MỤC TĨNH GIAO DIỆN WEB
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")