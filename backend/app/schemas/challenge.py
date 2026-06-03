from pydantic import BaseModel


class ChallengeOption(BaseModel):
    text: str
    index: int
    is_correct: bool = False


class ChallengeQuestion(BaseModel):
    word: str
    pinyin: str
    level: int
    level_name: str
    question_text: str
    hint: str
    options: list[ChallengeOption]
    correct_answer: str


class SubmitAnswerRequest(BaseModel):
    word: str
    subject: str
    grade: int = 3
    level: int
    answer: str
    streak: int = 0


class SubmitAnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    new_level: int
    points_earned: int
    streak: int
    badge_earned: str | None = None
    encouragement: str


class DailyTaskResponse(BaseModel):
    task_date: str
    subject: str
    total: int
    completed: int
    remaining: int
    words: list[str]


class BadgeDetail(BaseModel):
    id: str
    name: str
    desc: str


class UserStatsResponse(BaseModel):
    total_points: int
    streak_days: int
    words_mastered: int
    badges: list[BadgeDetail]
