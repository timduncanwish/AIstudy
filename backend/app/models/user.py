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
    notify_subscribed = mapped_column(Integer, default=0)  # 0=未订阅 1=已订阅
    notify_time = mapped_column(String(5), nullable=True)  # "HH:MM"，每日推送时间
    created_at = mapped_column(DateTime, default=datetime.now)
