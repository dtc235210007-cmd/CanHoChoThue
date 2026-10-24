"""Dữ liệu mẫu ban đầu và hàm khởi tạo / seed dữ liệu tự động vào PostgreSQL.
"""

from app.database import engine, SessionLocal, Base
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

BUILDING_FLOORPLANS = {
    "studio": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&q=80",
    "oneBedStd": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=600&q=80",
    "oneBedPlus": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=600&q=80",
    "twoBedDeluxe": "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=600&q=80",
    "twoBedCorner": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=600&q=80",
    "twoBedPanorama": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=600&q=80",
}

INITIAL_ROOMS = [
    {"room": "A101", "model_type": "2PN Căn Góc", "tenant": "Nguyễn Văn An", "price": "8.500.000", "area": 75, "date": "05/09/2026", "status": "debt", "image": BUILDING_FLOORPLANS["twoBedCorner"]},
    {"room": "A102", "model_type": "2PN Deluxe", "tenant": "Trần Thị Bích", "price": "10.000.000", "area": 72, "date": "01/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["twoBedDeluxe"]},
    {"room": "A103", "model_type": "Studio", "tenant": "(Chưa có khách)", "price": "7.500.000", "area": 48, "date": "--", "status": "empty", "image": BUILDING_FLOORPLANS["studio"]},
    {"room": "A104", "model_type": "1PN+ Ban Công", "tenant": "Lê Văn Cường", "price": "9.000.000", "area": 65, "date": "02/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["oneBedPlus"]},
    {"room": "A105", "model_type": "1PN Standard", "tenant": "Phạm Quỳnh Nga", "price": "8.000.000", "area": 55, "date": "05/09/2026", "status": "debt", "image": BUILDING_FLOORPLANS["oneBedStd"]},
    {"room": "A106", "model_type": "2PN Panorama", "tenant": "Đỗ Minh Đức", "price": "8.500.000", "area": 68, "date": "01/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["twoBedPanorama"]},
    {"room": "A201", "model_type": "2PN Căn Góc", "tenant": "Hoàng Thùy Linh", "price": "11.000.000", "area": 85, "date": "03/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["twoBedCorner"]},
    {"room": "A202", "model_type": "2PN Deluxe", "tenant": "Vũ Trọng Phụng", "price": "9.500.000", "area": 70, "date": "05/09/2026", "status": "debt", "image": BUILDING_FLOORPLANS["twoBedDeluxe"]},
    {"room": "A203", "model_type": "Studio", "tenant": "(Bảo trì vòi nước)", "price": "8.000.000", "area": 48, "date": "--", "status": "maint", "image": BUILDING_FLOORPLANS["studio"]},
    {"room": "A204", "model_type": "1PN+ Ban Công", "tenant": "Ngô Bảo Châu", "price": "12.000.000", "area": 65, "date": "01/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["oneBedPlus"]},
    {"room": "A205", "model_type": "1PN Standard", "tenant": "Bùi Tiến Dũng", "price": "9.000.000", "area": 55, "date": "02/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["oneBedStd"]},
    {"room": "A206", "model_type": "2PN Panorama", "tenant": "(Chưa có khách)", "price": "7.500.000", "area": 68, "date": "--", "status": "empty", "image": BUILDING_FLOORPLANS["twoBedPanorama"]},
    {"room": "A301", "model_type": "2PN Căn Góc", "tenant": "Đặng Thu Thảo", "price": "10.500.000", "area": 85, "date": "01/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["twoBedCorner"]},
    {"room": "A302", "model_type": "2PN Deluxe", "tenant": "Chu Đăng Khoa", "price": "11.500.000", "area": 75, "date": "05/09/2026", "status": "debt", "image": BUILDING_FLOORPLANS["twoBedDeluxe"]},
    {"room": "A303", "model_type": "Studio", "tenant": "(Chưa có khách)", "price": "8.000.000", "area": 50, "date": "--", "status": "empty", "image": BUILDING_FLOORPLANS["studio"]},
    {"room": "A304", "model_type": "1PN+ Ban Công", "tenant": "Phan Mạnh Quỳnh", "price": "9.500.000", "area": 66, "date": "04/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["oneBedPlus"]},
    {"room": "A305", "model_type": "1PN Standard", "tenant": "Mai Phương Thúy", "price": "12.500.000", "area": 58, "date": "01/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["oneBedStd"]},
    {"room": "A306", "model_type": "2PN Panorama", "tenant": "Lâm Khánh Chi", "price": "8.500.000", "area": 70, "date": "03/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["twoBedPanorama"]},
    {"room": "B101", "model_type": "Studio", "tenant": "Trịnh Thăng Bình", "price": "7.000.000", "area": 45, "date": "02/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["studio"]},
    {"room": "B102", "model_type": "Studio", "tenant": "(Chưa có khách)", "price": "6.500.000", "area": 45, "date": "--", "status": "empty", "image": BUILDING_FLOORPLANS["studio"]},
    {"room": "B103", "model_type": "1PN Standard", "tenant": "Dương Triệu Vũ", "price": "7.500.000", "area": 52, "date": "05/09/2026", "status": "debt", "image": BUILDING_FLOORPLANS["oneBedStd"]},
    {"room": "B104", "model_type": "1PN+ Ban Công", "tenant": "Nguyễn Cao Kỳ Duyên", "price": "9.000.000", "area": 62, "date": "01/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["oneBedPlus"]},
    {"room": "B105", "model_type": "Studio", "tenant": "(Hỏng điều hòa)", "price": "7.000.000", "area": 48, "date": "--", "status": "maint", "image": BUILDING_FLOORPLANS["studio"]},
    {"room": "B106", "model_type": "1PN Standard", "tenant": "Hồ Quang Hiếu", "price": "6.800.000", "area": 50, "date": "02/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["oneBedStd"]},
    {"room": "B201", "model_type": "2PN Deluxe", "tenant": "Châu Bùi", "price": "10.000.000", "area": 74, "date": "01/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["twoBedDeluxe"]},
    {"room": "B202", "model_type": "1PN Standard", "tenant": "Nguyễn Hoàng Đức", "price": "8.200.000", "area": 56, "date": "04/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["oneBedStd"]},
    {"room": "B203", "model_type": "Studio", "tenant": "(Chưa có khách)", "price": "6.500.000", "area": 45, "date": "--", "status": "empty", "image": BUILDING_FLOORPLANS["studio"]},
    {"room": "B204", "model_type": "1PN+ Ban Công", "tenant": "Đoàn Văn Hậu", "price": "9.000.000", "area": 65, "date": "01/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["oneBedPlus"]},
    {"room": "B205", "model_type": "Studio", "tenant": "Lê Hoàng Chinh", "price": "6.200.000", "area": 46, "date": "05/09/2026", "status": "debt", "image": BUILDING_FLOORPLANS["studio"]},
    {"room": "B206", "model_type": "2PN Panorama", "tenant": "Đinh Thanh Bình", "price": "8.000.000", "area": 68, "date": "02/09/2026", "status": "paid", "image": BUILDING_FLOORPLANS["twoBedPanorama"]},
]

INITIAL_TENANTS = [
    {"id": "KH-01", "name": "Nguyễn Văn An", "phone": "0912 345 678", "email": "an.nguyen@gmail.com", "id_card": "034195001234", "room": "A101"},
    {"id": "KH-02", "name": "Trần Thị Bích", "phone": "0988 765 432", "email": "bich.tran@gmail.com", "id_card": "034195005678", "room": "A102"},
    {"id": "KH-03", "name": "Lê Văn Cường", "phone": "0903 111 222", "email": "cuong.le@gmail.com", "id_card": "034195009999", "room": "A104"},
    {"id": "KH-04", "name": "Phạm Quỳnh Nga", "phone": "0934 888 777", "email": "nga.pham@gmail.com", "id_card": "034195004321", "room": "A105"},
    {"id": "KH-05", "name": "Đỗ Minh Đức", "phone": "0977 555 444", "email": "duc.do@gmail.com", "id_card": "034195008765", "room": "A106"},
    {"id": "KH-06", "name": "Hoàng Thùy Linh", "phone": "0918 222 333", "email": "linh.hoang@gmail.com", "id_card": "034195001122", "room": "A201"},
]

INITIAL_CONTRACTS = [
    {"id": "HD-2026-001", "room": "A101", "tenant": "Nguyễn Văn An", "start": "2026-01-01", "end": "2026-12-31", "deposit": "17.000.000", "status": "Hiệu lực"},
    {"id": "HD-2026-002", "room": "A102", "tenant": "Trần Thị Bích", "start": "2025-09-01", "end": "2026-09-30", "deposit": "20.000.000", "status": "Sắp hết hạn"},
    {"id": "HD-2026-003", "room": "A104", "tenant": "Lê Văn Cường", "start": "2026-03-01", "end": "2027-02-28", "deposit": "18.000.000", "status": "Hiệu lực"},
    {"id": "HD-2026-004", "room": "A105", "tenant": "Phạm Quỳnh Nga", "start": "2025-10-01", "end": "2026-10-01", "deposit": "16.000.000", "status": "Sắp hết hạn"},
    {"id": "HD-2026-005", "room": "A201", "tenant": "Hoàng Thùy Linh", "start": "2026-04-01", "end": "2027-03-31", "deposit": "22.000.000", "status": "Hiệu lực"},
]

INITIAL_MAINTENANCE = [
    {"id": "BT-101", "room": "A203", "desc": "Rò rỉ vòi nước lavabo", "date": "03/09/2026", "priority": "Bình thường", "status": "Đang xử lý"},
    {"id": "BT-102", "room": "B105", "desc": "Hỏng bo mạch điều hòa", "date": "04/09/2026", "priority": "Khẩn cấp", "status": "Chờ xử lý"},
]

INITIAL_SERVICES = [
    {"room": "A101", "tenant": "Nguyễn Văn An", "old_elec": 1240, "new_elec": 1410, "old_water": 85, "new_water": 97, "bikes": 2, "cars": 0, "manage_fee": 1125000, "trash_fee": 120000},
    {"room": "A102", "tenant": "Trần Thị Bích", "old_elec": 2100, "new_elec": 2320, "old_water": 140, "new_water": 156, "bikes": 1, "cars": 1, "manage_fee": 1080000, "trash_fee": 120000},
    {"room": "A104", "tenant": "Lê Văn Cường", "old_elec": 980, "new_elec": 1135, "old_water": 60, "new_water": 72, "bikes": 2, "cars": 0, "manage_fee": 975000, "trash_fee": 120000},
    {"room": "A105", "tenant": "Phạm Quỳnh Nga", "old_elec": 1520, "new_elec": 1690, "old_water": 110, "new_water": 124, "bikes": 1, "cars": 0, "manage_fee": 825000, "trash_fee": 120000},
    {"room": "A106", "tenant": "Đỗ Minh Đức", "old_elec": 1750, "new_elec": 1940, "old_water": 95, "new_water": 108, "bikes": 2, "cars": 0, "manage_fee": 1020000, "trash_fee": 120000},
    {"room": "A201", "tenant": "Hoàng Thùy Linh", "old_elec": 3200, "new_elec": 3480, "old_water": 210, "new_water": 230, "bikes": 1, "cars": 1, "manage_fee": 1275000, "trash_fee": 120000},
]

INITIAL_VEHICLES = [
    {"card_id": "RFID-101A", "room": "A101", "resident": "Nguyễn Văn An", "card_type": "Thẻ Thang Máy & Bãi Xe", "vehicle_type": "Xe Máy", "plate": "29E1-886.99", "brand": "Honda SH 150i", "issue_date": "01/01/2026", "status": "active"},
    {"card_id": "RFID-101B", "room": "A101", "resident": "Nguyễn Văn An", "card_type": "Thẻ Bãi Đỗ Xe", "vehicle_type": "Xe Máy", "plate": "29B1-123.45", "brand": "Yamaha Grande", "issue_date": "15/01/2026", "status": "active"},
    {"card_id": "RFID-102A", "room": "A102", "resident": "Trần Thị Bích", "card_type": "Thẻ Thang Máy & Bãi Xe", "vehicle_type": "Ô Tô", "plate": "30H-998.68", "brand": "Mazda CX-5 Trắng", "issue_date": "01/09/2025", "status": "active"},
    {"card_id": "RFID-104A", "room": "A104", "resident": "Lê Văn Cường", "card_type": "Thẻ Thang Máy & Bãi Xe", "vehicle_type": "Xe Máy", "plate": "29D2-678.90", "brand": "Honda AirBlade", "issue_date": "01/03/2026", "status": "active"},
    {"card_id": "RFID-105A", "room": "A105", "resident": "Phạm Quỳnh Nga", "card_type": "Thẻ Thang Máy", "vehicle_type": "Xe Máy", "plate": "98B3-555.66", "brand": "VinFast Feliz S", "issue_date": "01/10/2025", "status": "active"},
    {"card_id": "RFID-201A", "room": "A201", "resident": "Hoàng Thùy Linh", "card_type": "Thẻ Thang Máy & Bãi Xe", "vehicle_type": "Ô Tô", "plate": "30A-686.88", "brand": "Mercedes C200 Đen", "issue_date": "01/04/2026", "status": "active"},
]

INITIAL_CASHFLOW = [
    {"id": "PT-0901", "date": "01/09/2026", "type": "income", "category": "Tiền thuê căn hộ", "partner": "A102 (Trần Thị Bích)", "amount": 10000000.0, "actor": "Kế Toán"},
    {"id": "PT-0902", "date": "01/09/2026", "type": "income", "category": "Tiền thuê căn hộ", "partner": "A204 (Ngô Bảo Châu)", "amount": 12000000.0, "actor": "Kế Toán"},
    {"id": "PC-0901", "date": "02/09/2026", "type": "expense", "category": "Điện lưới EVN tòa nhà", "partner": "Điện Lực", "amount": 18500000.0, "actor": "Kế Toán"},
    {"id": "PC-0902", "date": "03/09/2026", "type": "expense", "category": "Bảo trì thang máy", "partner": "Schindler", "amount": 8000000.0, "actor": "Kỹ Thuật"},
    {"id": "PT-0903", "date": "04/09/2026", "type": "income", "category": "Tiền cọc hợp đồng mới", "partner": "A305 (Mai Phương Thúy)", "amount": 25000000.0, "actor": "Kế Toán"},
]

INITIAL_AUDIT_LOGS = [
    {"time": "13:45:20 18/09/2026", "user": "Kế Toán", "action": "Gạch nợ căn hộ A101", "detail": "Đã thu 8.500.000 đ qua VietQR"},
    {"time": "11:20:15 18/09/2026", "user": "Kỹ Thuật", "action": "Tiếp nhận bảo trì A203", "detail": "Rò rỉ nước lavabo"},
    {"time": "09:10:05 18/09/2026", "user": "Kỹ Thuật", "action": "Cấp thẻ từ RFID-101B", "detail": "Xe máy Yamaha Grande 29B1-123.45"},
    {"time": "08:30:00 18/09/2026", "user": "Admin", "action": "Khởi động ca trực hệ thống", "detail": "Tỷ lệ lấp đầy đạt 83.3%"},
]


def init_and_seed_db():
    """Tự động tạo bảng trong PostgreSQL và nạp dữ liệu mẫu ban đầu nếu bảng rỗng."""
    if engine is None or SessionLocal is None:
        print("[Database] Bỏ qua khởi tạo DB (chưa cài driver hoặc sai cấu hình)")
        return False

    try:
        # 1. Tạo tất cả các bảng nếu chưa có
        Base.metadata.create_all(bind=engine)
        print("[Database] Đã kiểm tra / tạo các bảng PostgreSQL thành công!")

        db = SessionLocal()
        try:
            # Seed Rooms
            if db.query(RoomModel).count() == 0:
                for r in INITIAL_ROOMS:
                    db.add(RoomModel(**r))
                print(f"[Database Seed] Đã thêm {len(INITIAL_ROOMS)} căn hộ")

            # Seed Tenants
            if db.query(TenantModel).count() == 0:
                for t in INITIAL_TENANTS:
                    db.add(TenantModel(**t))
                print(f"[Database Seed] Đã thêm {len(INITIAL_TENANTS)} cư dân")

            # Seed Contracts
            if db.query(ContractModel).count() == 0:
                for c in INITIAL_CONTRACTS:
                    db.add(ContractModel(**c))
                print(f"[Database Seed] Đã thêm {len(INITIAL_CONTRACTS)} hợp đồng")

            # Seed Maintenance
            if db.query(MaintenanceModel).count() == 0:
                for m in INITIAL_MAINTENANCE:
                    db.add(MaintenanceModel(**m))
                print(f"[Database Seed] Đã thêm {len(INITIAL_MAINTENANCE)} phiếu bảo trì")

            # Seed Services
            if db.query(ServiceModel).count() == 0:
                for s in INITIAL_SERVICES:
                    db.add(ServiceModel(**s))
                print(f"[Database Seed] Đã thêm {len(INITIAL_SERVICES)} biểu phí dịch vụ")

            # Seed Vehicles
            if db.query(VehicleModel).count() == 0:
                for v in INITIAL_VEHICLES:
                    db.add(VehicleModel(**v))
                print(f"[Database Seed] Đã thêm {len(INITIAL_VEHICLES)} thẻ xe")

            # Seed Cashflow
            if db.query(CashflowModel).count() == 0:
                for cf in INITIAL_CASHFLOW:
                    db.add(CashflowModel(**cf))
                print(f"[Database Seed] Đã thêm {len(INITIAL_CASHFLOW)} giao dịch sổ quỹ")

            # Seed Audit Logs
            if db.query(AuditLogModel).count() == 0:
                for al in INITIAL_AUDIT_LOGS:
                    db.add(AuditLogModel(**al))
                print(f"[Database Seed] Đã thêm {len(INITIAL_AUDIT_LOGS)} nhật ký thao tác")

            db.commit()
            print("[Database] Hoàn tất nạp dữ liệu mẫu vào PostgreSQL!")
            return True
        finally:
            db.close()
    except Exception as e:
        print(f"[Database Error] Lỗi khi tạo bảng hoặc seed dữ liệu: {e}")
        return False
