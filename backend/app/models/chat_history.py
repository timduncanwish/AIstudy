from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    subject = Column(String(20), nullable=False)
    grade = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
