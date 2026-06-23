from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Mistake(Base):
    __tablename__ = "mistakes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = mapped_column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    homework_id = mapped_column(Integer, ForeignKey("homework.id"), nullable=True)
    subject = mapped_column(String(20), nullable=False)
    question_text = mapped_column(Text, nullable=False)
    correct_answer = mapped_column(Text, nullable=False)
    student_answer = mapped_column(Text, nullable=True)
    explanation = mapped_column(Text, nullable=True)
    topic = mapped_column(String(100), nullable=True)
    mastery = mapped_column(Integer, default=0)
    review_count = mapped_column(Integer, default=0)
    next_review = mapped_column(DateTime, default=datetime.now)
    created_at = mapped_column(DateTime, default=datetime.now)
