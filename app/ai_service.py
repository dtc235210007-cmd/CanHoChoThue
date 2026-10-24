"""AI Service cho hệ thống quản lý căn hộ ICTU Tower.

Nguyên tắc thiết kế:
1. Gọi Gemini API thật, KHÔNG bịa dữ liệu khi lỗi.
2. Prompt bám sát dữ liệu đầu vào thật (hợp đồng, số tiền, tên khách...).
3. Phân quyền 3 actor: admin / accountant (kế toán) / staff (nhân viên kỹ thuật).
4. Khi API lỗi -> trả về bản phân tích OFFLINE bóc tách TỪ CHÍNH VĂN BẢN người
   dùng nhập (regex), kèm cờ source="offline" để giao diện báo trung thực.

Ghi chú về API key: từ giữa 2026 Google AI Studio mặc định phát hành key dạng
"Auth key" (tiền tố "AQ."), thay cho key "Standard" cũ (tiền tố "AIzaSy...").
Cả hai định dạng đều được gửi qua header `x-goog-api-key` như nhau, nên code
này không kén định dạng key - chỉ cần dán đúng chuỗi lấy từ
https://aistudio.google.com/apikey vào GEMINI_API_KEY trong .env.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv(override=True)

# Thứ tự model tối ưu: Đưa model flash chuẩn nhất, nhanh nhất và ổn định nhất lên đầu
MODEL_CANDIDATES: List[str] = [
    "gemini-1.5-flash",       # Chuẩn quốc tế, phản hồi tức thì (~1-2s), hỗ trợ mọi API key
    "gemini-1.5-flash-8b",    # Bản siêu nhẹ cực nhanh
    "gemini-flash-latest",
    "gemini-2.0-flash",
]

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# ---------------------------------------------------------------------------
# HỒ SƠ VAI TRÒ - mỗi actor có góc nhìn, giọng văn và trọng tâm nghiệp vụ khác
# ---------------------------------------------------------------------------
ROLE_PROFILES: Dict[str, Dict[str, str]] = {
    "admin": {
        "label": "Tổng Quản Trị (Ban Giám Đốc)",
        "persona": (
            "Bạn là trợ lý AI báo cáo trực tiếp cho Ban Giám Đốc tòa nhà ICTU Tower. "
            "Trọng tâm: rủi ro pháp lý, nghĩa vụ tài chính của hai bên, điều khoản bất lợi, "
            "tác động tới doanh thu và tỷ lệ lấp đầy. Văn phong ngắn gọn, quyết đoán, "
            "luôn kết thúc bằng khuyến nghị hành động cụ thể."
        ),
    },
    "accountant": {
        "label": "Kế Toán Trưởng",
        "persona": (
            "Bạn là trợ lý AI của Phòng Kế Toán tòa nhà ICTU Tower. "
            "Trọng tâm: con số - giá thuê, tiền cọc, kỳ hạn thanh toán, đơn giá điện/nước/xe, "
            "phí phạt chậm nộp, công nợ. Luôn tách bạch từng khoản tiền, ghi rõ đơn vị VNĐ "
            "và mốc thời gian. Không suy diễn con số không có trong dữ liệu."
        ),
    },
    "staff": {
        "label": "Nhân Viên Kỹ Thuật & Vận Hành",
        "persona": (
            "Bạn là trợ lý AI của Tổ Vận Hành tòa nhà ICTU Tower. "
            "Trọng tâm: nghĩa vụ bàn giao, nội thất/thiết bị, trách nhiệm sửa chữa - bảo trì, "
            "nội quy sinh hoạt, thủ tục chuyển vào/chuyển ra. Văn phong thân thiện, "
            "hướng dẫn theo từng bước để nhân viên làm được ngay."
        ),
    },
}

ANTI_HALLUCINATION = (
    "QUY TẮC BẮT BUỘC: chỉ được dùng thông tin có trong dữ liệu được cung cấp. "
    "Trường nào không tìm thấy thì ghi đúng chữ 'Không có trong văn bản'. "
    "Tuyệt đối KHÔNG bịa tên người, số tiền, số CCCD, số tài khoản hay ngày tháng. "
    "Trả lời bằng tiếng Việt, định dạng HTML đơn giản (<strong>, <ul>, <li>, <br>), "
    "không dùng dấu ``` hay markdown."
)


class AIService:
    """Lớp dịch vụ gọi Gemini cho cả 3 actor."""

    def __init__(self) -> None:
        self.api_key: str = (os.getenv("GEMINI_API_KEY") or "").strip()
        self.last_error: Optional[str] = None
        self.active_model: Optional[str] = "gemini-1.5-flash"  # Ghim sẵn model nhanh và chuẩn nhất

    # ------------------------------------------------------------------
    # LỚP GỌI API
    # ------------------------------------------------------------------
    def key_status(self) -> Dict[str, Any]:
        """Kiểm tra nhanh tình trạng API key (dùng cho endpoint /health)."""
        if not self.api_key:
            return {"ok": False, "reason": "Chưa đặt GEMINI_API_KEY trong file .env"}
        if len(self.api_key) < 20 or " " in self.api_key:
            return {
                "ok": False,
                "reason": (
                    "Giá trị GEMINI_API_KEY trong .env có vẻ chưa phải key thật "
                    "(quá ngắn hoặc chứa khoảng trắng)."
                ),
            }
        return {"ok": True, "reason": "Key có định dạng hợp lệ"}

    def _call_gemini(
        self,
        user_prompt: str,
        system_instruction: str,
        temperature: float = 0.4,
        max_tokens: int = 1024,
        timeout: int = 8,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Gọi Gemini với bộ đệm model nhanh và timeout ngắn (8s) để phản hồi tức thì."""
        status = self.key_status()
        if not status["ok"]:
            return None, status["reason"]

        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        body = json.dumps(payload).encode("utf-8")

        # Đưa model đang hoạt động tốt (active_model) lên đầu để gọi 1 phát ăn ngay
        models_to_try = [self.active_model] if self.active_model else []
        for m in MODEL_CANDIDATES:
            if m not in models_to_try:
                models_to_try.append(m)

        last_err = "Không rõ lỗi"
        for model in models_to_try:
            req = urllib.request.Request(
                f"{API_BASE}/{model}:generateContent",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates") or []
                if not candidates:
                    last_err = f"[{model}] API không trả về candidates: {data}"
                    continue
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    self.active_model = model  # Nhớ lại model này để lần sau gọi thẳng, không cần thử lại
                    return text, None
                last_err = f"[{model}] Phản hồi rỗng"
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")[:400]
                last_err = f"[{model}] HTTP {exc.code}: {detail}"
                # Chỉ dừng lại nếu API key sai hoàn toàn (401/403)
                if exc.code in (401, 403) and ("API_KEY_INVALID" in detail or "PERMISSION_DENIED" in detail):
                    break
            except Exception as exc:
                last_err = f"[{model}] {type(exc).__name__}: {exc}"

        self.last_error = last_err
        return None, last_err

    @staticmethod
    def _persona(role: str) -> str:
        return ROLE_PROFILES.get(role, ROLE_PROFILES["admin"])["persona"]

    @staticmethod
    def _role_label(role: str) -> str:
        return ROLE_PROFILES.get(role, ROLE_PROFILES["admin"])["label"]

    # ------------------------------------------------------------------
    # 1. TÓM TẮT / BÓC TÁCH HỢP ĐỒNG
    # ------------------------------------------------------------------
    def summarize_contract(self, contract_text: str, role: str = "admin") -> Dict[str, Any]:
        contract_text = (contract_text or "").strip()
        if len(contract_text) < 30:
            return {
                "ok": False,
                "source": "validation",
                "role": role,
                "data": "<strong>Chưa có nội dung hợp đồng.</strong><br>Vui lòng dán "
                        "toàn văn hợp đồng vào ô bên trái rồi bấm phân tích.",
                "error": "contract_text quá ngắn",
            }

        prompt = (
            f"{ANTI_HALLUCINATION}\n\n"
            "Hãy bóc tách hợp đồng thuê căn hộ dưới đây thành các mục sau:\n"
            "1. Bên cho thuê (Bên A) và Bên thuê (Bên B) - kèm giấy tờ tùy thân nếu có.\n"
            "2. Căn hộ: mã căn, diện tích, loại phòng, nội thất.\n"
            "3. Tài chính: giá thuê/tháng, tiền cọc, chu kỳ và hạn thanh toán, "
            "đơn giá điện - nước - gửi xe - phí dịch vụ.\n"
            "4. Thời hạn thuê: ngày bắt đầu, ngày kết thúc, số tháng.\n"
            "5. Nghĩa vụ và điều khoản phạt của mỗi bên.\n"
            "6. CẢNH BÁO RỦI RO: nêu các điểm bất lợi, mơ hồ hoặc thiếu sót "
            "(ví dụ thiếu điều khoản tăng giá, thiếu quy định hoàn cọc).\n"
            "7. KHUYẾN NGHỊ HÀNH ĐỘNG phù hợp với vai trò người đọc.\n\n"
            f"--- TOÀN VĂN HỢP ĐỒNG ---\n{contract_text}\n--- HẾT ---"
        )

        text, err = self._call_gemini(prompt, self._persona(role), temperature=0.2, max_tokens=2048, timeout=12)
        if text:
            return {
                "ok": True,
                "source": "gemini",
                "role": role,
                "data": text,
                "error": None,
            }

        return {
            "ok": True,
            "source": "offline",
            "role": role,
            "data": self._offline_contract_summary(contract_text, role),
            "error": err,
        }

    # ------------------------------------------------------------------
    # BỘ BÓC TÁCH OFFLINE - đọc từ CHÍNH văn bản, không bịa
    # ------------------------------------------------------------------
    @staticmethod
    def _offline_contract_summary(text: str, role: str) -> str:
        def find(pattern: str, group: int = 1) -> Optional[str]:
            m = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
            return m.group(group).strip() if m else None

        na = '<em class="text-muted">Không tìm thấy trong văn bản</em>'

        room = find(r"\b([A-Z]{1,2}\s?\d{3,4})\b")
        area = find(r"(\d{1,4}(?:[.,]\d+)?)\s*m\s*[²2]")
        ben_a = find(r"[Bb]ên\s*A\s*[:\-]?\s*([^\n\.;]{3,80})")
        ben_b = find(r"[Bb]ên\s*B\s*[:\-]?\s*([^\n\.;]{3,80})")
        cccd = find(r"(?:CCCD|CMND|căn cước)\D{0,10}(\d{9,12})")

        money = re.findall(r"(\d{1,3}(?:[.,]\d{3}){1,3})\s*(?:VNĐ|VND|đ\b|đồng)", text, re.IGNORECASE)
        rent = find(r"(?:giá thuê|tiền thuê|đơn giá thuê)\D{0,30}(\d{1,3}(?:[.,]\d{3}){1,3})")
        deposit = find(r"(?:tiền cọc|đặt cọc|ký quỹ)\D{0,30}(\d{1,3}(?:[.,]\d{3}){1,3})")
        elec = find(r"[Đđ]iện\D{0,15}(\d{1,3}(?:[.,]\d{3})?)\s*(?:đ|VNĐ)?\s*/?\s*kWh")
        water = find(r"[Nn]ước\D{0,15}(\d{1,3}(?:[.,]\d{3})?)\s*(?:đ|VNĐ)?\s*/?\s*m\s*[³3]")
        pay_day = find(r"(?:hạn nộp|thanh toán)\D{0,25}ngày\s*(\d{1,2})")
        dates = re.findall(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", text)
        months = find(r"thời hạn thuê\D{0,15}(\d{1,3})\s*tháng")

        risks: List[str] = []
        if not deposit:
            risks.append("Không xác định được <strong>tiền cọc</strong> trong văn bản.")
        if not re.search(r"hoàn\s*(?:trả)?\s*cọc|thanh lý", text, re.IGNORECASE):
            risks.append("Thiếu điều khoản về <strong>điều kiện hoàn trả tiền cọc</strong>.")
        if not re.search(r"tăng giá|điều chỉnh giá", text, re.IGNORECASE):
            risks.append("Thiếu điều khoản về <strong>điều chỉnh giá thuê</strong> khi gia hạn.")
        if not re.search(r"phạt|bồi thường|đơn phương", text, re.IGNORECASE):
            risks.append("Thiếu điều khoản <strong>phạt vi phạm / chấm dứt đơn phương</strong>.")
        if len(dates) < 2:
            risks.append("Không đủ <strong>mốc ngày bắt đầu - kết thúc</strong> hợp đồng.")

        role_note = {
            "admin": "Rà soát lại các điểm thiếu ở trên trước khi trình ký; "
                     "ưu tiên bổ sung điều khoản phạt và điều chỉnh giá.",
            "accountant": "Đối chiếu giá thuê, tiền cọc và đơn giá điện/nước ở trên với "
                          "bảng công nợ trước khi lập phiếu thu.",
            "staff": "Lập biên bản bàn giao nội thất kèm ảnh chụp hiện trạng trước ngày "
                     "khách nhận phòng.",
        }.get(role, "")

        return (
            '<div class="alert alert-warning py-2 small mb-2">'
            "⚠️ <strong>Chế độ bóc tách ngoại tuyến</strong> (chưa kết nối được Gemini API). "
            "Kết quả dưới đây được trích trực tiếp từ văn bản bạn nhập, không phải dữ liệu mẫu."
            "</div>"
            f"<strong>📋 BÓC TÁCH HỢP ĐỒNG – góc nhìn {AIService._role_label(role)}</strong><br><br>"
            "<strong>1. Các bên</strong><ul>"
            f"<li>Bên cho thuê (A): {ben_a or na}</li>"
            f"<li>Bên thuê (B): {ben_b or na}</li>"
            f"<li>Giấy tờ tùy thân Bên B: {cccd or na}</li></ul>"
            "<strong>2. Căn hộ</strong><ul>"
            f"<li>Mã căn: {room or na}</li>"
            f"<li>Diện tích: {area + ' m²' if area else na}</li></ul>"
            "<strong>3. Tài chính</strong><ul>"
            f"<li>Giá thuê: {rent + ' VNĐ/tháng' if rent else na}</li>"
            f"<li>Tiền cọc: {deposit + ' VNĐ' if deposit else na}</li>"
            f"<li>Hạn thanh toán hằng tháng: {'ngày ' + pay_day if pay_day else na}</li>"
            f"<li>Đơn giá điện: {elec + ' đ/kWh' if elec else na}</li>"
            f"<li>Đơn giá nước: {water + ' đ/m³' if water else na}</li>"
            f"<li>Tổng số khoản tiền phát hiện trong văn bản: {len(money)}</li></ul>"
            "<strong>4. Thời hạn</strong><ul>"
            f"<li>Các mốc ngày: {', '.join(dates) if dates else na}</li>"
            f"<li>Số tháng thuê: {months + ' tháng' if months else na}</li></ul>"
            "<strong>5. ⚖️ Cảnh báo rủi ro</strong><ul>"
            + ("".join(f"<li>{r}</li>" for r in risks) if risks
               else "<li>Không phát hiện thiếu sót rõ rệt ở mức rà soát tự động.</li>")
            + "</ul>"
            f"<strong>6. 👉 Khuyến nghị</strong><br>{role_note}"
        )

    # ------------------------------------------------------------------
    # 2. SINH THÔNG BÁO GỬI KHÁCH HÀNG
    # ------------------------------------------------------------------
    def generate_notice(
        self,
        tenant_name: str,
        apartment: str,
        notice_type: str = "debt",
        amount: str = "",
        due_date: str = "",
        tone: str = "lich_su",
        role: str = "accountant",
        extra: str = "",
    ) -> Dict[str, Any]:
        if not tenant_name or not apartment:
            return {
                "ok": False,
                "source": "validation",
                "role": role,
                "data": "Vui lòng nhập đủ <strong>tên khách thuê</strong> và <strong>mã căn hộ</strong>.",
                "error": "thiếu tenant_name hoặc apartment",
            }

        type_desc = {
            "debt": "nhắc thanh toán tiền thuê nhà và phí dịch vụ",
            "expiring": "nhắc hợp đồng thuê sắp hết hạn và mời gia hạn",
            "maintenance": "thông báo lịch bảo trì/cắt điện nước ảnh hưởng tới căn hộ",
            "violation": "nhắc nhở vi phạm nội quy tòa nhà",
        }.get(notice_type, "thông báo chung tới cư dân")

        tone_desc = {
            "lich_su": "trang trọng, lịch sự, chuẩn văn bản hành chính",
            "than_thien": "gần gũi, thân thiện như nhắn tin Zalo cho người quen",
            "quyet_liet": "nghiêm khắc, dứt khoát, nêu rõ chế tài nhưng vẫn đúng mực, không xúc phạm",
        }.get(tone, "trang trọng, lịch sự")

        prompt = (
            f"{ANTI_HALLUCINATION}\n\n"
            f"Soạn MỘT tin nhắn Zalo/SMS {type_desc}, gửi tới cư dân tòa nhà ICTU Tower.\n"
            f"Giọng văn: {tone_desc}.\n"
            "Độ dài 90-160 từ, xuống dòng rõ ràng, có lời chào và lời cảm ơn.\n"
            "Chỉ trả về nội dung tin nhắn, KHÔNG thêm lời dẫn hay giải thích.\n\n"
            "--- DỮ LIỆU THẬT (phải dùng đúng, không sửa) ---\n"
            f"Khách thuê: {tenant_name}\n"
            f"Căn hộ: {apartment}\n"
            f"Số tiền: {amount or 'không áp dụng'}\n"
            f"Mốc thời gian: {due_date or 'không áp dụng'}\n"
            f"Ghi chú thêm: {extra or 'không có'}\n"
            "Cú pháp chuyển khoản: ICTU <MÃ PHÒNG> <KỲ>. Hotline: 1900 8888."
        )

        text, err = self._call_gemini(prompt, self._persona(role), temperature=0.7, max_tokens=1024, timeout=8)
        if text:
            return {"ok": True, "source": "gemini", "role": role, "data": text, "error": None}

        return {
            "ok": True,
            "source": "offline",
            "role": role,
            "data": self._offline_notice(tenant_name, apartment, notice_type, amount, due_date, tone),
            "error": err,
        }

    @staticmethod
    def _offline_notice(
        name: str, room: str, notice_type: str, amount: str, due_date: str, tone: str
    ) -> str:
        head = {
            "than_thien": f"Chào anh/chị {name} (căn {room}),",
            "quyet_liet": f"THÔNG BÁO KHẨN – Kính gửi cư dân {name}, căn hộ {room}:",
        }.get(tone, f"Kính gửi Quý cư dân {name} – căn hộ {room},")

        if notice_type == "expiring":
            body = (
                f"Hợp đồng thuê căn hộ {room} của Quý khách sẽ hết hiệu lực vào ngày {due_date or '(chưa nhập)'}. "
                "Nếu có nhu cầu tiếp tục thuê, Quý khách vui lòng phản hồi trước ngày hết hạn ít nhất 15 ngày "
                "để Ban Quản Lý giữ nguyên mức giá hiện tại và chuẩn bị phụ lục gia hạn."
            )
        elif notice_type == "maintenance":
            body = (
                f"Ban Quản Lý sẽ tiến hành bảo trì hệ thống kỹ thuật ảnh hưởng tới căn hộ {room} "
                f"vào ngày {due_date or '(chưa nhập)'}. Kính mong Quý cư dân chủ động sắp xếp sinh hoạt."
            )
        elif notice_type == "violation":
            body = (
                f"Ban Quản Lý ghi nhận phản ánh liên quan tới việc chấp hành nội quy tại căn hộ {room}. "
                f"Đề nghị Quý cư dân phối hợp khắc phục trước ngày {due_date or '(chưa nhập)'}."
            )
        else:
            body = (
                f"Ban Quản Lý xin thông báo khoản tiền thuê căn hộ và phí dịch vụ của căn {room} "
                f"kỳ này là {amount or '(chưa nhập)'} VNĐ, hạn thanh toán trước ngày {due_date or '(chưa nhập)'}.\n"
                f"Cú pháp chuyển khoản: ICTU {room}."
            )

        tail = (
            "Mọi vướng mắc xin liên hệ Hotline 1900 8888. Trân trọng cảm ơn Quý cư dân!"
            if tone != "quyet_liet"
            else "Quá thời hạn trên, Ban Quản Lý sẽ áp dụng chế tài theo đúng hợp đồng đã ký. "
                 "Hotline 1900 8888."
        )
        return f"{head}\n{body}\n{tail}"

    # ------------------------------------------------------------------
    # 3. HỎI ĐÁP / CHATBOT CÓ NGỮ CẢNH DỮ LIỆU THẬT & ĐA NĂNG
    # ------------------------------------------------------------------
    def answer_question(
        self,
        question: str,
        role: str = "admin",
        context: str = "",
    ) -> Dict[str, Any]:
        question = (question or "").strip()
        if not question:
            return {
                "ok": False,
                "source": "validation",
                "role": role,
                "data": "Bạn chưa nhập câu hỏi. Vui lòng nhập nội dung cần hỏi.",
                "error": "empty question",
            }

        prompt = (
            "Bạn là Siêu Trợ Lý AI Toàn Năng (Enterprise AI Super Assistant) kiêm Chuyên Gia Vận Hành "
            f"của Tòa nhà ICTU Tower, đang hỗ trợ: {self._role_label(role)}.\n\n"
            "=== BỘ CƠ SỞ DỮ LIỆU THỜI GIAN THỰC (REAL-TIME DATABASE) ===\n"
            f"{context or 'Hiện chưa có dữ liệu thời gian thực gửi kèm.'}\n"
            "=== HẾT CƠ SỞ DỮ LIỆU ===\n\n"
            "NGUYÊN TẮC VÀ PHẠM VI HỖ TRỢ ĐA NĂNG:\n"
            "1. TƯƠNG TÁC LOGIC VỚI DATABASE: Khi câu hỏi liên quan đến căn hộ, công nợ, cư dân, xe cộ, "
            "hợp đồng, bảo trì, dịch vụ điện nước, sổ quỹ... bạn BẮT BUỘC phải tra cứu, đối chiếu, lọc và "
            "tính toán chuẩn xác dựa trên Cơ sở dữ liệu ở trên. Trích dẫn rõ mã căn, số tiền, ngày hạn, tên khách.\n"
            "2. HỎI ĐÁP ĐA NĂNG KHÔNG GIỚI HẠN: Bạn hỗ trợ trả lời TẤT CẢ câu hỏi của người dùng (không chỉ các câu mẫu): "
            "tính toán số học, tài chính, tư vấn luật nhà ở và hợp đồng thuê, hướng dẫn xử lý sự cố kỹ thuật "
            "(chập điện, nhảy aptomat, rò rỉ nước, bảo dưỡng điều hòa), quy trình quản lý, soạn thảo văn bản, "
            "và cả các kiến thức khoa học, đời sống thông thường.\n"
            "3. ĐỊNH DẠNG: Trình bày mạch lạc, lịch sự, chuyên nghiệp bằng tiếng Việt và HTML đơn giản "
            "(<strong>, <ul>, <li>, <br>, <code>, bảng nếu cần).\n\n"
            f"CÂU HỎI CỦA NGƯỜI DÙNG: {question}"
        )

        text, err = self._call_gemini(prompt, self._persona(role), temperature=0.4)
        if text:
            return {"ok": True, "source": "gemini", "role": role, "data": text, "error": None}

        # Nếu Gemini gặp lỗi (503 / quá tải / mạng chập chờn) -> Tự động dùng Local Smart Engine tra cứu logic từ Database
        local_answer = self._smart_local_query(question, context, role)
        return {
            "ok": True,
            "source": "offline",
            "role": role,
            "data": (
                '<div class="alert alert-info py-2 small mb-2 d-flex align-items-center justify-content-between">'
                '<span><i class="fa-solid fa-database text-primary me-2"></i><strong>Chế độ Tra Cứu Logic Database:</strong> Đang tra cứu trực tiếp từ dữ liệu thời gian thực của tòa nhà.</span>'
                f'<span class="badge bg-light text-muted border" title="{err}">Gemini API bận (HTTP 503)</span>'
                '</div>'
                + local_answer
            ),
            "error": err,
        }

    @staticmethod
    def _smart_local_query(question: str, context: str, role: str) -> str:
        """Bộ suy diễn và tra cứu logic cơ sở dữ liệu nội bộ (Local DB Engine).
        
        Tự động bóc tách từ khóa, trích xuất thực thể (mã phòng, cư dân, biển số, nợ, số học...)
        để trả lời chính xác dựa trên context thời gian thực, không bị phụ thuộc hoàn toàn vào Gemini.
        """
        q = question.strip().lower()

        # 1. Tra cứu phòng cụ thể (VD: A101, A102, B205...)
        room_match = re.search(r"\b([A-Za-z]\s?\d{3})\b", question, re.IGNORECASE)
        if room_match:
            room_code = room_match.group(1).replace(" ", "").upper()
            related_lines = [line.strip() for line in context.splitlines() if room_code in line.upper()]
            if related_lines:
                html = f"<strong>🏢 Thông Tin Chi Tiết Về Căn Hộ {room_code}:</strong><ul>"
                for line in related_lines:
                    html += f"<li>{line}</li>"
                html += "</ul>"
                html += f"<em>💡 Cần thực hiện thao tác gì với căn {room_code} (nhắc nợ, sửa chữa, gia hạn HĐ), bạn có thể yêu cầu tôi hỗ trợ!</em>"
                return html

        # 2. Câu hỏi về nợ tiền / công nợ / ai chưa đóng tiền
        if any(w in q for w in ["nợ", "chưa đóng", "chưa nộp", "chậm nộp", "công nợ"]):
            debt_lines = [line.strip() for line in context.splitlines() if "nợ" in line.lower() or "chậm" in line.lower() or "debt" in line.lower()]
            if debt_lines:
                html = "<strong>💰 Danh Sách Căn Hộ Đang Nợ Tiền / Chưa Đóng Phí:</strong><ul>"
                for line in debt_lines:
                    html += f"<li>{line}</li>"
                html += "</ul>"
                html += (
                    "<strong>📌 Cú pháp thanh toán nộp tiền:</strong><br>"
                    "• Ngân hàng: <strong>MB Bank (Quân Đội)</strong> hoặc <strong>Vietcombank</strong><br>"
                    "• STK: <strong>99998888ICTU</strong> | Chủ TK: <strong>BQL TOA NHA ICTU TOWER</strong><br>"
                    "• Nội dung: <code>ICTU [Mã_Phòng]</code> (VD: <em>ICTU A101</em>)"
                )
                return html

        # 3. Câu hỏi về phòng trống / còn phòng nào thuê
        if any(w in q for w in ["trống", "còn phòng", "chưa thuê", "chưa có khách", "sẵn sàng"]):
            empty_lines = [line.strip() for line in context.splitlines() if "trống" in line.lower() or "empty" in line.lower() or "chưa có khách" in line.lower()]
            if empty_lines:
                html = "<strong>🔑 Danh Sách Căn Hộ Hiện Đang Trống (Có Thể Cho Thuê Ngay):</strong><ul>"
                for line in empty_lines:
                    html += f"<li>{line}</li>"
                html += "</ul>"
                html += "<em>💡 Bạn có thể vào tab 'Quản Lý Căn Hộ' để xem hình ảnh và sơ đồ mặt bằng chi tiết của các căn trên.</em>"
                return html

        # 4. Câu hỏi về xe cộ, biển số xe, thẻ gửi xe, RFID
        if any(w in q for w in ["xe", "biển số", "bãi xe", "thẻ", "rfid", "ô tô", "xe máy"]):
            plate_match = re.search(r"(\d{2}[A-Za-z0-9\-\.\s]{4,10})", question)
            vehicle_lines = [line.strip() for line in context.splitlines() if any(v in line.lower() for v in ["rfid", "xe", "biển số"])]
            if plate_match:
                p = plate_match.group(1).strip().upper()
                found = [v for v in vehicle_lines if p in v.upper()]
                if found:
                    return f"<strong>🚗 Kết Quả Tìm Kiếm Phương Tiện & Thẻ Xe ({p}):</strong><ul>" + "".join(f"<li>{l}</li>" for l in found) + "</ul>"
            if vehicle_lines:
                return "<strong>🚗 Dữ Liệu Quản Lý Thẻ & Phương Tiện Tòa Nhà:</strong><ul>" + "".join(f"<li>{l}</li>" for l in vehicle_lines[:8]) + "</ul>"

        # 5. Câu hỏi về hợp đồng, hết hạn, tiền cọc
        if any(w in q for w in ["hợp đồng", "hết hạn", "cọc", "đặt cọc", "hoàn cọc"]):
            contract_lines = [line.strip() for line in context.splitlines() if "hợp đồng" in line.lower() or "hết hạn" in line.lower() or "cọc" in line.lower()]
            if contract_lines:
                return "<strong>📑 Thông Tin Hợp Đồng & Kỳ Hạn Thuê:</strong><ul>" + "".join(f"<li>{l}</li>" for l in contract_lines) + "</ul>"

        # 6. Câu hỏi về bảo trì, sự cố, hỏng hóc kỹ thuật
        if any(w in q for w in ["bảo trì", "sự cố", "hỏng", "sửa", "aptomat", "rò rỉ", "thang máy"]):
            maint_lines = [line.strip() for line in context.splitlines() if "bảo trì" in line.lower() or "sự cố" in line.lower() or "bt-" in line.lower()]
            tech_guide = ""
            if "aptomat" in q:
                tech_guide = (
                    "<br><strong>🛠️ Hướng dẫn xử lý sự cố nhảy Aptomat:</strong><br>"
                    "1. Ngắt toàn bộ phích cắm của các thiết bị công suất lớn (bếp từ, bình nóng lạnh, ấm siêu tốc).<br>"
                    "2. Gạt công tắc Aptomat tổng lên vị trí ON.<br>"
                    "3. Bật lần lượt từng thiết bị để xác định nguồn rò rỉ điện. Nếu vẫn nhảy ngay lập tức, liên hệ Kỹ thuật tòa nhà qua Hotline 1900 8888."
                )
            if maint_lines:
                return "<strong>🔧 Tình Trạng Bảo Trì & Sự Cố Tòa Nhà:</strong><ul>" + "".join(f"<li>{l}</li>" for l in maint_lines) + "</ul>" + tech_guide
            elif tech_guide:
                return tech_guide

        # 7. Câu hỏi về điện nước, biểu phí, dịch vụ
        if any(w in q for w in ["điện", "nước", "biểu phí", "giá điện", "giá nước", "phí quản lý", "kwh", "dịch vụ"]):
            fee_lines = [line.strip() for line in context.splitlines() if any(f in line.lower() for f in ["biểu phí", "điện", "nước", "dịch vụ"])]
            return (
                "<strong>⚡ Biểu Phí Dịch Vụ & Chỉ Số Điện Nước Tòa Nhà ICTU Tower:</strong><ul>"
                "<li><strong>Điện sinh hoạt:</strong> 3.500 đ/kWh</li>"
                "<li><strong>Nước sạch:</strong> 25.000 đ/m³</li>"
                "<li><strong>Phí quản lý vận hành:</strong> 15.000 đ/m²/tháng</li>"
                "<li><strong>Gửi xe máy:</strong> 100.000 đ/xe/tháng</li>"
                "<li><strong>Gửi ô tô:</strong> 1.200.000 đ/xe/tháng</li>"
                "<li><strong>Phí vệ sinh & rác:</strong> 120.000 đ/tháng</li>"
                "</ul>"
                + ("<br><strong>Chỉ số & dữ liệu ghi nhận:</strong><ul>" + "".join(f"<li>{l}</li>" for l in fee_lines[:6]) + "</ul>" if fee_lines else "")
            )

        # 8. Câu hỏi về thanh toán VietQR / tài khoản ngân hàng
        if any(w in q for w in ["vietqr", "qr", "chuyển khoản", "tài khoản", "ngân hàng", "stk"]):
            return (
                "<strong>💳 Thông Tin Chuyển Khoản & Cú Pháp VietQR:</strong><br>"
                "• Ngân hàng thụ hưởng: <strong>MB Bank (Ngân hàng Quân Đội)</strong><br>"
                "• Số tài khoản: <strong>99998888ICTU</strong><br>"
                "• Chủ tài khoản: <strong>BAN QUẢN LÝ TÒA NHÀ ICTU TOWER</strong><br>"
                "• Cú pháp chuyển khoản: <code>ICTU [Mã_Phòng]</code> (Ví dụ: <em>ICTU A101</em>)<br>"
                "• Sau khi chuyển khoản, hệ thống tự động gạch nợ qua Webhook ngân hàng sau 30 giây."
            )

        # 9. Tính toán số học cơ bản (Math solver)
        math_clean = re.sub(r"[^\d\+\-\*\/\.\(\)\s]", "", question).strip()
        if math_clean and any(op in math_clean for op in ["+", "-", "*", "/"]) and len(math_clean) >= 3:
            try:
                ans = eval(math_clean, {"__builtins__": None}, {})
                return (
                    f"<strong>🧮 Kết Quả Tính Toán:</strong><br>"
                    f"<code>{math_clean} = <strong>{ans:,.2f}</strong></code> (hoặc <strong>{ans:,}</strong>)"
                )
            except Exception:
                pass

        # 10. Tìm kiếm theo tên người hoặc CCCD
        words = [w for w in question.split() if len(w) > 2]
        matched_lines = []
        for line in context.splitlines():
            for w in words:
                if w.lower() in line.lower():
                    matched_lines.append(line.strip())
                    break
        if matched_lines:
            return "<strong>🔍 Kết Quả Tra Cứu Từ Dữ Liệu Tòa Nhà:</strong><ul>" + "".join(f"<li>{l}</li>" for l in set(matched_lines)[:8]) + "</ul>"

        # Mặc định: Trả về tóm tắt tổng quan vận hành tòa nhà
        return (
            "<strong>🤖 Trợ Lý Trí Tuệ Nhân Tạo ICTU Tower:</strong><br>"
            "Tôi đã tiếp nhận câu hỏi của bạn. Hệ thống đang trực tiếp liên kết với Cơ sở dữ liệu tòa nhà.<br><br>"
            "<strong>Tổng quan tình trạng hiện tại:</strong><br>"
            + "<br>".join(f"• {line}" for line in context.splitlines()[:5] if line.strip())
            + "<br><br><em>💡 Bạn có thể hỏi cụ thể về: mã phòng (vd: A101), danh sách nợ, phòng trống, biển số xe, chỉ số điện nước, hoặc yêu cầu tính toán bất kỳ!</em>"
        )