import json
import random
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.word_progress import WordProgress
from app.models.daily_task import DailyTask
from app.models.user_stats import UserStats
from app.services.word_bank import get_words_for_grade, get_word_detail
from app.scope import active_student_id

REVIEW_INTERVALS = [1, 2, 4, 7, 14, 30]

LEVEL_POINTS = {1: 5, 2: 10, 3: 15, 4: 20}
LEVEL_NAMES = {1: "认读", 2: "拼写", 3: "造句", 4: "应用"}

BADGE_DEFS = {
    "first_word": ("初学者", "完成第一个字词的认读"),
    "daily_done": ("任务达人", "完成第一个每日任务"),
    "streak_3": ("三日连胜", "连续3天练习"),
    "streak_7": ("周冠军", "连续7天练习"),
    "master_10": ("字词达人", "掌握10个字词"),
    "master_50": ("小学者", "掌握50个字词"),
    "perfect_day": ("完美日", "每日任务全部正确"),
}


async def get_or_create_daily_task(
    db: AsyncSession, user_id: int, subject: str, grade: int
) -> DailyTask:
    sid = await active_student_id(db, user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    conds = [
        DailyTask.user_id == user_id,
        DailyTask.subject == subject,
        DailyTask.task_date == today,
    ]
    if sid is not None:
        conds.append(DailyTask.student_id == sid)
    result = await db.execute(select(DailyTask).where(*conds))
    task = result.scalar_one_or_none()
    if task:
        return task

    review_words = await _get_review_words(db, user_id, subject, sid)
    all_words = get_words_for_grade(subject, grade)

    new_words = []
    for w in all_words:
        wp_conds = [
            WordProgress.user_id == user_id,
            WordProgress.word == w["word"],
            WordProgress.subject == subject,
        ]
        if sid is not None:
            wp_conds.append(WordProgress.student_id == sid)
        wp_result = await db.execute(select(WordProgress).where(*wp_conds))
        if not wp_result.scalar_one_or_none():
            new_words.append(w["word"])

    selected = []
    for rw in review_words:
        selected.append(rw.word)
        if len(selected) >= 10:
            break

    remaining = 10 - len(selected)
    random.shuffle(new_words)
    selected.extend(new_words[:remaining])

    if not selected and all_words:
        random.shuffle(all_words)
        selected = [w["word"] for w in all_words[:10]]

    task = DailyTask(
        user_id=user_id,
        student_id=sid,
        subject=subject,
        task_date=today,
        words_json=json.dumps(selected[:10], ensure_ascii=False),
        total=min(len(selected), 10),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def _get_review_words(
    db: AsyncSession, user_id: int, subject: str, student_id: int | None
) -> list[WordProgress]:
    conds = [
        WordProgress.user_id == user_id,
        WordProgress.subject == subject,
        WordProgress.next_review <= datetime.now(),
        WordProgress.level < 4,
    ]
    if student_id is not None:
        conds.append(WordProgress.student_id == student_id)
    result = await db.execute(
        select(WordProgress).where(*conds).order_by(WordProgress.next_review.asc())
    )
    return list(result.scalars().all())


async def generate_challenge(
    db: AsyncSession, user_id: int, subject: str, grade: int
) -> dict | None:
    task = await get_or_create_daily_task(db, user_id, subject, grade)
    words = json.loads(task.words_json)
    completed_words = set()

    if task.completed >= task.total:
        return None

    for i, word_str in enumerate(words):
        if i >= task.completed:
            wp = await _get_or_create_progress(db, user_id, word_str, subject)
            word_detail = get_word_detail(subject, grade, word_str)
            if not word_detail:
                continue

            challenge_level = wp.level + 1
            if challenge_level > 4:
                continue

            return _build_challenge(word_detail, challenge_level, subject, grade)

    return None


def _build_challenge(word_detail: dict, level: int, subject: str, grade: int) -> dict:
    word = word_detail["word"]

    if level == 1:
        options = _make_options(word_detail["meaning"], word_detail.get("distractor_meanings", []))
        return {
            "word": word,
            "target_word": word,
            "pinyin": word_detail.get("pinyin", word_detail.get("phonetic", "")),
            "level": level,
            "level_name": LEVEL_NAMES[level],
            "question_text": f"「{word}」是什么意思？",
            "hint": word_detail.get("pinyin", word_detail.get("phonetic", "")),
            "options": options,
            "correct_answer": word_detail["meaning"],
        }

    elif level == 2:
        options = _make_options(word, word_detail.get("distractor_words", []))
        meaning = word_detail["meaning"]
        return {
            "word": "",
            "target_word": word,
            "pinyin": word_detail.get("pinyin", word_detail.get("phonetic", "")),
            "level": level,
            "level_name": LEVEL_NAMES[level],
            "question_text": f"「{meaning}」对应的字/词是？",
            "hint": word_detail.get("pinyin", word_detail.get("phonetic", "")),
            "options": options,
            "correct_answer": word,
        }

    elif level == 3:
        sentences = word_detail.get("sample_sentences", [])
        if len(sentences) >= 1:
            correct = sentences[0]
            other_words = get_words_for_grade(subject, grade)
            distractor_sents = []
            for ow in other_words:
                if ow["word"] != word and ow.get("sample_sentences"):
                    distractor_sents.append(ow["sample_sentences"][0])
                if len(distractor_sents) >= 3:
                    break
            options = _make_options(correct, distractor_sents)
            return {
                "word": word,
                "target_word": word,
                "pinyin": word_detail.get("pinyin", word_detail.get("phonetic", "")),
                "level": level,
                "level_name": LEVEL_NAMES[level],
                "question_text": f"哪个句子正确使用了「{word}」？",
                "hint": "",
                "options": options,
                "correct_answer": correct,
            }

    elif level == 4:
        hint = word_detail.get("level_hint", f"____{word}____")
        distractors = word_detail.get("distractor_words", [])[:3]
        options = _make_options(word, distractors)
        return {
            "word": "",
            "target_word": word,
            "pinyin": "",
            "level": level,
            "level_name": LEVEL_NAMES[level],
            "question_text": f"请选择正确的字/词填空：{hint}",
            "hint": "",
            "options": options,
            "correct_answer": word,
        }

    return {}


def _make_options(correct: str, distractors: list[str]) -> list[dict]:
    options = [{"text": correct, "is_correct": True}]
    for d in distractors[:3]:
        options.append({"text": d, "is_correct": False})
    while len(options) < 4:
        options.append({"text": "—", "is_correct": False})
    random.shuffle(options)
    for i, opt in enumerate(options):
        opt["index"] = i
    return options


async def _get_or_create_progress(
    db: AsyncSession, user_id: int, word: str, subject: str
) -> WordProgress:
    sid = await active_student_id(db, user_id)
    conds = [
        WordProgress.user_id == user_id,
        WordProgress.word == word,
        WordProgress.subject == subject,
    ]
    if sid is not None:
        conds.append(WordProgress.student_id == sid)
    result = await db.execute(select(WordProgress).where(*conds))
    wp = result.scalar_one_or_none()
    if wp:
        return wp

    wp = WordProgress(user_id=user_id, student_id=sid, word=word, subject=subject, level=0)
    db.add(wp)
    await db.commit()
    await db.refresh(wp)
    return wp


async def submit_answer(
    db: AsyncSession,
    user_id: int,
    word_str: str,
    subject: str,
    grade: int,
    level: int,
    answer: str,
    streak: int,
) -> dict:
    sid = await active_student_id(db, user_id)
    wp = await _get_or_create_progress(db, user_id, word_str, subject)
    word_detail = get_word_detail(subject, grade, word_str)

    correct_answer = ""
    if word_detail:
        if level == 1:
            correct_answer = word_detail["meaning"]
        elif level == 2:
            correct_answer = word_str
        elif level == 3:
            correct_answer = word_detail.get("sample_sentences", [""])[0]
        elif level == 4:
            correct_answer = word_str

    is_correct = answer == correct_answer

    points = 0
    new_badge = None

    if is_correct:
        wp.level = min(4, wp.level + 1)
        wp.review_count += 1
        interval_idx = min(wp.level, len(REVIEW_INTERVALS) - 1)
        wp.next_review = datetime.now() + timedelta(days=REVIEW_INTERVALS[interval_idx])

        points = LEVEL_POINTS.get(level, 5)
        streak += 1
        if streak > 0 and streak % 5 == 0:
            points += 5
    else:
        wp.review_count += 1
        wp.next_review = datetime.now() + timedelta(days=1)
        streak = 0

    wp.updated_at = datetime.now()
    await db.commit()

    task_conds = [
        DailyTask.user_id == user_id,
        DailyTask.subject == subject,
        DailyTask.task_date == datetime.now().strftime("%Y-%m-%d"),
    ]
    if sid is not None:
        task_conds.append(DailyTask.student_id == sid)
    task_result = await db.execute(select(DailyTask).where(*task_conds))
    task = task_result.scalar_one_or_none()
    if task:
        task.completed += 1
        task.points_earned += points

        if task.completed >= task.total and is_correct:
            points += 20

        await db.commit()

    stats = await _get_or_create_stats(db, user_id)
    stats.total_points += points
    today = datetime.now().strftime("%Y-%m-%d")
    if stats.last_practice_date:
        last = datetime.strptime(stats.last_practice_date, "%Y-%m-%d")
        if (datetime.now() - last).days == 1:
            stats.streak_days += 1
        elif (datetime.now() - last).days > 1:
            stats.streak_days = 1
    else:
        stats.streak_days = 1
    stats.last_practice_date = today

    mastered_conds = [WordProgress.user_id == user_id, WordProgress.level >= 4]
    if sid is not None:
        mastered_conds.append(WordProgress.student_id == sid)
    mastered = await db.execute(
        select(func.count()).select_from(WordProgress).where(*mastered_conds)
    )
    stats.words_mastered = mastered.scalar() or 0

    new_badge = _check_badges(stats, wp, task)
    stats.updated_at = datetime.now()
    await db.commit()

    encouragement = _get_encouragement(is_correct, level)

    return {
        "correct": is_correct,
        "correct_answer": correct_answer,
        "new_level": wp.level,
        "points_earned": points,
        "streak": streak,
        "badge_earned": new_badge,
        "encouragement": encouragement,
    }


async def record_preview_challenge(
    db: AsyncSession,
    user_id: int,
    subject: str,
    grade: int,
    results: list[dict],
) -> dict:
    """记录「预习单元闯关」成绩，并入既有积分/掌握度/徽章体系。

    results: [{"word": str, "correct": bool}, ...]
    认读级计分，与每日闯关共用 WordProgress / UserStats / 徽章。
    """
    sid = await active_student_id(db, user_id)
    points = 0
    correct_count = 0
    total = 0
    best_wp: WordProgress | None = None

    for r in results:
        word = (r.get("word") or "").strip()
        if not word:
            continue
        total += 1
        wp = await _get_or_create_progress(db, user_id, word, subject)
        wp.review_count += 1
        if r.get("correct"):
            correct_count += 1
            wp.level = min(4, wp.level + 1)
            interval_idx = min(wp.level, len(REVIEW_INTERVALS) - 1)
            wp.next_review = datetime.now() + timedelta(days=REVIEW_INTERVALS[interval_idx])
            points += LEVEL_POINTS[1]
        else:
            wp.next_review = datetime.now() + timedelta(days=1)
        wp.updated_at = datetime.now()
        if best_wp is None or wp.level >= best_wp.level:
            best_wp = wp

    if total and correct_count == total:
        points += 10  # 全对奖励

    await db.commit()

    stats = await _get_or_create_stats(db, user_id)
    stats.total_points += points
    today = datetime.now().strftime("%Y-%m-%d")
    if stats.last_practice_date:
        last = datetime.strptime(stats.last_practice_date, "%Y-%m-%d")
        delta = (datetime.now() - last).days
        if delta == 1:
            stats.streak_days += 1
        elif delta > 1:
            stats.streak_days = 1
    else:
        stats.streak_days = 1
    stats.last_practice_date = today

    mastered_conds = [WordProgress.user_id == user_id, WordProgress.level >= 4]
    if sid is not None:
        mastered_conds.append(WordProgress.student_id == sid)
    mastered = await db.execute(
        select(func.count()).select_from(WordProgress).where(*mastered_conds)
    )
    stats.words_mastered = mastered.scalar() or 0

    new_badges: list[str] = []
    if best_wp is not None:
        while True:
            b = _check_badges(stats, best_wp, None)
            if not b:
                break
            new_badges.append(b)
    stats.updated_at = datetime.now()
    await db.commit()

    badge_details = []
    for b in new_badges:
        if b in BADGE_DEFS:
            name, desc = BADGE_DEFS[b]
            badge_details.append({"id": b, "name": name, "desc": desc})

    return {
        "points_earned": points,
        "correct_count": correct_count,
        "total": total,
        "total_points": stats.total_points,
        "streak_days": stats.streak_days,
        "words_mastered": stats.words_mastered,
        "new_badges": badge_details,
    }


def _check_badges(stats: UserStats, wp: WordProgress, task: DailyTask | None) -> str | None:
    badges = json.loads(stats.badges_json)
    new_badge = None

    if wp.level >= 1 and "first_word" not in badges:
        new_badge = "first_word"
    elif task and task.completed >= task.total and "daily_done" not in badges:
        new_badge = "daily_done"
    elif stats.streak_days >= 3 and "streak_3" not in badges:
        new_badge = "streak_3"
    elif stats.streak_days >= 7 and "streak_7" not in badges:
        new_badge = "streak_7"
    elif stats.words_mastered >= 10 and "master_10" not in badges:
        new_badge = "master_10"
    elif stats.words_mastered >= 50 and "master_50" not in badges:
        new_badge = "master_50"

    if new_badge:
        badges.append(new_badge)
        stats.badges_json = json.dumps(badges, ensure_ascii=False)

    return new_badge


async def _get_or_create_stats(db: AsyncSession, user_id: int) -> UserStats:
    sid = await active_student_id(db, user_id)
    conds = [UserStats.user_id == user_id]
    if sid is not None:
        conds.append(UserStats.student_id == sid)
    result = await db.execute(select(UserStats).where(*conds))
    stats = result.scalar_one_or_none()
    if stats:
        return stats

    stats = UserStats(user_id=user_id, student_id=sid)
    db.add(stats)
    await db.commit()
    await db.refresh(stats)
    return stats


async def get_user_stats(db: AsyncSession, user_id: int) -> dict:
    stats = await _get_or_create_stats(db, user_id)
    badges = json.loads(stats.badges_json)
    badge_details = []
    for b in badges:
        if b in BADGE_DEFS:
            name, desc = BADGE_DEFS[b]
            badge_details.append({"id": b, "name": name, "desc": desc})

    return {
        "total_points": stats.total_points,
        "streak_days": stats.streak_days,
        "words_mastered": stats.words_mastered,
        "badges": badge_details,
    }


def _get_encouragement(correct: bool, level: int) -> str:
    if correct:
        msgs = [
            "太棒了！你真厉害！",
            "答对了！继续加油！",
            "非常好！你学得很快！",
            "真聪明！再来一题吧！",
        ]
        return random.choice(msgs)
    else:
        msgs = [
            "没关系，多练几次就会了！",
            "别灰心，下次一定能答对！",
            "加油，你已经很棒了！",
        ]
        return random.choice(msgs)
