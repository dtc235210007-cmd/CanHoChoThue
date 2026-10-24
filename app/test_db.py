"""Script kiểm tra kết nối PostgreSQL và khởi tạo bảng.
Chạy: python app/test_db.py
"""

import sys
import os

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import sqlalchemy
    import psycopg2
    print("[OK] Đã tìm thấy thư viện sqlalchemy và psycopg2!")
except ImportError as e:
    print(f"[THIẾU THƯ VIỆN] {e}")
    print("Vui lòng chạy lệnh sau trong terminal:")
    print("pip install sqlalchemy psycopg2-binary")
    sys.exit(1)

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

print(f"[Đang kết nối] Kiểm tra kết nối tới PostgreSQL...")
try:
    success = init_and_seed_db()
    if success:
        db = SessionLocal()
        print("\n=== THỐNG KÊ BẢNG TRONG DATABASE ICTU_TOWER ===")
        print(f"1. Căn hộ (rooms): {db.query(RoomModel).count()} bản ghi")
        print(f"2. Cư dân (tenants): {db.query(TenantModel).count()} bản ghi")
        print(f"3. Hợp đồng (contracts): {db.query(ContractModel).count()} bản ghi")
        print(f"4. Bảo trì (maintenance): {db.query(MaintenanceModel).count()} bản ghi")
        print(f"5. Dịch vụ (services): {db.query(ServiceModel).count()} bản ghi")
        print(f"6. Thẻ xe (vehicles): {db.query(VehicleModel).count()} bản ghi")
        print(f"7. Sổ quỹ (cashflow): {db.query(CashflowModel).count()} bản ghi")
        print(f"8. Nhật ký (audit_logs): {db.query(AuditLogModel).count()} bản ghi")
        print("=================================================")
        print("Tất cả bảng và dữ liệu đã sẵn sàng trên pgAdmin!")
        db.close()
    else:
        print("[LỖI] Không thể kết nối hoặc khởi tạo dữ liệu.")
except Exception as err:
    print(f"[LỖI KẾT NỐI] {err}")
