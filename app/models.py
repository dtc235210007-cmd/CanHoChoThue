"""SQLAlchemy Models cho toàn bộ hệ thống quản lý căn hộ ICTU Tower.
Bao gồm: Rooms, Tenants, Contracts, Maintenance, Services, Vehicles, Cashflow, AuditLogs.
"""

from sqlalchemy import Column, Integer, String, Float, Text
from app.database import Base


class RoomModel(Base):
    __tablename__ = "rooms"

    room = Column(String(20), primary_key=True, index=True)
    model_type = Column(String(100), nullable=False)
    tenant = Column(String(150), default="(Chưa có khách)")
    price = Column(String(50), default="0")
    area = Column(Float, default=0.0)
    date = Column(String(50), default="--")
    status = Column(String(20), default="empty")  # paid | debt | empty | maint
    image = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "room": self.room,
            "modelType": self.model_type,
            "tenant": self.tenant,
            "price": self.price,
            "area": self.area,
            "date": self.date,
            "status": self.status,
            "image": self.image,
        }


class TenantModel(Base):
    __tablename__ = "tenants"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(150), nullable=True)
    id_card = Column(String(50), nullable=True)
    room = Column(String(50), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "idCard": self.id_card,
            "room": self.room,
        }


class ContractModel(Base):
    __tablename__ = "contracts"

    id = Column(String(50), primary_key=True, index=True)
    room = Column(String(50), nullable=False)
    tenant = Column(String(150), nullable=False)
    start = Column(String(50), nullable=False)
    end = Column(String(50), nullable=False)
    deposit = Column(String(50), default="0")
    status = Column(String(50), default="Hiệu lực")

    def to_dict(self):
        return {
            "id": self.id,
            "room": self.room,
            "tenant": self.tenant,
            "start": self.start,
            "end": self.end,
            "deposit": self.deposit,
            "status": self.status,
        }


class MaintenanceModel(Base):
    __tablename__ = "maintenance"

    id = Column(String(50), primary_key=True, index=True)
    room = Column(String(50), nullable=False)
    desc = Column(Text, nullable=False)
    date = Column(String(50), nullable=False)
    priority = Column(String(50), default="Bình thường")
    status = Column(String(50), default="Chờ xử lý")

    def to_dict(self):
        return {
            "id": self.id,
            "room": self.room,
            "desc": self.desc,
            "date": self.date,
            "priority": self.priority,
            "status": self.status,
        }


class ServiceModel(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room = Column(String(50), nullable=False, unique=True, index=True)
    tenant = Column(String(150), nullable=False)
    old_elec = Column(Float, default=0)
    new_elec = Column(Float, default=0)
    old_water = Column(Float, default=0)
    new_water = Column(Float, default=0)
    bikes = Column(Integer, default=0)
    cars = Column(Integer, default=0)
    manage_fee = Column(Float, default=0)
    trash_fee = Column(Float, default=0)

    def to_dict(self):
        return {
            "room": self.room,
            "tenant": self.tenant,
            "oldElec": self.old_elec,
            "newElec": self.new_elec,
            "oldWater": self.old_water,
            "newWater": self.new_water,
            "bikes": self.bikes,
            "cars": self.cars,
            "manageFee": self.manage_fee,
            "trashFee": self.trash_fee,
        }


class VehicleModel(Base):
    __tablename__ = "vehicles"

    card_id = Column(String(50), primary_key=True, index=True)
    room = Column(String(50), nullable=False)
    resident = Column(String(150), nullable=False)
    card_type = Column(String(100), default="Thẻ Thang Máy & Bãi Xe")
    vehicle_type = Column(String(50), default="Xe Máy")
    plate = Column(String(50), default="")
    brand = Column(String(100), default="")
    issue_date = Column(String(50), default="")
    status = Column(String(50), default="active")

    def to_dict(self):
        return {
            "cardId": self.card_id,
            "room": self.room,
            "resident": self.resident,
            "cardType": self.card_type,
            "vehicleType": self.vehicle_type,
            "plate": self.plate,
            "brand": self.brand,
            "issueDate": self.issue_date,
            "status": self.status,
        }


class CashflowModel(Base):
    __tablename__ = "cashflow"

    id = Column(String(50), primary_key=True, index=True)
    date = Column(String(50), nullable=False)
    type = Column(String(50), nullable=False)  # income | expense
    category = Column(String(150), nullable=False)
    partner = Column(String(150), nullable=False)
    amount = Column(Float, default=0.0)
    actor = Column(String(100), default="Kế Toán")

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "type": self.type,
            "category": self.category,
            "partner": self.partner,
            "amount": self.amount,
            "actor": self.actor,
        }


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(String(100), nullable=False)
    user = Column(String(100), nullable=False)
    action = Column(String(200), nullable=False)
    detail = Column(Text, default="")

    def to_dict(self):
        return {
            "time": self.time,
            "user": self.user,
            "action": self.action,
            "detail": self.detail,
        }
