from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PreviewProgress(Base):
    __tablename__ = "preview_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = mapped_column(Integer, ForeignKey("students.id"), nullable=True)
    subject = mapped_column(String(20), nullable=False)
    grade = mapped_column(Integer, nullable=False)
    semester = mapped_column(String(10), nullable=False)
    textbook_version = mapped_column(String(50), nullable=False)
    unit = mapped_column(Integer, nullable=False)
    item_key = mapped_column(String(120), nullable=False)
    item_type = mapped_column(String(40), nullable=False)
    completed_at = mapped_column(DateTime, default=datetime.now)
    created_at = mapped_column(DateTime, default=datetime.now)
