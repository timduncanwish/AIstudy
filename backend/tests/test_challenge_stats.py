"""此前没有测试的一块：/challenge/stats 背后的积分/连续天数/徽章逻辑。

这套数据被 2026-06-27 新加的「学习报告-闯关成长卡」和「个人中心-学习成长卡」
直接展示给家长看（见 frontend/src/pages/report/index.vue、
frontend/src/pages/profile/index.vue），但两次改动都是纯前端、
"复用既有接口"，get_user_stats 本身从没被单独测过。
"""
from datetime import datetime, timedelta

from tests.conftest import make_user
from app.services.challenge_service import (
    get_user_stats,
    submit_answer,
    record_preview_challenge,
    _get_or_create_stats,
)
from app.services.word_bank import get_words_for_grade


def _real_word(subject="chinese", grade=3, index=0):
    """从真实字词库取一个 (word, meaning)，避免硬编码可能不存在的字/义。"""
    w = get_words_for_grade(subject, grade)[index]
    return w["word"], w["meaning"]


async def test_get_user_stats_defaults_for_new_user(db):
    user = await make_user(db)
    stats = await get_user_stats(db, user.id)

    assert stats == {
        "total_points": 0,
        "streak_days": 0,
        "words_mastered": 0,
        "badges": [],
    }


async def test_get_user_stats_reflects_badge_details_not_just_ids(db):
    user = await make_user(db)
    word, meaning = _real_word()
    await submit_answer(
        db=db, user_id=user.id, word_str=word, subject="chinese",
        grade=3, level=1, answer=meaning, streak=0,
    )
    stats = await get_user_stats(db, user.id)

    assert stats["total_points"] > 0
    assert any(b["id"] == "first_word" for b in stats["badges"])
    # 徽章要带前端展示用的中文名/描述，不能只是原始 id
    first_word_badge = next(b for b in stats["badges"] if b["id"] == "first_word")
    assert first_word_badge["name"] == "初学者"


async def test_streak_bonus_every_fifth_correct_answer(db):
    """streak 从 4 涨到 5 时应该多给 5 分奖励（submit_answer 里 streak % 5 == 0）。"""
    user = await make_user(db)
    word, meaning = _real_word()
    result = await submit_answer(
        db=db, user_id=user.id, word_str=word, subject="chinese",
        grade=3, level=1, answer=meaning, streak=4,
    )
    assert result["correct"] is True
    assert result["streak"] == 5
    assert result["points_earned"] == 5 + 5  # level1 基础分 + 连续奖励


async def test_wrong_answer_resets_streak_to_zero(db):
    user = await make_user(db)
    word, _meaning = _real_word()
    result = await submit_answer(
        db=db, user_id=user.id, word_str=word, subject="chinese",
        grade=3, level=1, answer="完全错误的答案", streak=3,
    )
    assert result["correct"] is False
    assert result["streak"] == 0
    assert result["points_earned"] == 0


async def test_streak_days_increments_on_consecutive_day_then_resets_after_gap(db):
    user = await make_user(db)
    word1, meaning1 = _real_word(index=0)
    word2, meaning2 = _real_word(index=1)

    stats = await _get_or_create_stats(db, user.id)
    stats.streak_days = 1  # 昨天已经练过一天
    stats.last_practice_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    await db.commit()

    await submit_answer(
        db=db, user_id=user.id, word_str=word1, subject="chinese",
        grade=3, level=1, answer=meaning1, streak=0,
    )
    after_consecutive = await get_user_stats(db, user.id)
    assert after_consecutive["streak_days"] == 2

    stats = await _get_or_create_stats(db, user.id)
    stats.last_practice_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    await db.commit()

    await submit_answer(
        db=db, user_id=user.id, word_str=word2, subject="chinese",
        grade=3, level=1, answer=meaning2, streak=0,
    )
    after_gap = await get_user_stats(db, user.id)
    assert after_gap["streak_days"] == 1


async def test_record_preview_challenge_can_award_multiple_badges_in_one_call(db):
    """批量提交（预习闯关一次交一批词）可能一次跨过多个徽章门槛，
    record_preview_challenge 用 while 循环补发，这里验证真的能一次拿多个。
    """
    user = await make_user(db)
    stats = await _get_or_create_stats(db, user.id)
    stats.streak_days = 6  # 再涨一天就满足 streak_7
    stats.last_practice_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    await db.commit()

    word, _meaning = _real_word()
    res = await record_preview_challenge(db, user.id, "chinese", 3, [{"word": word, "correct": True}])

    badge_ids = {b["id"] for b in res["new_badges"]}
    assert "first_word" in badge_ids
    assert "streak_7" in badge_ids


async def test_challenge_stats_are_isolated_per_child(db):
    """修复验证：闯关积分/连续天数/掌握字词/徽章现在按当前活跃孩子分别记，
    不再是一个家长账号下所有孩子共享一份。

    此前 WordProgress/DailyTask/UserStats 三张表都没有 student_id 列（对比
    mistakes/homework/chat_history 早就有），个人中心与学习报告 2026-06-27
    新增的「学习成长」「闯关成长」卡片实际展示的是全家合计数据，切换孩子
    也不会变。现在这三张表都补上了 student_id，并在 challenge_service.py
    里用 active_student_id() 按当前活跃孩子过滤/建行。
    """
    from tests.conftest import make_student
    from app.services.student_service import activate_student

    user = await make_user(db)
    elder = await make_student(db, user.id, name="哥哥", is_active=True)
    younger = await make_student(db, user.id, name="弟弟", is_active=False)

    word, meaning = _real_word()
    await submit_answer(
        db=db, user_id=user.id, word_str=word, subject="chinese",
        grade=3, level=1, answer=meaning, streak=0,
    )
    elder_stats = await get_user_stats(db, user.id)
    assert elder_stats["total_points"] > 0
    assert elder_stats["words_mastered"] == 0  # level 1 还没到掌握线(level>=4)

    # 切到弟弟：应该是全新的一份统计，看不到哥哥刚拿到的积分/徽章
    await activate_student(db, younger.id, user.id)
    younger_stats = await get_user_stats(db, user.id)
    assert younger_stats == {
        "total_points": 0,
        "streak_days": 0,
        "words_mastered": 0,
        "badges": [],
    }

    # 切回哥哥：之前的积分/徽章还在，没有被弟弟的空白记录覆盖
    await activate_student(db, elder.id, user.id)
    elder_stats_again = await get_user_stats(db, user.id)
    assert elder_stats_again["total_points"] == elder_stats["total_points"]
    assert elder_stats_again["badges"] == elder_stats["badges"]


async def test_record_preview_challenge_skips_blank_words(db):
    user = await make_user(db)
    res = await record_preview_challenge(
        db, user.id, "chinese", 3, [{"word": "  ", "correct": True}, {"word": "", "correct": False}]
    )
    assert res["total"] == 0
    assert res["correct_count"] == 0
    assert res["points_earned"] == 0
