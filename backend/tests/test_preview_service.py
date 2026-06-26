"""字词句课前预习：教材清单、单元清单和完成记录。"""

import pytest

from app.services.preview_service import (
    complete_preview_item,
    get_preview_unit_detail,
    get_preview_units,
    list_textbook_options,
)
from tests.conftest import make_user


def test_textbook_options_cover_grades_1_to_9():
    options = list_textbook_options()
    grades = {item["grade"] for item in options}
    assert grades == set(range(1, 10))
    assert any(item["subject"] == "chinese" and item["version"] == "统编版" for item in options)
    assert any(item["subject"] == "english" and item["version"] == "PEP人教版" for item in options)


@pytest.mark.asyncio
async def test_preview_units_return_grade_word_bank(db):
    user = await make_user(db)
    units = await get_preview_units(db, user.id, "chinese", 3, "上册", "统编版")

    assert units
    assert units[0]["unit"] == 1
    assert units[0]["total_items"] > 0
    assert units[0]["completed_items"] == 0


@pytest.mark.asyncio
async def test_semester_units_differ(db):
    """上册和下册必须取到不同的教材数据，验证学期已生效。"""
    user = await make_user(db)
    up = await get_preview_units(db, user.id, "chinese", 3, "上册", "统编版")
    down = await get_preview_units(db, user.id, "chinese", 3, "下册", "统编版")
    assert up and down
    assert up[0]["title"] != down[0]["title"]


@pytest.mark.asyncio
async def test_chinese_detail_has_first_and_second_class(db):
    """语文单元应同时给出一类字(会写)和二类字(会认)。"""
    user = await make_user(db)
    detail = await get_preview_unit_detail(db, user.id, "chinese", 3, "上册", "统编版", 1)
    types = {item["item_type"] for item in detail["items"]}
    assert "first_class_char" in types
    assert "second_class_char" in types
    assert detail["source_status"] == "待人工复核"


@pytest.mark.asyncio
async def test_english_detail_has_vocabulary(db):
    user = await make_user(db)
    detail = await get_preview_unit_detail(db, user.id, "english", 3, "上册", "PEP人教版", 1)
    types = {item["item_type"] for item in detail["items"]}
    assert "vocabulary" in types


def test_build_explain_messages_chinese_first_class():
    from app.services.ai_service import build_preview_explain_messages
    msgs = build_preview_explain_messages(
        "chinese", 3, "晨", "first_class_char", "一类字（会写）", "第一单元 · 校园生活", "早晨"
    )
    assert msgs[0]["role"] == "system" and msgs[1]["role"] == "user"
    assert "3年级" in msgs[0]["content"]
    assert "会写" in msgs[0]["content"]  # 一类字强调书写
    assert "晨" in msgs[1]["content"]
    assert "第一单元" in msgs[1]["content"]


def test_build_explain_messages_chinese_second_class_no_writing():
    from app.services.ai_service import build_preview_explain_messages
    msgs = build_preview_explain_messages("chinese", 5, "鹭", "second_class_char")
    assert "会认" in msgs[0]["content"]
    assert "鹭" in msgs[1]["content"]


def test_build_explain_messages_english_uses_simple_english():
    from app.services.ai_service import build_preview_explain_messages
    msgs = build_preview_explain_messages("english", 4, "panda", "vocabulary", "词汇表单词", "Unit 4", "熊猫")
    assert "grade 4" in msgs[0]["content"]
    assert "panda" in msgs[1]["content"]
    assert "熊猫" in msgs[1]["content"]


@pytest.mark.asyncio
async def test_complete_preview_item_marks_unit_detail(db):
    user = await make_user(db)
    detail = await get_preview_unit_detail(db, user.id, "english", 3, "上册", "PEP人教版", 1)
    first = detail["items"][0]

    progress = await complete_preview_item(
        db,
        user.id,
        "english",
        3,
        "上册",
        "PEP人教版",
        1,
        first["item_key"],
        first["item_type"],
    )

    assert progress.item_key == first["item_key"]
    updated = await get_preview_unit_detail(db, user.id, "english", 3, "上册", "PEP人教版", 1)
    assert updated["items"][0]["completed"] is True
