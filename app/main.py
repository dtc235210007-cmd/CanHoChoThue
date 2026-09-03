import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

class ReminderRequest(BaseModel):
    tenant_name: str
    apartment: str
    amount: str
    due_date: str
    template_type: str = "1"  # Mặc định là Mẫu 1

@app.post("/api/v1/ai/generate-reminder")
async def generate_reminder(req: ReminderRequest):
    try:
        # MẪU 1: Lịch sự & Chuyên nghiệp (Gửi đầu tháng/Đúng hạn)
        if req.template_type == "1":
            message = (
                f"Kính gửi anh/chị {req.tenant_name},\n\n"
                f"Ban quản lý căn hộ xin thông báo tiền thuê nhà phòng {req.apartment} tháng này là {req.amount} VNĐ.\n"
                f"Hạn thanh toán: Ngày {req.due_date}.\n\n"
                f"Anh/chị vui lòng thanh toán đúng hạn qua chuyển khoản ngân hàng hoặc nộp trực tiếp.\n"
                f"Xin cảm ơn anh/chị!"
            )
        # MẪU 2: Nhắc nhở Thân thiện (Gửi khi sắp tới hạn)
        elif req.template_type == "2":
            message = (
                f"Chào anh/chị {req.tenant_name} (phòng {req.apartment}),\n\n"
                f"BQL nhắc nhẹ anh/chị tiền nhà tháng này là {req.amount} VNĐ, hạn đóng đến ngày {req.due_date} nha.\n"
                f"Anh/chị sắp xếp thanh toán sớm giúp bên em nhé. Chúc anh/chị một tuần làm việc hiệu quả!"
            )
        # MẪU 3: Quyết liệt (Nhắc nợ quá hạn)
        else:
            message = (
                f"[THÔNG BÁO QUÁ HẠN] - Phòng {req.apartment}\n\n"
                f"Gửi anh/chị {req.tenant_name},\n"
                f"Tiền nhà tháng này ({req.amount} VNĐ) đã quá hạn thanh toán ngày {req.due_date}.\n"
                f"Đề nghị anh/chị hoàn tất thanh toán trong hôm nay để không làm ảnh hưởng đến hợp đồng thuê nhà."
            )

        return {"status": "success", "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory="static", html=True), name="static")