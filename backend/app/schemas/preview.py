from datetime import datetime

from pydantic import BaseModel


class TextbookOption(BaseModel):
    subject: str
    grade: int
    semester: str
    version: str
    label: str
    source_name: str
    source_url: str
    status: str


class TextbookOptionsResponse(BaseModel):
    items: list[TextbookOption]


class PreviewUnitItem(BaseModel):
    unit: int
    title: str
    total_items: int
    completed_items: int
    source_status: str


class PreviewUnitsResponse(BaseModel):
    subject: str
    grade: int
    semester: str
    textbook_version: str
    units: list[PreviewUnitItem]


class PreviewItem(BaseModel):
    item_key: str
    item_type: str
    category_label: str
    word: str
    pronunciation: str = ""
    meaning: str
    hint: str = ""
    sample_sentences: list[str] = []
    practice_prompt: str
    completed: bool = False


class PreviewUnitDetailResponse(BaseModel):
    subject: str
    grade: int
    semester: str
    textbook_version: str
    unit: int
    title: str
    source_name: str
    source_url: str
    source_status: str
    guidance: str
    items: list[PreviewItem]


class CompletePreviewItemRequest(BaseModel):
    subject: str
    grade: int
    semester: str
    textbook_version: str
    unit: int
    item_key: str
    item_type: str


class CompletePreviewItemResponse(BaseModel):
    item_key: str
    completed: bool
    completed_at: datetime


class ExplainPreviewItemRequest(BaseModel):
    subject: str
    grade: int
    word: str
    item_type: str
    category_label: str = ""
    unit_title: str = ""
    meaning: str = ""


class ExplainPreviewItemResponse(BaseModel):
    word: str
    explanation: str


class StudiedUnit(BaseModel):
    subject: str
    grade: int
    semester: str
    unit: int
    title: str
    completed_items: int
    total_items: int
    percent: int


class ParentSummaryResponse(BaseModel):
    period_days: int
    weekly_completed: int
    subject_breakdown: dict[str, int]
    studied_units: list[StudiedUnit]
    review_suggestions: list[str]


class ChallengeOption(BaseModel):
    text: str
    is_correct: bool
    index: int


class ChallengeQuestion(BaseModel):
    word: str
    pinyin: str = ""
    type: str
    question_text: str
    options: list[ChallengeOption]
    correct_answer: str


class UnitChallengeResponse(BaseModel):
    subject: str
    grade: int
    semester: str
    unit: int
    questions: list[ChallengeQuestion]


class ChallengeResultItem(BaseModel):
    word: str
    correct: bool


class ChallengeResultRequest(BaseModel):
    subject: str
    grade: int
    results: list[ChallengeResultItem]


class BadgeInfo(BaseModel):
    id: str
    name: str
    desc: str


class ChallengeResultResponse(BaseModel):
    points_earned: int
    correct_count: int
    total: int
    total_points: int
    streak_days: int
    words_mastered: int
    new_badges: list[BadgeInfo]
