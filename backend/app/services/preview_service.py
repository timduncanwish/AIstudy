from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preview_progress import PreviewProgress
from app.scope import active_student_id
from app.services.textbook_bank import (
    SEMESTERS,
    get_semester_units,
    has_semester_data,
    textbook_meta,
)

TEXTBOOK_SOURCES = {
    "chinese": {
        "version": "统编版",
        "label": "语文·统编版",
        "source_name": "国家中小学智慧教育平台 / 人教社中小学教材电子版",
        "source_url": "https://basic.smartedu.cn/",
    },
    "english": {
        "version": "PEP人教版",
        "label": "英语·PEP人教版",
        "source_name": "国家中小学智慧教育平台 / 人教社中小学教材电子版",
        "source_url": "https://jc.pep.com.cn/",
    },
}

SUPPORTED_GRADES = list(range(1, 10))


def list_textbook_options() -> list[dict]:
    items = []
    for grade in SUPPORTED_GRADES:
        for semester in SEMESTERS:
            for subject, source in TEXTBOOK_SOURCES.items():
                ready = has_semester_data(subject, grade, semester)
                items.append({
                    "subject": subject,
                    "grade": grade,
                    "semester": semester,
                    "version": source["version"],
                    "label": f"{grade}年级{semester} {source['label']}",
                    "source_name": source["source_name"],
                    "source_url": source["source_url"],
                    "status": "ready" if ready else "pending_source",
                })
    return items


async def get_preview_units(
    db: AsyncSession,
    user_id: int,
    subject: str,
    grade: int,
    semester: str,
    textbook_version: str,
) -> list[dict]:
    units = get_semester_units(subject, grade, semester)
    if not units:
        return []

    completed = await _completed_keys(db, user_id, subject, grade, semester, textbook_version)
    result = []
    for unit in units:
        unit_no = int(unit.get("unit", 0))
        items = _build_unit_items(subject, grade, semester, unit_no, unit)
        unit_completed = sum(1 for item in items if item["item_key"] in completed)
        result.append({
            "unit": unit_no,
            "title": unit.get("title", ""),
            "total_items": len(items),
            "completed_items": unit_completed,
            "source_status": unit.get("source_status", "待人工复核"),
        })
    return result


async def get_preview_unit_detail(
    db: AsyncSession,
    user_id: int,
    subject: str,
    grade: int,
    semester: str,
    textbook_version: str,
    unit_no: int,
) -> dict | None:
    units = get_semester_units(subject, grade, semester)
    if not units:
        return None

    completed = await _completed_keys(db, user_id, subject, grade, semester, textbook_version)
    for unit in units:
        if int(unit.get("unit", 0)) != unit_no:
            continue
        items = _build_unit_items(subject, grade, semester, unit_no, unit)
        for item in items:
            item["completed"] = item["item_key"] in completed

        meta = textbook_meta(subject, grade)
        fallback = TEXTBOOK_SOURCES[subject]
        return {
            "subject": subject,
            "grade": grade,
            "semester": semester,
            "textbook_version": textbook_version,
            "unit": unit_no,
            "title": unit.get("title", ""),
            "source_name": meta["source_name"] or fallback["source_name"],
            "source_url": meta["source_url"] or fallback["source_url"],
            "source_status": unit.get("source_status", "待人工复核"),
            "guidance": _guidance(subject),
            "items": items,
        }
    return None


async def complete_preview_item(
    db: AsyncSession,
    user_id: int,
    subject: str,
    grade: int,
    semester: str,
    textbook_version: str,
    unit: int,
    item_key: str,
    item_type: str,
) -> PreviewProgress:
    sid = await active_student_id(db, user_id)
    stmt = select(PreviewProgress).where(
        PreviewProgress.user_id == user_id,
        PreviewProgress.student_id == sid,
        PreviewProgress.subject == subject,
        PreviewProgress.grade == grade,
        PreviewProgress.semester == semester,
        PreviewProgress.textbook_version == textbook_version,
        PreviewProgress.unit == unit,
        PreviewProgress.item_key == item_key,
    )
    progress = (await db.execute(stmt)).scalar_one_or_none()
    if progress:
        progress.completed_at = datetime.now()
    else:
        progress = PreviewProgress(
            user_id=user_id,
            student_id=sid,
            subject=subject,
            grade=grade,
            semester=semester,
            textbook_version=textbook_version,
            unit=unit,
            item_key=item_key,
            item_type=item_type,
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)
    return progress


async def _completed_keys(
    db: AsyncSession,
    user_id: int,
    subject: str,
    grade: int,
    semester: str,
    textbook_version: str,
) -> set[str]:
    sid = await active_student_id(db, user_id)
    stmt = select(PreviewProgress.item_key).where(
        PreviewProgress.user_id == user_id,
        PreviewProgress.student_id == sid,
        PreviewProgress.subject == subject,
        PreviewProgress.grade == grade,
        PreviewProgress.semester == semester,
        PreviewProgress.textbook_version == textbook_version,
    )
    return set((await db.execute(stmt)).scalars().all())


# ---- 单元 → 预习项 ----

def _build_unit_items(
    subject: str, grade: int, semester: str, unit_no: int, unit: dict
) -> list[dict]:
    items: list[dict] = []
    if subject == "english":
        for word in unit.get("words", []):
            items.append(_word_item(subject, grade, semester, unit_no, word, "vocabulary"))
        for phrase in unit.get("phrases", []):
            items.append(_text_item(subject, grade, semester, unit_no, phrase, "phrase"))
        for sentence in unit.get("sentences", []):
            items.append(_text_item(subject, grade, semester, unit_no, sentence, "sentence"))
    else:
        for word in unit.get("first_class", []):
            items.append(_word_item(subject, grade, semester, unit_no, word, "first_class_char"))
        for word in unit.get("second_class", []):
            items.append(_word_item(subject, grade, semester, unit_no, word, "second_class_char"))
        for phrase in unit.get("phrases", []):
            items.append(_text_item(subject, grade, semester, unit_no, phrase, "phrase"))
        for sentence in unit.get("sentences", []):
            items.append(_text_item(subject, grade, semester, unit_no, sentence, "sentence"))
    return items


def _word_item(
    subject: str, grade: int, semester: str, unit_no: int, word: dict, item_type: str
) -> dict:
    text = word.get("word", "")
    examples = word.get("examples") or word.get("sample_sentences") or []
    return {
        "item_key": _item_key(subject, grade, semester, unit_no, item_type, text),
        "item_type": item_type,
        "category_label": _category_label(subject, item_type),
        "word": text,
        "pronunciation": word.get("pinyin") or word.get("phonetic") or "",
        "meaning": word.get("meaning", ""),
        "hint": word.get("hint", ""),
        "sample_sentences": examples,
        "practice_prompt": _practice_prompt(subject, item_type, text),
        "completed": False,
    }


def _text_item(
    subject: str, grade: int, semester: str, unit_no: int, raw, item_type: str
) -> dict:
    """词语/句子项：raw 可为字符串或 {text, meaning} 字典。"""
    if isinstance(raw, dict):
        text = raw.get("text") or raw.get("word", "")
        meaning = raw.get("meaning", "")
        examples = raw.get("examples", [])
    else:
        text = str(raw)
        meaning = ""
        examples = []
    return {
        "item_key": _item_key(subject, grade, semester, unit_no, item_type, text),
        "item_type": item_type,
        "category_label": _category_label(subject, item_type),
        "word": text,
        "pronunciation": "",
        "meaning": meaning,
        "hint": "",
        "sample_sentences": examples,
        "practice_prompt": _practice_prompt(subject, item_type, text),
        "completed": False,
    }


def _item_key(subject: str, grade: int, semester: str, unit_no: int, item_type: str, text: str) -> str:
    return f"{subject}:g{grade}:{semester}:u{unit_no}:{item_type}:{text}"


def _category_label(subject: str, item_type: str) -> str:
    labels = {
        "vocabulary": "词汇表单词",
        "first_class_char": "一类字（会写）",
        "second_class_char": "二类字（会认）",
        "phrase": "重点词语" if subject == "chinese" else "重点短语",
        "sentence": "重点句",
    }
    return labels.get(item_type, item_type)


def _practice_prompt(subject: str, item_type: str, word: str) -> str:
    if subject == "english":
        if item_type == "sentence":
            return f"跟读句子“{word}”，再试着替换其中一个词说一句。"
        if item_type == "phrase":
            return f"读一读短语“{word}”，想想它在什么情景下用。"
        return f"读一读 {word}，再用它说一个简单英文句子。"
    if item_type == "first_class_char":
        return f"认读“{word}”，写一遍，组一个词，再试着说一句话。"
    if item_type == "second_class_char":
        return f"认读“{word}”，说说它在句子里的意思。"
    if item_type == "sentence":
        return f"读一读句子“{word}”，再仿写一句。"
    return f"读一读“{word}”，理解意思后试着用它说一句话。"


def _guidance(subject: str) -> str:
    if subject == "english":
        return "先听读单词，再看中文意思，最后用一个简单句子说出来。"
    return "先读准字音，再理解意思；一类字多练书写，二类字重点会认会用。"
