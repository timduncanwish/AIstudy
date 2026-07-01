from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WordProgress(Base):
    __tablename__ = "word_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = mapped_column(Integer, ForeignKey("students.id"), nullable=True)
    word = mapped_column(String(50), nullable=False)
    subject = mapped_column(String(20), nullable=False)
    level = mapped_column(Integer, default=0)
    review_count = mapped_column(Integer, default=0)
    next_review = mapped_column(DateTime, default=datetime.now)
    created_at = mapped_column(DateTime, default=datetime.now)
    updated_at = mapped_column(DateTime, default=datetime.now)
