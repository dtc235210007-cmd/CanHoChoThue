"""FastAPI app cho hệ thống quản lý căn hộ ICTU Tower.
Tích hợp Google Gemini AI và Cơ sở dữ liệu PostgreSQL (qua pgAdmin).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.ai_service import ROLE_PROFILES, AIService

# Database & Models
try:
    from app.database import engine, SessionLocal
    from app.seed_data import init_and_seed_db
    from app.models import (
        RoomModel,
        TenantModel,
        ContractModel,
        MaintenanceModel,
        ServiceModel,
        VehicleModel,
        CashflowModel,
        AuditLogModel,
    )
    DB_AVAILABLE = True
except Exception as e:
    print(f"[Database Warning] Không thể import module database: {e}")
    DB_AVAILABLE = False


app = FastAPI(
    title="ICTU Tower - Enterprise AI Apartment Management",
    description="Hệ thống quản trị căn hộ thông minh tích hợp Google Gemini AI & PostgreSQL",
    version="3.5.0",
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


@app.on_event("startup")
def on_startup():
    """Tự động kiểm tra và khởi tạo bảng PostgreSQL khi server chạy."""
    if DB_AVAILABLE:
        print("[Startup] Đang kết nối PostgreSQL và khởi tạo dữ liệu...")
        init_and_seed_db()


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


class SyncPayload(BaseModel):
    rooms: Optional[List[Dict[str, Any]]] = None
    tenants: Optional[List[Dict[str, Any]]] = None
    contracts: Optional[List[Dict[str, Any]]] = None
    maint: Optional[List[Dict[str, Any]]] = None
    services: Optional[List[Dict[str, Any]]] = None
    vehicles: Optional[List[Dict[str, Any]]] = None
    cashflow: Optional[List[Dict[str, Any]]] = None
    audit_logs: Optional[List[Dict[str, Any]]] = None


# ==========================================
# DATABASE & DATA API ENDPOINTS
# ==========================================
@app.get("/api/v1/db/status")
def api_db_status():
    """Kiểm tra trạng thái kết nối PostgreSQL và số lượng bản ghi từng bảng."""
    if not DB_AVAILABLE or engine is None or SessionLocal is None:
        return {"connected": False, "reason": "Chưa cài đặt SQLAlchemy/psycopg2 hoặc cấu hình DB lỗi."}
    
    try:
        db = SessionLocal()
        counts = {
            "rooms": db.query(RoomModel).count(),
            "tenants": db.query(TenantModel).count(),
            "contracts": db.query(ContractModel).count(),
            "maintenance": db.query(MaintenanceModel).count(),
            "services": db.query(ServiceModel).count(),
            "vehicles": db.query(VehicleModel).count(),
            "cashflow": db.query(CashflowModel).count(),
            "audit_logs": db.query(AuditLogModel).count(),
        }
        db.close()
        return {"connected": True, "database": "PostgreSQL (ictu_tower)", "counts": counts}
    except Exception as e:
        return {"connected": False, "reason": str(e)}


@app.get("/api/v1/data/all")
def api_get_all_data():
    """Lấy toàn bộ dữ liệu 8 bảng từ PostgreSQL để hiển thị lên frontend."""
    if not DB_AVAILABLE or SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database chưa khả dụng")

    db = SessionLocal()
    try:
        return {
            "rooms": [r.to_dict() for r in db.query(RoomModel).all()],
            "tenants": [t.to_dict() for t in db.query(TenantModel).all()],
            "contracts": [c.to_dict() for c in db.query(ContractModel).all()],
            "maint": [m.to_dict() for m in db.query(MaintenanceModel).all()],
            "services": [s.to_dict() for s in db.query(ServiceModel).all()],
            "vehicles": [v.to_dict() for v in db.query(VehicleModel).all()],
            "cashflow": [cf.to_dict() for cf in db.query(CashflowModel).all()],
            "audit_logs": [al.to_dict() for al in db.query(AuditLogModel).order_by(AuditLogModel.id.desc()).all()],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/api/v1/data/sync")
def api_sync_data(payload: SyncPayload):
    """Đồng bộ dữ liệu từ giao diện vào PostgreSQL."""
    if not DB_AVAILABLE or SessionLocal is None:
        return {"ok": False, "reason": "Database chưa khả dụng"}

    db = SessionLocal()
    try:
        # Cập nhật Rooms
        if payload.rooms is not None:
            db.query(RoomModel).delete()
            for r in payload.rooms:
                db.add(RoomModel(
                    room=r.get("room"),
                    model_type=r.get("modelType") or r.get("model_type", ""),
                    tenant=r.get("tenant", "(Chưa có khách)"),
                    price=str(r.get("price", "0")),
                    area=float(r.get("area", 0)),
                    date=str(r.get("date", "--")),
                    status=str(r.get("status", "empty")),
                    image=r.get("image", ""),
                ))

        # Cập nhật Tenants
        if payload.tenants is not None:
            db.query(TenantModel).delete()
            for t in payload.tenants:
                db.add(TenantModel(
                    id=t.get("id"),
                    name=t.get("name", ""),
                    phone=t.get("phone", ""),
                    email=t.get("email", ""),
                    id_card=t.get("idCard") or t.get("id_card", ""),
                    room=t.get("room", ""),
                ))

        # Cập nhật Contracts
        if payload.contracts is not None:
            db.query(ContractModel).delete()
            for c in payload.contracts:
                db.add(ContractModel(
                    id=c.get("id"),
                    room=c.get("room", ""),
                    tenant=c.get("tenant", ""),
                    start=str(c.get("start", "")),
                    end=str(c.get("end", "")),
                    deposit=str(c.get("deposit", "0")),
                    status=str(c.get("status", "Hiệu lực")),
                ))

        # Cập nhật Maintenance
        if payload.maint is not None:
            db.query(MaintenanceModel).delete()
            for m in payload.maint:
                db.add(MaintenanceModel(
                    id=m.get("id"),
                    room=m.get("room", ""),
                    desc=m.get("desc", ""),
                    date=str(m.get("date", "")),
                    priority=str(m.get("priority", "Bình thường")),
                    status=str(m.get("status", "Chờ xử lý")),
                ))

        # Cập nhật Services
        if payload.services is not None:
            db.query(ServiceModel).delete()
            for s in payload.services:
                db.add(ServiceModel(
                    room=s.get("room", ""),
                    tenant=s.get("tenant", ""),
                    old_elec=float(s.get("oldElec", 0)),
                    new_elec=float(s.get("newElec", 0)),
                    old_water=float(s.get("oldWater", 0)),
                    new_water=float(s.get("newWater", 0)),
                    bikes=int(s.get("bikes", 0)),
                    cars=int(s.get("cars", 0)),
                    manage_fee=float(s.get("manageFee", 0)),
                    trash_fee=float(s.get("trashFee", 0)),
                ))

        # Cập nhật Vehicles
        if payload.vehicles is not None:
            db.query(VehicleModel).delete()
            for v in payload.vehicles:
                db.add(VehicleModel(
                    card_id=v.get("cardId") or v.get("card_id", ""),
                    room=v.get("room", ""),
                    resident=v.get("resident", ""),
                    card_type=v.get("cardType") or v.get("card_type", ""),
                    vehicle_type=v.get("vehicleType") or v.get("vehicle_type", ""),
                    plate=v.get("plate", ""),
                    brand=v.get("brand", ""),
                    issue_date=str(v.get("issueDate") or v.get("issue_date", "")),
                    status=str(v.get("status", "active")),
                ))

        # Cập nhật Cashflow
        if payload.cashflow is not None:
            db.query(CashflowModel).delete()
            for cf in payload.cashflow:
                db.add(CashflowModel(
                    id=cf.get("id"),
                    date=str(cf.get("date", "")),
                    type=cf.get("type", "income"),
                    category=cf.get("category", ""),
                    partner=cf.get("partner", ""),
                    amount=float(cf.get("amount", 0)),
                    actor=cf.get("actor", "Kế Toán"),
                ))

        # Cập nhật Audit Logs
        if payload.audit_logs is not None:
            db.query(AuditLogModel).delete()
            for al in payload.audit_logs:
                db.add(AuditLogModel(
                    time=str(al.get("time", "")),
                    user=al.get("user", "Hệ thống"),
                    action=al.get("action", ""),
                    detail=al.get("detail", ""),
                ))

        db.commit()
        return {"ok": True, "message": "Đã lưu vào PostgreSQL thành công"}
    except Exception as e:
        db.rollback()
        return {"ok": False, "reason": str(e)}
    finally:
        db.close()


@app.post("/api/v1/db/reseed")
def api_db_reseed():
    """Nạp lại dữ liệu mẫu gốc từ đầu."""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database chưa cấu hình")
    success = init_and_seed_db()
    return {"ok": success}


# ==========================================
# AI ENDPOINTS
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
# STATIC FILES
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")