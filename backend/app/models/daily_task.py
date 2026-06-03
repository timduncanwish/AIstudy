from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyTask(Base):
    __tablename__ = "daily_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    subject = mapped_column(String(20), nullable=False)
    task_date = mapped_column(String(10), nullable=False)
    words_json = mapped_column(Text, nullable=False)
    completed = mapped_column(Integer, default=0)
    total = mapped_column(Integer, default=10)
    points_earned = mapped_column(Integer, default=0)
    created_at = mapped_column(DateTime, default=datetime.now)
