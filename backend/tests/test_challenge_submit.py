"""闯关答题判分回归测试。

前端只能从题目响应里拿到字段再回传给 /challenge/submit。
后端 submit 用 word_str 去 get_word_detail 反查正确答案，
所以题目响应必须始终带一个“底层生字”标识（target_word），
且用它提交正确答案时必须判为正确——尤其是一类字（level 1，
correct_answer 是字义而非生字本身）与造句（level 3）。
"""
from tests.conftest import make_user
from app.services.challenge_service import generate_challenge, submit_answer


async def test_challenge_response_carries_target_word_and_scores_correct(db):
    user = await make_user(db)
    challenge = await generate_challenge(db, user.id, "chinese", 3)
    assert challenge is not None

    # 新用户第一题应为 level 1（认读）：correct_answer 是字义，word 才是生字
    assert challenge["level"] == 1
    assert challenge["correct_answer"] != challenge["word"]

    # 题目必须提供一个稳定的底层生字标识，供前端原样回传
    target_word = challenge["target_word"]
    assert target_word == challenge["word"]

    # 用正确答案提交，必须判对
    result = await submit_answer(
        db=db,
        user_id=user.id,
        word_str=target_word,
        subject="chinese",
        grade=3,
        level=challenge["level"],
        answer=challenge["correct_answer"],
        streak=0,
    )
    assert result["correct"] is True
    assert result["correct_answer"] == challenge["correct_answer"]
    assert result["points_earned"] > 0
