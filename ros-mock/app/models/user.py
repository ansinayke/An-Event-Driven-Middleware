import uuid
from sqlalchemy import Column, String, Enum as PgEnum
from app.db.database import Base
import enum


class RoleEnum(str, enum.Enum):
    CLIENT = "CLIENT"
    DRIVER = "DRIVER"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(PgEnum(RoleEnum), nullable=False, default=RoleEnum.CLIENT)
