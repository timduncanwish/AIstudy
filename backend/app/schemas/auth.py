from pydantic import BaseModel


class LoginRequest(BaseModel):
    code: str
    nickname: str = "家长"
    avatar: str = ""


class LoginResponse(BaseModel):
    token: str
    user_id: int
    is_new_user: bool
    nickname: str
