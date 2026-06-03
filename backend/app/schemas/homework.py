from pydantic import BaseModel


class QuestionResult(BaseModel):
    question_number: int
    question_text: str
    student_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str
    topic: str


class HomeworkUploadResponse(BaseModel):
    homework_id: int
    status: str
    questions: list[QuestionResult]
    summary: str
    score: int | None = None
    encouragement: str
    mistake_count: int
