import json
import re

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.config import ZHIPU_API_KEY, ZHIPU_BASE_URL, ZHIPU_MODEL

_client = AsyncOpenAI(
    api_key=ZHIPU_API_KEY,
    base_url=ZHIPU_BASE_URL,
)

SYSTEM_PROMPTS = {
    "chinese": (
        "你是一位耐心、友善的小学语文老师，专门辅导{grade}年级的学生。"
        "你的职责：\n"
        "- 用适合{grade}年级学生理解的语言解释课文、字词和写作技巧\n"
        "- 引导学生思考，不要直接给出全部答案\n"
        "- 回答要简洁生动，多用比喻和例子\n"
        "- 如果学生犯错，温和地纠正并解释原因\n"
        "- 鼓励学生，增强学习信心"
    ),
    "english": (
        "You are a patient and friendly elementary school English teacher for grade {grade} students (Chinese native speakers).\n"
        "Your responsibilities:\n"
        "- Use simple English mixed with Chinese explanations when needed\n"
        "- Help with vocabulary, grammar, reading, and simple conversations\n"
        "- Correct mistakes gently and explain why\n"
        "- Use examples relevant to a {grade} grader's daily life\n"
        "- Keep responses short and encouraging"
    ),
}

HOMEWORK_GRADING_PROMPTS = {
    "chinese": (
        "你是小学{grade}年级语文老师。批改这份作业图片，逐题分析。\n"
        "直接返回JSON（不要markdown标记），格式：\n"
        '  questions数组: question_number, question_text, student_answer, correct_answer, is_correct, explanation, topic\n'
        '  summary: 总评, score: 百分制, encouragement: 鼓励语\n'
        "要求：适合{grade}年级、温和鼓励、看不清的标is_correct为true并说明。"
    ),
    "english": (
        "You are an elementary English teacher for grade {grade}. Grade this homework image.\n"
        "Return raw JSON with: questions array (question_number, question_text, student_answer, correct_answer, is_correct, explanation, topic), summary, score (percentage), encouragement (in Chinese).\n"
        "No markdown. Explain in simple English+Chinese. Be encouraging."
    ),
}


MISTAKE_CONTEXT_TEMPLATE = {
    "chinese": (
        "\n\n以下是该学生之前做错过的相关题目（错题知识库）：\n{mistakes}\n"
        "请在辅导时参考这些信息。如果学生当前问题涉及类似知识点，"
        "温和地引导他们回顾之前的错误，帮助巩固掌握。"
    ),
    "english": (
        "\n\nThe student previously made mistakes on these related questions (mistake knowledge base):\n{mistakes}\n"
        "Please reference this information during tutoring. If the student's current question involves similar concepts, "
        "gently guide them to recall and learn from past mistakes."
    ),
}


def _format_mistake_context(mistakes: list[dict], subject: str) -> str:
    parts = []
    for i, m in enumerate(mistakes, 1):
        parts.append(
            f"{i}. 题目: {m['question_text']}\n"
            f"   学生答案: {m['student_answer']}\n"
            f"   正确答案: {m['correct_answer']}\n"
            f"   知识点: {m.get('topic', '')}\n"
            f"   掌握度: {m['mastery']}/5"
        )
    return "\n".join(parts)


async def chat(
    messages: list[dict], subject: str, grade: int, mistake_context: list[dict] | None = None
) -> str:
    system_prompt = SYSTEM_PROMPTS.get(subject, SYSTEM_PROMPTS["chinese"]).format(
        grade=grade
    )

    if mistake_context:
        formatted = _format_mistake_context(mistake_context, subject)
        template = MISTAKE_CONTEXT_TEMPLATE.get(subject, MISTAKE_CONTEXT_TEMPLATE["chinese"])
        system_prompt += template.format(mistakes=formatted)

    api_messages = [{"role": "system", "content": system_prompt}] + messages

    response = await _client.chat.completions.create(
        model=ZHIPU_MODEL,
        messages=api_messages,
        max_tokens=2048,
        temperature=0.7,
    )

    return response.choices[0].message.content


async def chat_stream(
    messages: list[dict], subject: str, grade: int, mistake_context: list[dict] | None = None
) -> AsyncGenerator[str, None]:
    system_prompt = SYSTEM_PROMPTS.get(subject, SYSTEM_PROMPTS["chinese"]).format(
        grade=grade
    )

    if mistake_context:
        formatted = _format_mistake_context(mistake_context, subject)
        template = MISTAKE_CONTEXT_TEMPLATE.get(subject, MISTAKE_CONTEXT_TEMPLATE["chinese"])
        system_prompt += template.format(mistakes=formatted)

    api_messages = [{"role": "system", "content": system_prompt}] + messages

    stream = await _client.chat.completions.create(
        model=ZHIPU_MODEL,
        messages=api_messages,
        max_tokens=2048,
        temperature=0.7,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def grade_homework(image_base64: str, subject: str, grade: int, ocr_hint: str = "") -> dict:
    system_prompt = HOMEWORK_GRADING_PROMPTS.get(
        subject, HOMEWORK_GRADING_PROMPTS["chinese"]
    ).format(grade=grade)

    text_prompt = system_prompt
    if ocr_hint:
        text_prompt += f"\n\n以下是OCR预识别的文字（可能有误，仅供参考）：\n{ocr_hint}"
    text_prompt += "\n\nGrade this homework now."

    response = await _client.chat.completions.create(
        model="glm-4v-flash",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": text_prompt,
                    },
                ],
            },
        ],
        max_tokens=3000,
        temperature=0.3,
    )

    text = response.choices[0].message.content
    return _parse_grading_json(text)


def _parse_grading_json(text: str) -> dict:
    cleaned = re.sub(r'```json\s*', '', text)
    cleaned = re.sub(r'```\s*', '', cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    obj_match = re.search(r'\{[\s\S]*\}', cleaned)
    if obj_match:
        try:
            return json.loads(obj_match.group())
        except json.JSONDecodeError:
            pass

    arr_match = re.search(r'\[[\s\S]*\]', cleaned)
    if arr_match:
        try:
            questions = json.loads(arr_match.group())
            if isinstance(questions, list):
                return {"questions": questions, "summary": "", "score": None, "encouragement": "继续加油！"}
        except json.JSONDecodeError:
            pass

    return {
        "questions": [],
        "summary": text,
        "score": None,
        "encouragement": "继续加油！",
    }
