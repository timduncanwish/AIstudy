from pydantic import BaseModel


class DailyReport(BaseModel):
    date: str
    chat_count: int
    homework_count: int
    words_learned: int
    mistakes_count: int
    review_count: int
    subject_dist: dict  # {"chinese": 5, "english": 3}
    weak_topics: list[dict]  # [{"topic": "组词", "count": 3}]
    total_interactions: int


class WeeklyDayData(BaseModel):
    date: str
    count: int


class WeeklyReport(BaseModel):
    week_start: str
    week_end: str
    total_interactions: int
    words_learned: int
    words_mastered: int
    mistakes_reviewed: int
    daily_trend: list[WeeklyDayData]
    subject_dist: dict
    weak_topics: list[dict]
    vs_last_week: dict  # {"interactions": +5, "words": +3}
