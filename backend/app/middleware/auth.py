from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Request, HTTPException
from app.config import JWT_SECRET, JWT_ALGORITHM


def create_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


async def require_auth(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": "Missing or invalid token"})
    token = auth_header[7:]
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"error": "TOKEN_EXPIRED", "message": "Token has expired"})
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": "Invalid token"})
    request.state.user_id = payload["sub"]
    request.state.username = payload["username"]
    return payload
