from datetime import datetime

from pydantic import BaseModel


class DailyPracticeGenerateRequest(BaseModel):
    subject: str = "chinese"


class PracticeQuestionItem(BaseModel):
    question: str
    options: list[str]
    correct_index: int
    explanation: str


class DailyPracticeResponse(BaseModel):
    id: int
    subject: str
    topic: str
    questions: list[PracticeQuestionItem]
    score: int | None = None
    total: int = 0
    created_at: datetime


class SubmitPracticeRequest(BaseModel):
    answers: list[int]


class PracticeHistoryItem(BaseModel):
    id: int
    subject: str
    topic: str
    score: int | None
    total: int
    created_at: datetime


class PracticeHistoryResponse(BaseModel):
    items: list[PracticeHistoryItem]
    streak: int
