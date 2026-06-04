from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyPractice(Base):
    __tablename__ = "daily_practices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    subject = mapped_column(String(20), nullable=False)
    topic = mapped_column(String(100), nullable=False)
    questions_json = mapped_column(Text, nullable=False)
    answers_json = mapped_column(Text, nullable=True)
    score = mapped_column(Integer, nullable=True)
    total = mapped_column(Integer, default=0)
    created_at = mapped_column(DateTime, default=datetime.now)
