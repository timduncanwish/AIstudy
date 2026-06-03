from datetime import datetime

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id = mapped_column(String(64), unique=True, nullable=False)
    openid = mapped_column(String(100), unique=True, nullable=True)
    nickname = mapped_column(String(50), default="同学")
    avatar_url = mapped_column(String(500), nullable=True)
    grade = mapped_column(Integer, default=3)
    created_at = mapped_column(DateTime, default=datetime.now)
