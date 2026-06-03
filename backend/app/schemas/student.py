from datetime import datetime
from pydantic import BaseModel


class StudentCreate(BaseModel):
    name: str
    grade: int = 3
    avatar_tag: str = "👦"


class StudentUpdate(BaseModel):
    name: str | None = None
    grade: int | None = None
    avatar_tag: str | None = None


class StudentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    grade: int
    avatar_tag: str
    is_active: bool
    created_at: datetime
