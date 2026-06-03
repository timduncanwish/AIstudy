from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    subject: str = "chinese"  # "chinese" or "english"
    grade: int = 3  # 3-6年级


class ChatResponse(BaseModel):
    reply: str
    subject: str
