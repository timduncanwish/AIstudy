import json
import os

_word_cache: dict[tuple[str, int], dict] = {}


def _load_word_bank(subject: str, grade: int) -> dict | None:
    key = (subject, grade)
    if key in _word_cache:
        return _word_cache[key]

    filename = f"{subject}_g{grade}.json"
    filepath = os.path.join(os.path.dirname(__file__), "..", "data", "word_banks", filename)

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    _word_cache[key] = data
    return data


def get_words_for_grade(subject: str, grade: int) -> list[dict]:
    data = _load_word_bank(subject, grade)
    if not data:
        return []

    words = []
    for unit in data.get("units", []):
        for word in unit.get("words", []):
            word["_unit"] = unit.get("unit", 0)
            word["_unit_title"] = unit.get("title", "")
            words.append(word)
    return words


def get_words_by_unit(subject: str, grade: int, unit: int) -> list[dict]:
    data = _load_word_bank(subject, grade)
    if not data:
        return []

    for u in data.get("units", []):
        if u.get("unit") == unit:
            return u.get("words", [])
    return []


def get_word_detail(subject: str, grade: int, word_str: str) -> dict | None:
    words = get_words_for_grade(subject, grade)
    for w in words:
        if w["word"] == word_str:
            return w
    return None
