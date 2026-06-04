from datetime import datetime

from pydantic import BaseModel


class MistakeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    subject: str
    question_text: str
    correct_answer: str
    student_answer: str | None
    explanation: str | None
    topic: str | None
    mastery: int
    review_count: int
    next_review: datetime
    created_at: datetime


class MistakeListResponse(BaseModel):
    items: list[MistakeResponse]
    total: int
    page: int


class ReviewRequest(BaseModel):
    correct: bool


class TopicStat(BaseModel):
    topic: str
    count: int
    avg_mastery: float


class MistakeStatsResponse(BaseModel):
    total_mistakes: int
    mastered_count: int
    reviewing_count: int
    new_count: int
    topics: list[TopicStat]
    subject_dist: dict[str, int]
