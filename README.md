# HỆ THỐNG QUẢN LÝ THUÊ CĂN HỘ CÓ TÍCH HỢP AI (APARTMENT AI)

**ĐẠI HỌC THÁI NGUYÊN - TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN VÀ TRUYỀN THÔNG (ICTU)**  
**Học phần:** Ứng dụng trí tuệ nhân tạo (AIA331)  
**Hình thức:** Dự án / Đồ án môn học  
**Mã số đề tài:** 80278  

---

## 🌟 TỔNG QUAN HỆ THỐNG

**Apartment AI** là hệ thống quản lý thuê căn hộ toàn diện kết hợp trí tuệ nhân tạo (Google Gemini AI) và cơ sở dữ liệu quan hệ PostgreSQL, giải quyết bài toán:

1. **Bài toán thực tế**: Đơn vị cho thuê căn hộ cần quản lý căn hộ, khách thuê, hợp đồng, thanh toán tiền thuê, tiền cọc và yêu cầu bảo trì. Việc quản lý thủ công bằng bảng tính thường dễ sai sót hạn thanh toán, khó theo dõi hợp đồng sắp hết hạn và mất nhiều thời gian phản hồi khách thuê. Hệ thống giải quyết triệt để thông qua số hóa vận hành và tự động hóa với AI.
2. **Quản lý phân quyền (RBAC)**: Phân quyền chặt chẽ giữa 3 vai trò: **Quản lý (Admin)**, **Kế toán (Accountant)**, **Nhân viên kỹ thuật (Staff)**, tích hợp thanh chuyển đổi vai trò Demo 1-click tiện lợi.
3. **Quản lý căn hộ, tòa nhà, tiện ích & trạng thái thuê**: Sơ đồ căn hộ trực quan, giám sát trạng thái phòng theo thời gian thực (`Đã thanh toán`, `Còn nợ`, `Phòng trống`, `Đang bảo trì`), đơn giá thuê và diện tích.
4. **Quản lý khách thuê & người liên hệ**: Lưu trữ hồ sơ định danh CCCD, thông tin liên hệ, phòng thuê và hợp đồng liên quan.
5. **Quản lý hợp đồng thuê & cảnh báo**: Giám sát tiền cọc, ngày bắt đầu/kết thúc hợp đồng; tự động cảnh báo hợp đồng sắp hết hạn và các khoản thanh toán quá hạn.
6. **Theo dõi thanh toán, phí dịch vụ & công nợ**: Tự động tính toán chỉ số điện, nước cũ - mới, phí rác, gửi xe, quản lý công nợ cư dân và dòng tiền thu chi minh bạch.
7. **Quản lý yêu cầu bảo trì từ khách thuê**: Tiếp nhận phản ánh sự cố kỹ thuật từ cư dân, phân loại mức độ khẩn cấp (Khẩn cấp, Cao, Bình thường) và cập nhật tiến độ xử lý sửa chữa.
8. **Thống kê công suất thuê, doanh thu, công nợ**: Biểu đồ trực quan hóa tỷ lệ lấp đầy phòng, doanh thu định kỳ và cơ cấu phòng bằng **Chart.js**.
9. **Tích hợp Trí tuệ Nhân tạo & Vector RAG (Gemini AI)**:
   - **Công nghệ Vector & RAG (Retrieval-Augmented Generation)**: Chuyển đổi bộ quy chế tòa nhà thành không gian vector bằng mô hình `text-embedding-004`, tính toán độ tương đồng Cosine Similarity để trích xuất chính xác từng Điều, Khoản nội quy khi cư dân hỏi đáp.
   - **Tóm tắt hợp đồng**: Tự động bóc tách các điều khoản trọng yếu, quyền và nghĩa vụ hai bên, đồng thời phát hiện và cảnh báo rủi ro pháp lý.
   - **Sinh thông báo thanh toán & vận hành**: Soạn thảo thông báo nhắc nợ, gia hạn hợp đồng, lịch bảo dưỡng, nhắc nhở nội quy theo 3 sắc thái (*Lịch sự & Trang trọng*, *Thân thiện & Gắn kết*, *Quyết liệt & Khẩn cấp*).
   - **Trợ lý hỏi đáp quy định thuê nhà**: Chatbot thông minh giải đáp quy chế tòa nhà dựa trên ngữ cảnh dữ liệu thời gian thực được đồng bộ từ CSDL và Vector RAG.
   - **Cơ chế Offline Fallback an toàn**: Tự động kích hoạt bộ phân tích dự phòng Regex khi mất mạng hoặc hết quota API, cam kết **không bịa đặt thông tin**.

---

## 🛠️ CÔNG NGHỆ SỬ DỤNG

| Phân Loại | Công Nghệ / Thư Viện | Mô Tả |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic | Xây dựng RESTful API hiệu năng cao, xác thực dữ liệu chặt chẽ |
| **Database & ORM** | PostgreSQL 14+, SQLAlchemy 2.0+, Psycopg2 | Hệ quản trị CSDL quan hệ tin cậy, thao tác ORM hướng đối tượng |
| **AI & LLM** | Google Gemini API (gemini-2.0-flash, gemini-1.5-flash) | Mô hình ngôn ngữ lớn xử lý văn bản, tóm tắt và sinh thông báo |
| **Vector & RAG** | Text-Embedding-004, Cosine Similarity, Vector Store | Không gian vector đặc trưng, tìm kiếm tương đồng ngữ nghĩa (Semantic Search) |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3 | Giao diện Single Page Application (SPA) responsive, hiện đại |
| **Giao diện & Biểu đồ**| Chart.js, SweetAlert2, Font Awesome 6 | Biểu đồ thống kê trực quan và hộp thoại tương tác người dùng |
| **Cấu hình** | Python-Dotenv | Quản lý biến môi trường bảo mật |

---

## 📁 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
DemoQL/
├── app/
│   ├── __init__.py          # Khởi tạo module app
│   ├── ai_service.py        # Module xử lý AI Gemini, Prompt Engineering & Offline Fallback
│   ├── rag_service.py       # Module Vector Database, Embedding & Cosine Similarity Search (RAG)
│   ├── database.py          # Cấu hình SQLAlchemy Engine, SessionLocal & kết nối PostgreSQL
│   ├── main.py              # Ứng dụng FastAPI chính, khai báo các API Endpoints
│   ├── models.py            # Khai báo cấu trúc bảng CSDL (Room, Tenant, Contract, v.v.)
│   ├── seed_data.py         # Script tự động khởi tạo bảng và nạp sẵn dữ liệu mẫu
│   ├── test_db.py           # Script kiểm tra kết nối PostgreSQL và thống kê dữ liệu
│   └── data/
│       └── quy_dinh_toa_nha.txt # Cơ sở tri thức quy chế tòa nhà cho hệ thống Vector RAG
├── static/
│   └── index.html           # Giao diện Single Page Application (HTML/CSS/JS)
├── .env.example             # File mẫu cấu hình biến môi trường
├── .gitignore               # Cấu hình bỏ qua các file nhạy cảm và rác khi đẩy Git
├── requirements.txt         # Danh sách các thư viện Python phụ thuộc
└── README.md                # Tài liệu hướng dẫn sử dụng và báo cáo dự án
```

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY DỰ ÁN

### 1. Yêu Cầu Tiên Quyết
- Đã cài đặt **Python 3.10** trở lên ([python.org](https://www.python.org/downloads/)).
- Đã cài đặt **PostgreSQL** & **pgAdmin** ([postgresql.org](https://www.postgresql.org/download/)).
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
# Trên Windows:
copy .env.example .env

# Trên Linux / macOS:
cp .env.example .env
```
Mở file `.env` và cập nhật thông tin của bạn:
```ini
# API Key lấy từ https://aistudio.google.com/apikey
GEMINI_API_KEY=your_actual_gemini_api_key

# Chuỗi kết nối PostgreSQL: postgresql://[user]:[password]@[host]:[port]/[database_name]
DATABASE_URL=postgresql://postgres:123456@localhost:5432/ictu_tower
```

#### Bước 5: Khởi tạo Database trên PostgreSQL
1. Mở **pgAdmin** (hoặc công cụ `psql`), tạo một Database mới có tên: `ictu_tower`.
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

## 📡 DANH SÁCH API CHÍNH (ENDPOINTS)

| Phương Thức | Endpoint | Chức Năng |
| :---: | :--- | :--- |
| `GET` | `/api/v1/db/status` | Kiểm tra trạng thái kết nối PostgreSQL & số lượng bản ghi các bảng |
| `GET` | `/api/v1/data/all` | Lấy toàn bộ dữ liệu 8 bảng phục vụ hiển thị trên giao diện |
| `POST` | `/api/v1/data/sync` | Đồng bộ lưu dữ liệu từ giao diện vào CSDL PostgreSQL |
| `POST` | `/api/v1/db/reseed` | Khôi phục lại bộ dữ liệu mẫu ban đầu |
| `GET` | `/api/v1/ai/health` | Kiểm tra kết nối và trạng thái hoạt động của Gemini API Key |
| `POST` | `/api/v1/ai/summarize-contract` | AI tóm tắt, phân tích và trích xuất điều khoản hợp đồng |
| `POST` | `/api/v1/ai/generate-notice` | AI tự động soạn thảo thông báo theo sắc thái và ngữ cảnh |
| `POST` | `/api/v1/ai/chat` | Trợ lý Chatbot hỏi đáp thông minh với dữ liệu ngữ cảnh tòa nhà & Vector RAG |
| `GET` | `/api/v1/ai/rag/status` | Kiểm tra trạng thái Vector Database & không gian vector RAG |
| `POST` | `/api/v1/ai/rag/search` | Tìm kiếm vector tương đồng (Cosine Similarity) trong văn bản quy chế |

---

## 🔐 BẢO MẬT & LƯU Ý KHI TRIỂN KHAI

- Không bao giờ commit file `.env` chứa API Key hoặc thông tin tài khoản Database lên GitHub. File `.gitignore` đã được cấu hình mặc định để bảo vệ file này.
- API Key Gemini hỗ trợ cả định dạng **Standard key** (`AIzaSy...`) và **Auth key mới** (`AQ...`).
- Nếu PostgreSQL đổi mật khẩu hoặc cổng port khác `5432`, chỉ cần cập nhật lại giá trị `DATABASE_URL` tương ứng trong file `.env`.

---

## 👥 THÔNG TIN ĐỒ ÁN & BẢN QUYỀN

- **Đơn vị đào tạo**: Trường Đại học Công nghệ Thông tin và Truyền thông - Đại học Thái Nguyên (ICTU)
- **Học phần**: Ứng dụng trí tuệ nhân tạo (AIA331)
- **Mã số đề tài**: **80278**
- **Đề tài**: **Hệ thống quản lý thuê căn hộ có tích hợp AI**
- **Repository**: [https://github.com/dtc235210007-cmd/CanHoChoThue](https://github.com/dtc235210007-cmd/CanHoChoThue)

---

<div align="center">
  <sub>Đồ án học phần Ứng dụng trí tuệ nhân tạo (AIA331) • ICTU 2026</sub>
</div>
