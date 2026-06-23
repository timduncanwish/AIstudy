import json
import uuid

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.limiter import limiter

from app.config import ZHIPU_API_KEY
from app.database import get_db
from app.deps import get_verified_user_id
from app.models.chat_history import ChatHistory
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatHistoryMessage,
    ChatSessionListResponse,
    ChatSessionSummary,
)
from app.services.ai_service import chat as ai_chat, chat_stream as ai_chat_stream
from app.services.mistake_service import get_relevant_mistakes
from app.scope import active_student_id

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat_endpoint(
    request: Request,
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    verified_uid: int | None = Depends(get_verified_user_id),
):
    if req.grade < 3 or req.grade > 6:
        raise HTTPException(status_code=400, detail="年级范围为3-6年级")
    if req.subject not in ("chinese", "english"):
        raise HTTPException(status_code=400, detail="科目仅支持 chinese 或 english")
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="AI服务未配置，请在 .env 文件中设置 ZHIPU_API_KEY",
        )

    # token 有效时以 token 中的 user_id 为准，防止客户端伪造
    effective_user_id = verified_uid or req.user_id

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    mistakes_context = None
    mistakes_referenced = 0
    if effective_user_id:
        relevant = await get_relevant_mistakes(db, effective_user_id, req.subject)
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
    if effective_user_id and req.session_id:
        sid = await active_student_id(db, effective_user_id)
        user_msg = req.messages[-1] if req.messages else None
        if user_msg and user_msg.role == "user":
            db.add(ChatHistory(
                user_id=effective_user_id,
                student_id=sid,
                session_id=req.session_id,
                subject=req.subject,
                grade=req.grade,
                role="user",
                content=user_msg.content,
            ))
        db.add(ChatHistory(
            user_id=effective_user_id,
            student_id=sid,
            session_id=req.session_id,
            subject=req.subject,
            grade=req.grade,
            role="assistant",
            content=reply,
        ))
        await db.commit()

    return ChatResponse(reply=reply, subject=req.subject, mistakes_referenced=mistakes_referenced)


@router.post("/stream")
@limiter.limit("30/minute")
async def chat_stream_endpoint(
    request: Request,
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    verified_uid: int | None = Depends(get_verified_user_id),
):
    if req.grade < 3 or req.grade > 6:
        raise HTTPException(status_code=400, detail="年级范围为3-6年级")
    if req.subject not in ("chinese", "english"):
        raise HTTPException(status_code=400, detail="科目仅支持 chinese 或 english")
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_api_key_here":
        raise HTTPException(status_code=503, detail="AI服务未配置")

    effective_user_id = verified_uid or req.user_id

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    mistakes_context = None
    mistakes_referenced = 0
    if effective_user_id:
        relevant = await get_relevant_mistakes(db, effective_user_id, req.subject)
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

    async def generate():
        full_reply = []
        try:
            async for chunk in ai_chat_stream(messages, req.subject, req.grade, mistakes_context):
                full_reply.append(chunk)
                yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        reply = "".join(full_reply)
        yield f"data: {json.dumps({'done': True, 'mistakes_referenced': mistakes_referenced}, ensure_ascii=False)}\n\n"

        if effective_user_id and req.session_id and reply:
            sid = await active_student_id(db, effective_user_id)
            user_msg = req.messages[-1] if req.messages else None
            if user_msg and user_msg.role == "user":
                db.add(ChatHistory(
                    user_id=effective_user_id,
                    student_id=sid,
                    session_id=req.session_id,
                    subject=req.subject,
                    grade=req.grade,
                    role="user",
                    content=user_msg.content,
                ))
            db.add(ChatHistory(
                user_id=effective_user_id,
                student_id=sid,
                session_id=req.session_id,
                subject=req.subject,
                grade=req.grade,
                role="assistant",
                content=reply,
            ))
            await db.commit()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions/{user_id}", response_model=ChatSessionListResponse)
async def list_sessions(user_id: int, db: AsyncSession = Depends(get_db)):
    """获取当前活跃孩子的对话会话列表"""
    sid = await active_student_id(db, user_id)
    student_conds = [ChatHistory.student_id == sid] if sid is not None else []
    subq = (
        select(
            ChatHistory.session_id,
            ChatHistory.subject,
            ChatHistory.grade,
            sa_func.count(ChatHistory.id).label("msg_count"),
            sa_func.max(ChatHistory.created_at).label("last_time"),
        )
        .where(ChatHistory.user_id == user_id, *student_conds)
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
    sid = await active_student_id(db, user_id)
    student_conds = [ChatHistory.student_id == sid] if sid is not None else []
    stmt = (
        select(ChatHistory)
        .where(ChatHistory.user_id == user_id, *student_conds, ChatHistory.session_id == session_id)
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
