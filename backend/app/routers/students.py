from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.user_service import get_or_create_user
from app.services.student_service import (
    list_students,
    create_student,
    update_student,
    delete_student,
    activate_student,
)
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=list[StudentResponse])
async def get_students(
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    students = await list_students(db, user.id)
    return [StudentResponse.model_validate(s) for s in students]


@router.post("", response_model=StudentResponse)
async def add_student(
    body: StudentCreate,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    student = await create_student(db, user.id, body.name, body.grade, body.avatar_tag)
    return StudentResponse.model_validate(student)


@router.put("/{student_id}", response_model=StudentResponse)
async def edit_student(
    student_id: int,
    body: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    student = await update_student(
        db, student_id, user.id,
        name=body.name, grade=body.grade, avatar_tag=body.avatar_tag,
    )
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    return StudentResponse.model_validate(student)


@router.delete("/{student_id}")
async def remove_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    ok = await delete_student(db, student_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="学生不存在")
    return {"ok": True}


@router.post("/{student_id}/activate", response_model=StudentResponse)
async def set_active_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    student = await activate_student(db, student_id, user.id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    return StudentResponse.model_validate(student)
