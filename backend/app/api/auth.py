from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# In-memory user store for local accounts.
registered_users: dict[str, dict] = {}


class LoginRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)


def _resolve_user(username: str, password: str):
    if username == "admin" and password == "123456":
        return {"username": "admin", "role": "admin"}

    user = registered_users.get(username)
    if user and user.get("password") == password:
        return {"username": username, "role": "user"}

    return None


@router.post("/login")
def login(req: LoginRequest):
    user = _resolve_user(req.username.strip(), req.password)
    if not user:
        raise HTTPException(status_code=401, detail="账号或密码错误")

    return {
        "access_token": f"demo-token-{user['username']}",
        "token_type": "bearer",
        "user": user,
    }


@router.post("/register")
def register(req: RegisterRequest):
    username = req.username.strip()
    if username == "admin":
        raise HTTPException(status_code=400, detail="admin 为系统保留账号")

    if username in registered_users:
        raise HTTPException(status_code=400, detail="该账号已存在")

    registered_users[username] = {"password": req.password}
    return {"status": "success", "message": "注册成功，请登录"}
