from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.user import create_user, verify_password
from app.middleware.auth import create_token, require_auth
from fastapi import Request, Depends

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(body: RegisterRequest):
    if len(body.username) < 3 or len(body.password) < 6:
        raise HTTPException(status_code=400, detail={"error": "VALIDATION", "message": "Username >= 3 chars, password >= 6 chars"})
    user = await create_user(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=409, detail={"error": "CONFLICT", "message": "Username already exists"})
    token = create_token(user["id"], user["username"])
    return {"token": token, "user": user}


@router.post("/login")
async def login(body: LoginRequest):
    user = await verify_password(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail={"error": "INVALID_CREDENTIALS", "message": "Invalid username or password"})
    token = create_token(user["id"], user["username"])
    return {"token": token, "user": user}


@router.get("/check")
async def check(request: Request, _payload: dict = Depends(require_auth)):
    return {"user_id": request.state.user_id, "username": request.state.username}
