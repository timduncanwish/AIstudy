import os
import uuid

from fastapi import APIRouter, UploadFile, File, Form, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.user_service import get_or_create_user
from app.services.homework_service import process_homework
from app.schemas.homework import HomeworkUploadResponse, QuestionResult

router = APIRouter(prefix="/homework", tags=["homework"])


@router.post("/upload", response_model=HomeworkUploadResponse)
async def upload_homework(
    file: UploadFile = File(...),
    subject: str = Form(...),
    grade: int = Form(...),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous", grade)

    ext = os.path.splitext(file.filename or "photo.jpg")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join("uploads", filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    result = await process_homework(db, user.id, subject, grade, file_path)

    questions = [
        QuestionResult(
            question_number=q.get("question_number", i + 1),
            question_text=q.get("question_text", ""),
            student_answer=q.get("student_answer", ""),
            correct_answer=q.get("correct_answer", ""),
            is_correct=q.get("is_correct", False),
            explanation=q.get("explanation", ""),
            topic=q.get("topic", ""),
        )
        for i, q in enumerate(result.get("questions", []))
    ]

    return HomeworkUploadResponse(
        homework_id=result.get("homework_id", 0),
        status=result.get("status", "done"),
        questions=questions,
        summary=result.get("summary", ""),
        score=result.get("score"),
        encouragement=result.get("encouragement", "继续加油！"),
        mistake_count=result.get("mistake_count", 0),
    )
