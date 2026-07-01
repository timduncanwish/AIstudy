from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_user_id
from app.services.student_service import (
    list_students,
    create_student,
    update_student,
    delete_student,
    activate_student,
)
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse

router = APIRouter(prefix="/students", tags=["students"])

# 孩子档案含姓名/年级等儿童个人信息，强制要求已登录（有效 JWT），不再接受
# 客户端自报的 X-User-Id 头兜底——那种匿名回退只要知道/猜到对方的 X-User-Id
# 字符串就能冒充对方，参见 tests/test_students_router_authz.py。


@router.get("", response_model=list[StudentResponse])
async def get_students(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    students = await list_students(db, user_id)
    return [StudentResponse.model_validate(s) for s in students]


@router.post("", response_model=StudentResponse)
async def add_student(
    body: StudentCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    student = await create_student(db, user_id, body.name, body.grade, body.avatar_tag)
    return StudentResponse.model_validate(student)


@router.put("/{student_id}", response_model=StudentResponse)
async def edit_student(
    student_id: int,
    body: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    student = await update_student(
        db, student_id, user_id,
        name=body.name, grade=body.grade, avatar_tag=body.avatar_tag,
    )
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    return StudentResponse.model_validate(student)


@router.delete("/{student_id}")
async def remove_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    ok = await delete_student(db, student_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="学生不存在")
    return {"ok": True}


@router.post("/{student_id}/activate", response_model=StudentResponse)
async def set_active_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_user_id),
):
    student = await activate_student(db, student_id, user_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    return StudentResponse.model_validate(student)
