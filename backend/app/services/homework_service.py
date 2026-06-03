import json
import base64
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.homework import Homework
from app.models.mistake import Mistake
from app.services.ai_service import grade_homework


async def process_homework(
    db: AsyncSession,
    user_id: int,
    subject: str,
    grade: int,
    file_path: str,
) -> dict:
    with open(file_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    homework = Homework(
        user_id=user_id,
        subject=subject,
        image_url=file_path,
        status="grading",
    )
    db.add(homework)
    await db.commit()
    await db.refresh(homework)

    try:
        result = await grade_homework(image_base64, subject, grade)

        mistake_count = 0
        for q in result.get("questions", []):
            if not q.get("is_correct", False):
                mistake_count += 1
                mistake = Mistake(
                    user_id=user_id,
                    homework_id=homework.id,
                    subject=subject,
                    question_text=q.get("question_text", ""),
                    correct_answer=q.get("correct_answer", ""),
                    student_answer=q.get("student_answer", ""),
                    explanation=q.get("explanation", ""),
                    topic=q.get("topic", ""),
                    mastery=0,
                    next_review=datetime.now(),
                )
                db.add(mistake)

        homework.status = "done"
        homework.result_json = json.dumps(result, ensure_ascii=False)
        await db.commit()

        result["homework_id"] = homework.id
        result["mistake_count"] = mistake_count
        if "encouragement" not in result:
            result["encouragement"] = "继续加油！"
        return result

    except Exception as e:
        homework.status = "failed"
        await db.commit()
        return {
            "homework_id": homework.id,
            "status": "failed",
            "questions": [],
            "summary": f"批改出错：{str(e)}",
            "score": None,
            "encouragement": "出了一点小问题，请重新试试哦！",
            "mistake_count": 0,
        }
