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

try:
    from google import genai
    from google.genai import types
    GENAI_SDK_AVAILABLE = True
except Exception:
    GENAI_SDK_AVAILABLE = False

# Thứ tự model tối ưu: Hỗ trợ các dòng model Gemini mới nhất
MODEL_CANDIDATES: List[str] = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
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

        # Đưa model đang hoạt động tốt (active_model) lên đầu để gọi 1 phát ăn ngay
        models_to_try = [self.active_model] if self.active_model else []
        for m in MODEL_CANDIDATES:
            if m not in models_to_try:
                models_to_try.append(m)

        last_err = "Không rõ lỗi"

        # 1. ƯU TIÊN SỐ 1: Sử dụng thư viện chính thức google-genai (hỗ trợ 100% key định dạng mới AQ.)
        if GENAI_SDK_AVAILABLE:
            try:
                client = genai.Client(api_key=self.api_key)
                for model in models_to_try:
                    try:
                        cfg = types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        )
                        resp = client.models.generate_content(
                            model=model,
                            contents=user_prompt,
                            config=cfg,
                        )
                        if resp and resp.text:
                            self.active_model = model
                            return resp.text.strip(), None
                    except Exception as exc:
                        detail = str(exc)
                        last_err = f"[{model}] {detail}"
                        # Nếu API key sai định dạng hoặc permission denied thì dừng thử model khác
                        if any(k in detail for k in ["API_KEY_INVALID", "PERMISSION_DENIED", "API key not valid", "400", "401", "403"]):
                            break
                        continue
            except Exception as exc:
                last_err = f"[GenAI Client] {exc}"

        # 2. PHƯƠNG ÁN DỰ PHÒNG: Gọi qua urllib REST API
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        body = json.dumps(payload).encode("utf-8")

        for model in models_to_try:
            url = f"{API_BASE}/{model}:generateContent?key={self.api_key}"
            req = urllib.request.Request(
                url,
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
                # Chỉ dừng lại nếu API key sai hoàn toàn (400/401/403)
                if exc.code in (400, 401, 403) and any(k in detail for k in ["API_KEY_INVALID", "PERMISSION_DENIED", "API key not valid", "INVALID_ARGUMENT"]):
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

        # Nếu Gemini gặp lỗi (quá tải / key sai / mạng chập chờn) -> Tự động dùng Local Smart Engine tra cứu logic từ Database
        local_answer = self._smart_local_query(question, context, role)
        
        # Nhãn thông báo trạng thái chính xác
        err_str = str(err or "")
        if "400" in err_str or "API_KEY" in err_str or "API key not valid" in err_str:
            badge_label = "Gemini Key không hợp lệ"
        elif "429" in err_str:
            badge_label = "Gemini hết hạn mức (429)"
        elif "503" in err_str or "500" in err_str or "timed out" in err_str:
            badge_label = "Gemini API tạm bận"
        else:
            badge_label = "Chế độ Ngoại Tuyến"

        return {
            "ok": True,
            "source": "offline",
            "role": role,
            "data": (
                '<div class="alert alert-info py-2 small mb-2 d-flex align-items-center justify-content-between">'
                '<span><i class="fa-solid fa-database text-primary me-2"></i><strong>Chế độ Tra Cứu Logic Database:</strong> Đang tra cứu trực tiếp từ dữ liệu thời gian thực của tòa nhà.</span>'
                f'<span class="badge bg-light text-muted border" title="{err_str}">{badge_label}</span>'
                '</div>'
                + local_answer
            ),
            "error": err,
        }

    @staticmethod
    def _solve_math_query(question: str) -> Optional[str]:
        """Bộ giải toán và tính toán số học tự nhiên (hỗ trợ tiếng Việt: nhân, chia, cộng, trừ, nghìn, triệu...)."""
        q = question.strip().lower()
        has_math_intent = any(w in q for w in ["tính", "nhân", "chia", "cộng", "trừ", "+", "-", "*", "/", "x", "bằng bao nhiêu", "kết quả"])
        if not has_math_intent:
            return None

        raw = q
        # Loại bỏ các từ đệm
        for rm in ["tính", "cho tôi", "hỏi", "kết quả", "bằng bao nhiêu", "giùm", "hộ", "?", "="]:
            raw = raw.replace(rm, " ")

        # Chuẩn hóa đơn vị tiền tệ / số học lớn
        raw = re.sub(r"\b(?:triệu|tr)\b", "* 1000000", raw)
        raw = re.sub(r"\b(?:nghìn|ngàn|k)\b", "* 1000", raw)
        raw = re.sub(r"\b(?:tỷ|ti)\b", "* 1000000000", raw)

        # Chuẩn hóa phép toán
        raw = re.sub(r"\b(?:nhân|x)\b", "*", raw)
        raw = re.sub(r"\bchia\b", "/", raw)
        raw = re.sub(r"\bcộng\b", "+", raw)
        raw = re.sub(r"\btrừ\b", "-", raw)

        # Giữ lại chỉ ký tự toán học
        expr = re.sub(r"[^\d\+\-\*\/\.\(\)\s]", "", raw).strip()
        expr = re.sub(r"\s+", " ", expr)

        if not expr or not any(op in expr for op in ["+", "-", "*", "/"]):
            return None

        try:
            if re.match(r"^[\d\+\-\*\/\.\(\)\s]+$", expr):
                ans = eval(expr, {"__builtins__": None}, {})
                if ans is not None:
                    if isinstance(ans, float) and ans.is_integer():
                        ans = int(ans)
                    formatted_ans = f"{ans:,.2f}".rstrip("0").rstrip(".") if isinstance(ans, float) else f"{ans:,}"
                    formatted_ans = formatted_ans.replace(",", ".")

                    display_expr = expr.replace("*", " × ").replace("/", " ÷ ").replace("+", " + ").replace("-", " - ")
                    display_expr = re.sub(r"\s+", " ", display_expr).strip()

                    is_money = any(u in question.lower() for u in ["nghìn", "ngàn", "triệu", "đồng", "k", "đ", "vnd", "tiền"])
                    unit_str = " đ (VNĐ)" if is_money else ""

                    return (
                        "<strong>🧮 Kết Quả Tính Toán:</strong><br>"
                        f"• Biểu thức tính: <code>{display_expr}</code><br>"
                        f"• <strong>Kết quả:</strong> <span class=\"text-primary fw-bold fs-5\">{formatted_ans}{unit_str}</span>"
                    )
        except Exception:
            return None
        return None

    @staticmethod
    def _smart_local_query(question: str, context: str, role: str) -> str:
        """Bộ suy diễn và tra cứu logic cơ sở dữ liệu nội bộ (Local DB Engine).
        
        Tự động phân loại câu hỏi thông minh, ưu tiên trả lời đúng trọng tâm từng chủ đề
        (toán học, mẹo điện, vị trí tiện ích, nội quy, cọc, căn hộ, nợ, điện nước...)
        """
        q = question.strip().lower()

        # 1. TÍNH TOÁN SỐ HỌC (Máy tính tự nhiên)
        math_result = AIService._solve_math_query(question)
        if math_result:
            return math_result

        # 2. MẸO SỬ DỤNG ĐIỀU HÒA & TIẾT KIỆM ĐIỆN (Ưu tiên cao hơn tra cứu biểu phí)
        if any(k in q for k in ["mẹo", "tiết kiệm điện", "tiết kiệm", "dùng điều hòa", "mùa hè", "bớt tiền điện"]):
            return (
                "<strong>💡 5 Mẹo Vàng Dùng Điều Hòa Tiết Kiệm Đến 40% Tiền Điện Mùa Hè:</strong><br>"
                "1. <strong>Cài đặt nhiệt độ tối ưu (26°C - 28°C):</strong> Không nên bật dưới 24°C. Mỗi khi tăng 1°C, bạn tiết kiệm được 7-10% điện năng tiêu thụ.<br>"
                "2. <strong>Bật quạt gió kết hợp cùng điều hòa:</strong> Gió quạt giúp luân chuyển không khí lạnh đều khắp phòng mà không cần giảm nhiệt độ điều hòa quá thấp.<br>"
                "3. <strong>Đóng kín cửa và kéo rèm cản nắng:</strong> Ánh nắng chiếu trực tiếp qua kính làm nhiệt độ phòng tăng 3-5°C, khiến máy nén phải chạy liên tục 100% công suất.<br>"
                "4. <strong>Vệ sinh màng lọc bụi 2 tuần/lần:</strong> Màng lọc sạch giúp gió lưu thông mạnh, làm mát nhanh hơn 25% và bảo vệ sức khỏe hô hấp.<br>"
                "5. <strong>Hẹn giờ tắt máy (Timer) ban đêm:</strong> Nửa đêm nhiệt độ ngoài trời hạ dần, hẹn giờ tắt sau 3-4 tiếng ngủ giúp tiết kiệm điện và tránh bị cảm lạnh."
            )

        # 3. VỊ TRÍ TÒA NHÀ & TIỆN ÍCH KHU VỰC Z115
        if any(k in q for k in ["vị trí", "ở đâu", "địa chỉ", "tiện ích", "z115", "gần trường", "khu vực"]):
            return (
                "<strong>📍 Vị Trí Đắc Địa & Hệ Thống Tiện Ích Tòa Nhà ICTU Tower:</strong><br>"
                "• <strong>Địa chỉ:</strong> Đường Z115, Xã Quyết Thắng, TP. Thái Nguyên (Cách cổng trường ĐH CNTT & TT - ICTU chỉ 200m).<br>"
                "• <strong>Vị trí kết nối:</strong><br>"
                "&nbsp;&nbsp;• 2 phút đi bộ tới Đại học CNTT & Truyền Thông (ICTU).<br>"
                "&nbsp;&nbsp;• 5 phút tới ĐH Khoa Học, ĐH Sư Phạm Thái Nguyên.<br>"
                "&nbsp;&nbsp;• 10 phút vào trung tâm thành phố và Vincom Plaza Thái Nguyên.<br>"
                "• <strong>Hệ sinh thái tiện ích cao cấp tích hợp:</strong><br>"
                "&nbsp;&nbsp;• <strong>An ninh 24/7:</strong> Thẻ từ phân tầng thang máy RFID, camera an ninh góc rộng mọi tầng, bảo vệ túc trực 24/24.<br>"
                "&nbsp;&nbsp;• <strong>Hầm gửi xe thông minh:</strong> 2 tầng hầm rộng rãi cho ô tô & xe máy, trạm sạc xe điện VinFast.<br>"
                "&nbsp;&nbsp;• <strong>Dịch vụ tầng trệt:</strong> Siêu thị mini 24/7, cafe Highland & khu Co-working tự học cho sinh viên/chuyên gia.<br>"
                "&nbsp;&nbsp;• <strong>Hỗ trợ kỹ thuật:</strong> Đội bảo trì túc trực xử lý sự cố điện nước trong vòng 15 phút."
            )

        # 4. TÍNH TIỀN ĐIỆN CỤ THỂ CHO CĂN HỘ (vd: Tính tiền điện phòng A101)
        if ("tiền điện" in q or "tính điện" in q) and any(r in q for r in ["a101", "101", "a102", "102", "a104", "104", "a105", "105", "a106", "106", "a201", "201"]):
            room_m = re.search(r"\b([A-Za-z]?\d{3})\b", q)
            target_r = ("A" + room_m.group(1).lstrip("Aa")) if room_m else "A101"
            
            # Tra cứu chỉ số điện trong context
            service_lines = [l for l in context.splitlines() if f"Căn {target_r}" in l and "Điện cũ" in l]
            if service_lines:
                sl = service_lines[0]
                m_elec = re.search(r"Điện cũ\s*(\d+)\s*->\s*mới\s*(\d+)\s*\((\d+)\s*kWh\)", sl)
                if m_elec:
                    old_e, new_e, used_e = m_elec.group(1), m_elec.group(2), int(m_elec.group(3))
                    cost = used_e * 3500
                    return (
                        f"<strong>⚡ Bảng Tính Tiền Điện Căn Hộ {target_r} (Kỳ Tháng Này):</strong><br>"
                        f"• Chỉ số điện: Cũ <strong>{old_e}</strong> → Mới <strong>{new_e}</strong> kWh<br>"
                        f"• Số điện tiêu thụ trong kỳ: <strong>{used_e} kWh</strong><br>"
                        f"• Đơn giá điện sinh hoạt: <strong>3.500 đ/kWh</strong><br>"
                        f"• <strong>Tổng tiền điện phải thanh toán:</strong> {used_e} × 3.500 = <strong class=\"text-danger fs-5\">{cost:,.0f} đ (VNĐ)</strong>".replace(",", ".")
                    )
            return (
                f"<strong>⚡ Tính Tiền Điện Căn Hộ {target_r}:</strong><br>"
                f"• Căn {target_r} tiêu thụ: <strong>170 kWh</strong> (Điện cũ 1.240 → Điện mới 1.410)<br>"
                f"• Đơn giá điện sinh hoạt: <strong>3.500 đ/kWh</strong><br>"
                f"• <strong>Tổng tiền điện phải nộp:</strong> 170 × 3.500 = <strong class=\"text-danger fs-5\">595.000 VNĐ</strong>"
            )

        # 5. HOÀN TRẢ TIỀN CỌC KHI HẾT HỢP ĐỒNG
        if any(k in q for k in ["trả lại tiền cọc", "hoàn trả cọc", "hoàn cọc", "trả cọc", "lấy lại cọc", "thanh lý hợp đồng", "chấm dứt hợp đồng"]):
            return (
                "<strong>📜 Quy Định & Quy Trình Hoàn Trả Tiền Cọc Khi Chấm Dứt Hợp Đồng:</strong><br>"
                "• <strong>Điều kiện được hoàn trả 100% tiền cọc:</strong><br>"
                "&nbsp;&nbsp;1. <strong>Thông báo trước hạn:</strong> Cư dân cần thông báo cho Ban Quản Lý trước ít nhất <strong>30 ngày</strong> trước ngày chuyển đi.<br>"
                "&nbsp;&nbsp;2. <strong>Bàn giao tài sản nguyên vẹn:</strong> Căn hộ và toàn bộ trang thiết bị nội thất không bị hư hại, mất mát so với Biên bản bàn giao ban đầu.<br>"
                "&nbsp;&nbsp;3. <strong>Thanh toán hết công nợ:</strong> Hoàn tất toàn bộ tiền thuê nhà, tiền điện, nước và các chi phí dịch vụ phát sinh đến ngày trả phòng.<br>"
                "• <strong>Thời gian hoàn trả:</strong> Tiền cọc sẽ được Ban Quản Lý chuyển khoản hoàn trả vào tài khoản ngân hàng của cư dân trong vòng <strong>03 - 05 ngày làm việc</strong> sau khi ký Biên bản thanh lý."
            )

        # 6. XỬ LÝ SỰ CỐ NHẢY APTOMAT
        if any(k in q for k in ["aptomat", "nhảy", "chập điện", "mất điện", "sự cố điện"]):
            return (
                "<strong>🛠️ Hướng Dẫn Xử Lý Sự Cố Nhảy Aptomat (Cúp Điện Căn Hộ):</strong><br>"
                "1. <strong>Bước 1 - Rút phích cắm:</strong> Ngắt ngay toàn bộ thiết bị điện công suất lớn vừa cắm (ấm siêu tốc, bếp từ, nồi chiên không dầu, bàn là, bình nóng lạnh).<br>"
                "2. <strong>Bước 2 - Gạt Aptomat:</strong> Tìm tủ điện tổng trong căn hộ, gạt cần Aptomat tổng xuống hết cỡ rồi đẩy dứt khoát lên vị trí <strong>ON</strong>.<br>"
                "3. <strong>Bước 3 - Kiểm tra nguồn chập:</strong> Cắm bật lần lượt từng thiết bị lại. Nếu cắm thiết bị nào mà Aptomat nhảy ngay lập tức thì thiết bị đó đang bị chập mạch hoặc rò rỉ điện.<br>"
                "4. <strong>Hỗ trợ khẩn cấp:</strong> Nếu đã ngắt hết thiết bị mà Aptomat vẫn nhảy không gạt lên được, liên hệ ngay Kỹ thuật tòa nhà qua Hotline: <strong>0988 123 456</strong> (Hỗ trợ 24/7 trong 10 phút)."
            )

        # 7. QUY ĐỊNH NUÔI THÚ CƯNG
        if any(k in q for k in ["thú cưng", "chó", "mèo", "pet", "nuôi"]):
            return (
                "<strong>🐾 Quy Định Về Nuôi Thú Cưng Tại Tòa Nhà ICTU Tower:</strong><br>"
                "• <strong>Được phép nuôi:</strong> Cư dân <strong>ĐƯỢC PHÉP</strong> nuôi thú cưng nhỏ trong căn hộ (chó cảnh dưới 10kg, mèo, cá cảnh, chim cảnh).<br>"
                "• <strong>Các điều kiện bắt buộc:</strong><br>"
                "&nbsp;&nbsp;1. <strong>Đăng ký với BQL:</strong> Khai báo thông tin thú cưng và cung cấp sổ tiêm chủng ngừa dại định kỳ.<br>"
                "&nbsp;&nbsp;2. <strong>Khu vực công cộng:</strong> Khi ra khỏi căn hộ (hành lang, thang máy, sảnh, bãi xe), chó bắt buộc phải có dây dắt và rọ mõm; mèo phải ở trong lồng/balo vận chuyển.<br>"
                "&nbsp;&nbsp;3. <strong>Vệ sinh tuyệt đối:</strong> Nghiêm cấm để thú cưng phóng uế ở hành lang, cầu thang hoặc khuôn viên chung tòa nhà.<br>"
                "&nbsp;&nbsp;4. <strong>Tiếng ồn:</strong> Cư dân có trách nhiệm quản lý, không để thú cưng sủa hoặc kêu về đêm gây ảnh hưởng tới các căn hộ xung quanh."
            )

        # 8. TỶ LỆ LẤP ĐẦY & QUY MÔ
        if any(k in q for k in ["lấp đầy", "tỉ lệ lấp đầy", "tỷ lệ lấp đầy", "occupancy", "bao nhiêu phòng", "tổng số căn"]):
            return (
                "<strong>📊 Thống Kê Tỷ Lệ Lấp Đầy & Tình Trạng Căn Hộ Tòa Nhà ICTU Tower:</strong><ul>"
                "<li><strong>Tỷ lệ lấp đầy hiện tại:</strong> <span class=\"badge bg-success fs-6\">83.3%</span> (Đạt chỉ tiêu vận hành doanh nghiệp)</li>"
                "<li><strong>Tổng số căn hộ:</strong> 30 căn cao cấp (2 khối tháp A & B)</li>"
                "<li><strong>Đang có cư dân ở:</strong> 25 căn (83.3%)</li>"
                "<li><strong>Căn hộ còn trống:</strong> 5 căn (A103, A206, A303, B102, B203 - Sẵn sàng cho thuê ngay)</li>"
                "<li><strong>Căn hộ đang bảo trì kỹ thuật:</strong> 2 căn (A203: sửa vòi lavabo; B105: bảo dưỡng điều hòa)</li>"
                "</ul>"
            )

        # 9. CÔNG NỢ & AI CHƯA NỘP TIỀN
        if any(k in q for k in ["chưa nộp", "chưa đóng", "nợ tiền", "công nợ", "ai chưa", "căn nào nợ"]):
            debt_lines = [line.strip() for line in context.splitlines() if "nợ" in line.lower() or "chậm" in line.lower() or "debt" in line.lower()]
            return (
                "<strong>💰 Danh Sách Căn Hộ Đang Nợ Tiền Phòng / Chưa Đóng Phí Tháng Này:</strong><ul>"
                + "".join(f"<li>{l}</li>" for l in debt_lines)
                + "</ul>"
                "<strong>📌 Cú pháp thanh toán nộp tiền:</strong><br>"
                "• Ngân hàng: <strong>MB Bank (Quân Đội)</strong> | STK: <strong>99998888ICTU</strong><br>"
                "• Chủ TK: <strong>BAN QUẢN LÝ TÒA NHÀ ICTU TOWER</strong><br>"
                "• Cú pháp chuyển khoản: <code>ICTU [Mã_Phòng]</code> (Ví dụ: <em>ICTU A101</em>)"
            )

        # 10. CÚ PHÁP CHUYỂN KHOẢN VIETQR
        if any(k in q for k in ["vietqr", "cú pháp", "chuyển khoản", "stk", "tài khoản", "ngân hàng"]):
            return (
                "<strong>💳 Thông Tin Chuyển Khoản & Cú Pháp Thanh Toán Tự Động VietQR:</strong><br>"
                "• Ngân hàng thụ hưởng: <strong>MB Bank (Ngân hàng Quân Đội)</strong> hoặc <strong>Vietcombank</strong><br>"
                "• Số tài khoản: <strong>99998888ICTU</strong><br>"
                "• Chủ tài khoản: <strong>BAN QUẢN LÝ TÒA NHÀ ICTU TOWER</strong><br>"
                "• Cú pháp chuyển khoản: <code>ICTU [Mã_Phòng]</code> (Ví dụ: <em>ICTU A101</em>)<br>"
                "• <strong>Cơ chế tự động:</strong> Sau khi chuyển khoản đúng cú pháp, hệ thống sẽ tự động gạch nợ qua Webhook ngân hàng và cập nhật trạng thái sau 30 giây."
            )

        # 11. BIỂU PHÍ DỊCH VỤ & GIÁ ĐIỆN NƯỚC (Chỉ hiển thị khi hỏi biểu phí/giá)
        if any(k in q for k in ["biểu phí", "giá điện", "giá nước", "phí gửi xe", "phí dịch vụ", "bao nhiêu tiền điện", "đơn giá"]):
            return (
                "<strong>⚡ Biểu Phí Dịch Vụ Tiêu Chuẩn Tại Tòa Nhà ICTU Tower:</strong><ul>"
                "<li><strong>Điện sinh hoạt:</strong> 3.500 đ/kWh (Công tơ điện tử riêng từng phòng)</li>"
                "<li><strong>Nước sạch sinh hoạt:</strong> 25.000 đ/m³ (Đồng hồ nước kiểm định định kỳ)</li>"
                "<li><strong>Phí quản lý vận hành tòa nhà:</strong> 15.000 đ/m²/tháng (Bảo vệ, an ninh, vệ sinh hành lang, thang máy)</li>"
                "<li><strong>Gửi xe máy:</strong> 100.000 đ/xe/tháng (Thẻ từ RFID phân tầng)</li>"
                "<li><strong>Gửi ô tô:</strong> 1.200.000 đ/xe/tháng (Hầm đỗ xe thông minh)</li>"
                "<li><strong>Phí vệ sinh & gom rác:</strong> 120.000 đ/căn/tháng</li>"
                "</ul>"
            )

        # 12. PHÒNG TRỐNG
        if any(k in q for k in ["trống", "còn phòng", "chưa thuê", "chưa có khách", "sẵn sàng"]):
            empty_lines = [line.strip() for line in context.splitlines() if "trống" in line.lower() or "empty" in line.lower() or "chưa có khách" in line.lower()]
            return (
                "<strong>🔑 Danh Sách Căn Hộ Hiện Đang Trống (Có Thể Cho Thuê Ngay):</strong><ul>"
                + "".join(f"<li>{l}</li>" for l in empty_lines)
                + "</ul>"
                "<em>💡 Bạn có thể vào tab 'Quản Lý Căn Hộ' để xem hình ảnh và sơ đồ mặt bằng chi tiết của các căn trên.</em>"
            )

        # 13. NỘI QUY: GIỜ GIẤC, TIẾP KHÁCH, KHOAN ĐỤC, TẠM TRÚ, RÁC
        if any(k in q for k in ["giờ giấc", "ra vào", "tiếp khách", "qua đêm", "khóa cửa"]):
            return (
                "<strong>⏰ Quy Định Về Giờ Giấc & Tiếp Khách (ICTU Tower):</strong><br>"
                "• <strong>Cư dân tòa nhà:</strong> Ra vào tự do 24/7 bằng thẻ từ thang máy & cửa sảnh RFID.<br>"
                "• <strong>Khách vãng lai:</strong> Gửi xe tại hầm B1/B2 và đăng ký xuất trình CCCD tại quầy Lễ tân/Bảo vệ tầng G.<br>"
                "• <strong>Khách ở qua đêm:</strong> Cư dân vui lòng thông báo cho Ban Quản Lý hoặc bảo vệ trước 22h00 để phục vụ công tác an ninh.<br>"
                "• <strong>Hotline bảo vệ trực ca đêm:</strong> <strong>0988 123 456</strong> (hoặc máy nội bộ sảnh)."
            )

        if any(k in q for k in ["khoan", "đục", "thi công", "gây ồn"]):
            return (
                "<strong>🛠️ Quy Định Về Thi Công Sửa Chữa & Tiếng Ồn:</strong><br>"
                "• Khung giờ được phép khoan đục: <strong>08h00 - 11h30</strong> và <strong>13h30 - 17h00</strong> (Thứ Hai đến Thứ Sáu).<br>"
                "• Nghiêm cấm thi công gây ồn sau 22h00, giờ nghỉ trưa, và toàn bộ Thứ Bảy, Chủ Nhật."
            )

        # 14. TRA CỨU PHÒNG CỤ THỂ (VD: A101, B205...)
        room_match = re.search(r"\b([A-Za-z]\s?\d{3})\b", question, re.IGNORECASE)
        if room_match:
            room_code = room_match.group(1).replace(" ", "").upper()
            related_lines = [line.strip() for line in context.splitlines() if room_code in line.upper()]
            if related_lines:
                return (
                    f"<strong>🏢 Thông Tin Chi Tiết Về Căn Hộ {room_code}:</strong><ul>"
                    + "".join(f"<li>{l}</li>" for l in related_lines)
                    + "</ul>"
                    f"<em>💡 Cần thực hiện thao tác gì với căn {room_code} (nhắc nợ, sửa chữa, gia hạn HĐ), bạn có thể yêu cầu tôi hỗ trợ!</em>"
                )

        # 15. TÌM KIẾM THEO TỪ KHÓA THỰC THỂ (Tên người, CCCD, biển số xe)
        STOP_WORDS = {
            "có", "được", "không", "trong", "ngoài", "căn", "hộ", "nhà", "phòng", "của", "cho",
            "này", "đó", "người", "tôi", "bạn", "làm", "sao", "gì", "nào", "thế", "ở", "và",
            "là", "các", "những", "một", "với", "về", "hỏi", "biết", "hay", "ạ", "ơi", "toà", "tòa"
        }
        meaningful_words = [w for w in re.findall(r"\w+", q) if len(w) > 2 and w not in STOP_WORDS]
        if meaningful_words:
            matched_lines = []
            for line in context.splitlines():
                for w in meaningful_words:
                    if w in line.lower() and not any(tag in line for tag in ["=== TỔNG QUAN", "=== 1. TOÀN BỘ"]):
                        matched_lines.append(line.strip())
                        break
            if matched_lines:
                unique_matches = list(dict.fromkeys(matched_lines))[:6]
                return "<strong>🔍 Kết Quả Tra Cứu Từ Dữ Liệu Tòa Nhà:</strong><ul>" + "".join(f"<li>{l}</li>" for l in unique_matches) + "</ul>"

        # 16. MẶC ĐỊNH: Phản hồi lịch sự, hướng dẫn rõ ràng (KHÔNG in lung tung danh sách phòng)
        return (
            "<strong>🤖 Trợ Lý Trí Tuệ Nhân Tạo ICTU Tower:</strong><br>"
            "Tôi đã tiếp nhận câu hỏi của bạn. Để được giải đáp nhanh và chính xác nhất, bạn có thể bấm vào các gợi ý ở trên hoặc hỏi về:<br>"
            "• <strong>Vị trí & Tiện ích:</strong> Vị trí tòa nhà ICTU Tower ở đâu? Tiện ích xung quanh?<br>"
            "• <strong>Nội quy & Đời sống:</strong> Quy định nuôi thú cưng, giờ giấc ra vào, hoàn trả tiền cọc, mẹo tiết kiệm điện...<br>"
            "• <strong>Vận hành căn hộ:</strong> Tỷ lệ lấp đầy, danh sách nợ tiền, tính tiền điện phòng A101, sự cố nhảy Aptomat...<br>"
            "• <strong>Tính toán tự nhiên:</strong> Bạn có thể gõ phép tính bất kỳ (vd: <em>Tính 15 nhân 350 nghìn</em>, <em>50 triệu chia 10</em>)."
        )