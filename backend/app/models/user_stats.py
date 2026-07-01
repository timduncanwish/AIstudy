from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserStats(Base):
    __tablename__ = "user_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 曾是 UNIQUE(user_id)（一人一行）；现按孩子分别记分，一个 user 下允许多行
    # （不同 student_id），唯一性由 service 层 get-or-create 查询保证，
    # 与 WordProgress/PreviewProgress 的做法一致。
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = mapped_column(Integer, ForeignKey("students.id"), nullable=True)
    total_points = mapped_column(Integer, default=0)
    streak_days = mapped_column(Integer, default=0)
    last_practice_date = mapped_column(String(10), nullable=True)
    words_mastered = mapped_column(Integer, default=0)
    badges_json = mapped_column(Text, default="[]")
    created_at = mapped_column(DateTime, default=datetime.now)
    updated_at = mapped_column(DateTime, default=datetime.now)
