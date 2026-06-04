import uuid

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ZHIPU_API_KEY
from app.database import get_db
from app.models.chat_history import ChatHistory
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatHistoryMessage,
    ChatSessionListResponse,
    ChatSessionSummary,
)
from app.services.ai_service import chat as ai_chat
from app.services.mistake_service import get_relevant_mistakes

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, db: AsyncSession = Depends(get_db)):
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

    mistakes_context = None
    mistakes_referenced = 0
    if req.user_id:
        relevant = await get_relevant_mistakes(db, req.user_id, req.subject)
        if relevant:
            mistakes_context = [
                {
                    "question_text": m.question_text,
                    "student_answer": m.student_answer,
                    "correct_answer": m.correct_answer,
                    "topic": m.topic,
                    "mastery": m.mastery,
                }
                for m in relevant
            ]
            mistakes_referenced = len(relevant)

    try:
        reply = await ai_chat(messages, req.subject, req.grade, mistakes_context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {str(e)}")

    # 持久化对话记录
    if req.user_id and req.session_id:
        user_msg = req.messages[-1] if req.messages else None
        if user_msg and user_msg.role == "user":
            db.add(ChatHistory(
                user_id=req.user_id,
                session_id=req.session_id,
                subject=req.subject,
                grade=req.grade,
                role="user",
                content=user_msg.content,
            ))
        db.add(ChatHistory(
            user_id=req.user_id,
            session_id=req.session_id,
            subject=req.subject,
            grade=req.grade,
            role="assistant",
            content=reply,
        ))
        await db.commit()

    return ChatResponse(reply=reply, subject=req.subject, mistakes_referenced=mistakes_referenced)


@router.get("/sessions/{user_id}", response_model=ChatSessionListResponse)
async def list_sessions(user_id: int, db: AsyncSession = Depends(get_db)):
    """获取用户的对话会话列表"""
    subq = (
        select(
            ChatHistory.session_id,
            ChatHistory.subject,
            ChatHistory.grade,
            sa_func.count(ChatHistory.id).label("msg_count"),
            sa_func.max(ChatHistory.created_at).label("last_time"),
        )
        .where(ChatHistory.user_id == user_id)
        .group_by(ChatHistory.session_id, ChatHistory.subject, ChatHistory.grade)
        .subquery()
    )

    stmt = select(subq).order_by(subq.c.last_time.desc()).limit(50)
    result = await db.execute(stmt)
    rows = result.all()

    sessions = []
    for row in rows:
        # 获取最后一条消息
        last_msg_stmt = (
            select(ChatHistory.content)
            .where(
                ChatHistory.user_id == user_id,
                ChatHistory.session_id == row.session_id,
            )
            .order_by(ChatHistory.created_at.desc())
            .limit(1)
        )
        last_msg_result = await db.execute(last_msg_stmt)
        last_msg = last_msg_result.scalar() or ""

        sessions.append(ChatSessionSummary(
            session_id=row.session_id,
            subject=row.subject,
            grade=row.grade,
            last_message=last_msg[:100],
            message_count=row.msg_count,
            created_at=str(row.last_time),
        ))

    return ChatSessionListResponse(sessions=sessions)


@router.get("/history/{user_id}/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    user_id: int, session_id: str, db: AsyncSession = Depends(get_db)
):
    """获取指定会话的完整对话记录"""
    stmt = (
        select(ChatHistory)
        .where(ChatHistory.user_id == user_id, ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    if not records:
        raise HTTPException(status_code=404, detail="对话记录不存在")

    first = records[0]
    messages = [
        ChatHistoryMessage(
            role=r.role,
            content=r.content,
            created_at=str(r.created_at),
        )
        for r in records
    ]

    return ChatHistoryResponse(
        session_id=session_id,
        subject=first.subject,
        grade=first.grade,
        messages=messages,
    )


@router.delete("/history/{user_id}/{session_id}")
async def delete_chat_history(
    user_id: int, session_id: str, db: AsyncSession = Depends(get_db)
):
    """删除指定会话的对话记录"""
    stmt = (
        select(ChatHistory)
        .where(ChatHistory.user_id == user_id, ChatHistory.session_id == session_id)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    if not records:
        raise HTTPException(status_code=404, detail="对话记录不存在")

    for r in records:
        await db.delete(r)
    await db.commit()

    return {"detail": "删除成功"}
