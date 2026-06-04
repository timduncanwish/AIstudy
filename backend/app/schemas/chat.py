from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    subject: str = "chinese"  # "chinese" or "english"
    grade: int = 3  # 3-6年级
    user_id: int | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    subject: str
    mistakes_referenced: int = 0


class ChatHistoryMessage(BaseModel):
    role: str
    content: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    subject: str
    grade: int
    messages: list[ChatHistoryMessage]


class ChatSessionSummary(BaseModel):
    session_id: str
    subject: str
    grade: int
    last_message: str
    message_count: int
    created_at: str


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionSummary]
