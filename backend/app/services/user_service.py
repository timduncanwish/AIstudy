from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User


async def get_or_create_user(db: AsyncSession, device_id: str, grade: int = 3) -> User:
    result = await db.execute(select(User).where(User.device_id == device_id))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(device_id=device_id, grade=grade)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
