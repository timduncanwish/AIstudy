"""多孩子数据隔离的作用域助手。

学习数据（错题/作业/对话/每日一练）按"当前活跃孩子"隔离。
- 用户有活跃孩子 → 返回该孩子 id，查询按 student_id 过滤
- 用户没有任何孩子 → 返回 None，退回 user 级（兼容匿名/未建档用户）
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.student_service import get_active_student


async def active_student_id(db: AsyncSession, user_id: int | None) -> int | None:
    if not user_id:
        return None
    student = await get_active_student(db, user_id)
    return student.id if student else None
