from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Homework(Base):
    __tablename__ = "homework"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    subject = mapped_column(String(20), nullable=False)
    image_url = mapped_column(String(500), nullable=False)
    status = mapped_column(String(20), default="pending")
    result_json = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.now)
