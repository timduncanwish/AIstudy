from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.security.types import EncryptedText


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name = mapped_column(EncryptedText, nullable=False)
    grade = mapped_column(Integer, default=3)
    avatar_tag = mapped_column(String(10), default="👦")
    is_active = mapped_column(Boolean, default=False)
    created_at = mapped_column(DateTime, default=datetime.now)
