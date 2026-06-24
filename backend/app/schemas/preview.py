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
