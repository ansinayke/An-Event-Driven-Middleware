from datetime import datetime, timedelta
from jose import jwt
import bcrypt as b
from app.core.config import settings


def hash_password(password: str) -> str:
    print(f"Hashing password: {password} Length: {len(password)}", flush=True)  
    return b.hashpw(password.encode('utf-8'), b.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    return b.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
