from fastapi import Header, HTTPException
from app.services.auth_service import verify_token


def get_verified_user_id(authorization: str = Header(None)) -> int | None:
    """
    可选 JWT 鉴权：
    - 有 Bearer token 且有效 → 返回 user_id
    - 有 token 但无效/过期   → 401
    - 无 token               → 返回 None（匿名访问）
    """
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证格式")
    token = authorization[7:]
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token 已过期或无效，请重新登录")
    return user_id


def require_user_id(authorization: str = Header(None)) -> int:
    """强制要求登录，未登录直接 401"""
    user_id = get_verified_user_id(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user_id
