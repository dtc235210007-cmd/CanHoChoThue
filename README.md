<div align="center">

# 🏢 ICTU TOWER - ENTERPRISE AI APARTMENT MANAGEMENT
### Hệ Thống Quản Trị Căn Hộ Cho Thuê Thông Minh Tích Hợp Google Gemini AI & PostgreSQL

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-AI%20SDK-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*Dự án giải pháp quản trị toàn diện cho ban quản lý tòa nhà, chung cư mini và chuỗi căn hộ dịch vụ cao cấp.*

</div>

---

## 📖 Giới Thiệu Dự Án

**ICTU Tower** là nền tảng quản trị căn hộ thông minh được phát triển theo mô hình Client-Server hiện đại. Hệ thống kết hợp sức mạnh xử lý dữ liệu quan hệ của **PostgreSQL** cùng mô hình ngôn ngữ lớn **Google Gemini AI**, hỗ trợ tối ưu hóa quy trình quản trị, tự động hóa tương tác khách hàng và hỗ trợ ra quyết định kinh doanh theo từng vị trí vai trò (Ban Giám Đốc, Kế Toán, Kỹ Thuật).

---

## ✨ Tính Năng Nổi Bật

### 1. 🏢 Quản Lý Nghiệp Vụ Toàn Diện (8 Phân Hệ)
- **Quản lý Căn hộ (Rooms)**: Theo dõi trực quan sơ đồ căn hộ, tình trạng phòng (`Đã thanh toán`, `Còn nợ`, `Phòng trống`, `Đang bảo trì`), đơn giá, diện tích và hình ảnh.
- **Quản lý Khách thuê (Tenants)**: Lưu trữ hồ sơ định danh CCCD, thông tin liên hệ, phòng thuê hiện tại.
- **Quản lý Hợp đồng (Contracts)**: Giám sát chu kỳ hợp đồng thuê, tiền cọc, ngày bắt đầu/kết thúc và cảnh báo thời hạn.
- **Quản lý Bảo trì (Maintenance)**: Tiếp nhận yêu cầu, phân loại mức độ khẩn cấp (Khẩn cấp, Cao, Bình thường) và cập nhật tiến độ xử lý sự cố kỹ thuật.
- **Tính toán Dịch vụ & Điện nước (Services)**: Nhập chỉ số điện/nước cũ - mới, tự động tính tổng tiền dịch vụ (điện, nước, rác, gửi xe, phí quản lý tòa nhà).
- **Quản lý Phương tiện & Thẻ cư dân (Vehicles)**: Cấp phát và quản lý thẻ thang máy, thẻ bãi xe, biển số, loại phương tiện.
- **Sổ Quỹ Thu Chi & Dòng tiền (Cashflow)**: Ghi nhận minh bạch các khoản thu phí, chi trả đối tác, tiền cọc và cân đối ngân sách.
- **Nhật ký Hoạt động (Audit Logs)**: Tự động lưu vết lịch sử mọi thao tác người dùng trên hệ thống, phục vụ tra soát bảo mật.

---

### 2. 🤖 Trợ Lý Trí Tuệ Nhân Tạo (Google Gemini AI)
- **Tóm tắt & Bóc tách Hợp đồng thông minh**: Phân tích nhanh văn bản hợp đồng thuê, tự động nhận diện bên thuê/cho thuê, thời hạn, tiền cọc, giá thuê và cảnh báo các điều khoản rủi ro pháp lý.
- **Tự động Soạn Thảo Thông Báo Đa Sắc Thái**: Sinh thông báo gửi khách thuê (nhắc thanh toán nợ, gia hạn hợp đồng, lịch bảo dưỡng, nhắc nhở vi phạm quy chế) theo 3 sắc thái giọng điệu:
  - 🕊️ *Lịch sự & Trang trọng* (Phù hợp định kỳ)
  - 🤝 *Thân thiện & Hỗ trợ* (Gắn kết cư dân)
  - ⚡ *Quyết liệt & Khẩn cấp* (Xử lý nợ đọng, vi phạm)
- **Chatbot Trợ Lý Tòa Nhà Hỏi Đáp Ngữ Cảnh Thật**: Giải đáp quy chế tòa nhà và phản hồi thông tin dựa trên dữ liệu thời gian thực được đồng bộ từ CSDL.
- **Phân Quyền Trợ Lý Theo 3 Vai Trò (Role-Based Persona)**:
  - 👔 **Ban Giám Đốc (Admin)**: Tập trung vào rủi ro pháp lý, tỷ lệ lấp đầy, chiến lược tối ưu dòng tiền.
  - 📊 **Kế Toán Trưởng (Accountant)**: Tập trung vào số liệu tài chính, công nợ, đối chiếu hóa đơn, chứng từ.
  - 🔧 **Kỹ Thuật / Vận Hành (Staff)**: Tập trung vào an toàn thiết bị, bảo trì, tiến độ sửa chữa hạ tầng.
- **Cơ Chế Offline Fallback An Toàn**: Khi mất kết nối Internet hoặc lỗi API, hệ thống kích hoạt bộ máy phân tích dự phòng Offline dựa trên Regex & Rule-Engine, cam kết **không bịa đặt thông tin**.

---

### 3. 🎨 Giao Diện Người Dùng Hiện Đại (Modern Dashboard UI)
- Thiết kế Single Page Application (SPA) mượt mà, thân thiện trên cả Desktop và Tablet/Mobile.
- Tích hợp biểu đồ trực quan hóa doanh thu và cơ cấu phòng với **Chart.js**.
- Hộp thoại cảnh báo và xác nhận đẹp mắt với **SweetAlert2**.

---

## 🛠️ Công Nghệ Sử Dụng

| Thành Phần | Công Nghệ / Thư Viện |
| :--- | :--- |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| **Database & ORM** | PostgreSQL 14+, SQLAlchemy 2.0+, Psycopg2-binary |
| **AI & LLM** | Google Gemini API (gemini-2.0-flash, gemini-1.5-flash), google-genai SDK |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Font Awesome 6 |
| **Visualization** | Chart.js, SweetAlert2 |
| **Config & Env** | Python-Dotenv |

---

## 📁 Cấu Trúc Thư Mục Dự Án

```text
DemoQL/
├── app/
│   ├── __init__.py          # Module init
│   ├── ai_service.py        # Module xử lý AI Gemini, Prompt Engineering & Offline Fallback
│   ├── database.py          # Cấu hình SQLAlchemy Engine, SessionLocal & kết nối PostgreSQL
│   ├── main.py              # Ứng dụng FastAPI chính, khai báo các API Routes & Router
│   ├── models.py            # Khai báo cấu trúc bảng CSDL (Room, Tenant, Contract, v.v.)
│   ├── seed_data.py         # Script tự động tạo bảng và nạp sẵn dữ liệu mẫu
│   └── test_db.py           # Script kiểm tra kết nối PostgreSQL và thống kê dữ liệu
├── static/
│   └── index.html           # Giao diện Single Page Application (HTML/CSS/JS)
├── .env.example             # File mẫu cấu hình biến môi trường
├── .gitignore               # Cấu hình bỏ qua các file nhạy cảm và rác khi đẩy Git
├── requirements.txt         # Danh sách thư viện Python phụ thuộc
└── README.md                # Tài liệu hướng dẫn sử dụng và giới thiệu dự án
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Dự Án

### 1. Yêu Cầu Tiên Quyết
- Đã cài đặt **Python 3.10** trở lên ([Tải tại đây](https://www.python.org/downloads/)).
- Đã cài đặt **PostgreSQL** và công cụ **pgAdmin** ([Tải tại đây](https://www.postgresql.org/download/)).
- Khóa **Google Gemini API Key** ([Đăng ký miễn phí tại Google AI Studio](https://aistudio.google.com/apikey)).

---

### 2. Các Bước Thực Hiện Chi Tiết

#### Bước 1: Clone Repository về máy tính
```bash
git clone https://github.com/dtc235210007-cmd/CanHoChoThue.git
cd CanHoChoThue
```

#### Bước 2: Tạo và kích hoạt môi trường ảo (Virtual Environment)
- **Trên Windows (cmd / PowerShell):**
  ```bash
  python -m venv venv
  .\venv\Scripts\activate
  ```
- **Trên Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

#### Bước 3: Cài đặt các gói thư viện cần thiết
```bash
pip install -r requirements.txt
```

#### Bước 4: Thiết lập biến môi trường `.env`
Sao chép file `.env.example` thành `.env`:
```bash
# Windows:
copy .env.example .env

# Linux / macOS:
cp .env.example .env
```
Mở file `.env` và điền cấu hình của bạn:
```ini
# API Key lấy từ https://aistudio.google.com/apikey
GEMINI_API_KEY=your_actual_gemini_api_key

# Chuỗi kết nối PostgreSQL: postgresql://[user]:[password]@[host]:[port]/[database_name]
DATABASE_URL=postgresql://postgres:123456@localhost:5432/ictu_tower
```

#### Bước 5: Khởi tạo Database trên PostgreSQL
1. Mở **pgAdmin** (hoặc `psql`), tạo một Database mới có tên: `ictu_tower`.
2. Chạy lệnh kiểm tra kết nối và nạp dữ liệu khởi tạo tự động:
   ```bash
   python app/test_db.py
   ```
   *Khi thấy thông báo nạp thành công 8 bảng dữ liệu là đã kết nối CSDL chuẩn xác.*

#### Bước 6: Khởi chạy Server
```bash
uvicorn app.main:app --reload --port 8000
```

---

### 3. Trải Nghiệm Ứng Dụng

Sau khi khởi chạy server thành công:
- 🌐 **Giao diện Quản trị**: Mở trình duyệt và truy cập: [http://localhost:8000](http://localhost:8000)
- 📚 **Tài liệu API Tương tác (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 📑 **Tài liệu API Redoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 Danh Sách API Chính (Endpoints Overview)

| Phương Thức | Đường Dẫn | Chức Năng |
| :---: | :--- | :--- |
| `GET` | `/api/v1/db/status` | Kiểm tra trạng thái kết nối PostgreSQL & số lượng bản ghi các bảng |
| `GET` | `/api/v1/data/all` | Lấy dữ liệu toàn bộ 8 bảng phục vụ hiển thị trên giao diện |
| `POST` | `/api/v1/data/sync` | Đồng bộ lưu dữ liệu từ giao diện vào PostgreSQL |
| `POST` | `/api/v1/db/reseed` | Khôi phục lại bộ dữ liệu mẫu ban đầu |
| `GET` | `/api/v1/ai/health` | Kiểm tra trạng thái kích hoạt của Gemini API Key |
| `POST` | `/api/v1/ai/summarize-contract` | AI tóm tắt, phân tích và trích xuất điều khoản hợp đồng |
| `POST` | `/api/v1/ai/generate-notice` | AI tự động soạn thảo thông báo theo sắc thái và ngữ cảnh |
| `POST` | `/api/v1/ai/chat` | Chatbot hỏi đáp thông minh với ngữ cảnh tòa nhà thời gian thực |

---

## 🔐 Bảo Mật & Lưu Ý Khi Triển Khai (Security Notes)

- Không bao giờ commit file `.env` chứa API Key hoặc thông tin tài khoản Database lên GitHub. File `.gitignore` đã được cấu hình mặc định để loại trừ `.env`.
- API Key Gemini hỗ trợ cả định dạng **Standard key** (`AIzaSy...`) và **Auth key mới** (`AQ...`).
- Nếu PostgreSQL đổi mật khẩu hoặc cổng port khác `5432`, chỉ cần cập nhật lại giá trị `DATABASE_URL` trong file `.env`.

---

## 👥 Nhóm Tác Giả & Đóng Góp

- **Dự án**: Quản Lý Căn Hộ Cho Thuê ICTU Tower
- **Repository**: [https://github.com/dtc235210007-cmd/CanHoChoThue](https://github.com/dtc235210007-cmd/CanHoChoThue)

Mọi đóng góp (Pull Request, Báo cáo lỗi Issue) đều được hoan nghênh để hoàn thiện hệ thống! 🚀

---

<div align="center">
  <sub>Phát triển với ❤️ bởi đội ngũ ICTU Tower • © 2026 All Rights Reserved</sub>
</div>
