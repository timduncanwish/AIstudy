from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.student import Student


async def list_students(db: AsyncSession, user_id: int) -> list[Student]:
    result = await db.execute(
        select(Student).where(Student.user_id == user_id).order_by(Student.created_at)
    )
    return list(result.scalars().all())


async def create_student(db: AsyncSession, user_id: int, name: str, grade: int = 3, avatar_tag: str = "👦") -> Student:
    students = await list_students(db, user_id)
    is_first = len(students) == 0

    student = Student(
        user_id=user_id,
        name=name,
        grade=grade,
        avatar_tag=avatar_tag,
        is_active=is_first,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


async def update_student(db: AsyncSession, student_id: int, user_id: int, **kwargs) -> Student | None:
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.user_id == user_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        return None

    for key, value in kwargs.items():
        if value is not None and hasattr(student, key):
            setattr(student, key, value)
    await db.commit()
    await db.refresh(student)
    return student


async def delete_student(db: AsyncSession, student_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.user_id == user_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        return False

    was_active = student.is_active
    await db.delete(student)
    await db.commit()

    if was_active:
        result = await db.execute(
            select(Student).where(Student.user_id == user_id).order_by(Student.created_at).limit(1)
        )
        next_student = result.scalar_one_or_none()
        if next_student:
            next_student.is_active = True
            await db.commit()

    return True


async def activate_student(db: AsyncSession, student_id: int, user_id: int) -> Student | None:
    result = await db.execute(
        select(Student).where(Student.user_id == user_id, Student.is_active == True)
    )
    current = result.scalar_one_or_none()
    if current:
        current.is_active = False

    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.user_id == user_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        return None

    student.is_active = True
    await db.commit()
    await db.refresh(student)
    return student


async def get_active_student(db: AsyncSession, user_id: int) -> Student | None:
    result = await db.execute(
        select(Student).where(Student.user_id == user_id, Student.is_active == True)
    )
    return result.scalar_one_or_none()
