from pydantic import BaseModel, EmailStr
from enum import Enum


class RoleEnum(str, Enum):
    CLIENT = "CLIENT"
    DRIVER = "DRIVER"


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: RoleEnum = RoleEnum.CLIENT


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: RoleEnum

    class Config:
        from_attributes = True
