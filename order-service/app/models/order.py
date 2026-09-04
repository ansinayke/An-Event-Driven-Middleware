import uuid
import enum
from sqlalchemy import Column, String, Enum as PgEnum, Text, func, DateTime
from app.db.database import Base


class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    CMS_CONFIRMED = "CMS_CONFIRMED"
    PACKAGE_REGISTERED = "PACKAGE_REGISTERED"
    ROUTE_ASSIGNED = "ROUTE_ASSIGNED"
    DRIVER_UNAVAILABLE = "DRIVER_UNAVAILABLE"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, nullable=False)
    driver_id = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    destination = Column(String, nullable=False)
    status = Column(PgEnum(OrderStatus), nullable=False, default=OrderStatus.CREATED)
    failed_reason = Column(Text, nullable=True)
    digital_signature_url = Column(String, nullable=True)
    pod_image_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())