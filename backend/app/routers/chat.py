from fastapi import APIRouter, HTTPException

from app.config import ZHIPU_API_KEY
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import chat as ai_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if req.grade < 3 or req.grade > 6:
        raise HTTPException(status_code=400, detail="年级范围为3-6年级")
    if req.subject not in ("chinese", "english"):
        raise HTTPException(status_code=400, detail="科目仅支持 chinese 或 english")
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="AI服务未配置，请在 .env 文件中设置 ZHIPU_API_KEY",
        )

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    try:
        reply = await ai_chat(messages, req.subject, req.grade)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {str(e)}")

    return ChatResponse(reply=reply, subject=req.subject)
