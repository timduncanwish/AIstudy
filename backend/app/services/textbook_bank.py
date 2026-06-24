"""按学期（上/下册）组织的教材预习数据加载层。

与 word_bank.py 分离：word_bank 服务于「字词闯关」游戏（含干扰项），
textbook_bank 服务于「字词句课前预习」，数据按真实教材生字表/词汇表落库。

数据文件：app/data/textbooks/{subject}_g{grade}.json
结构（语文）：
    {
      "subject": "chinese", "grade": 3, "version": "统编版",
      "source_url": "...",
      "semesters": {
        "上册": {"units": [
          {"unit": 1, "title": "...", "source_status": "待人工复核",
           "first_class": [{"word":"晨","pinyin":"chén","meaning":"...","examples":["早晨"]}],
           "second_class": [{"word":"...","pinyin":"...","meaning":"..."}],
           "phrases": ["..."], "sentences": ["..."]}
        ]},
        "下册": {"units": [...]}
      }
    }
结构（英语）：unit 内用 "words":[{"word","phonetic","meaning"}], "phrases", "sentences"。
"""

import json
import os

_textbook_cache: dict[tuple[str, int], dict | None] = {}

SEMESTERS = ("上册", "下册")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "textbooks")


def load_textbook(subject: str, grade: int) -> dict | None:
    key = (subject, grade)
    if key in _textbook_cache:
        return _textbook_cache[key]

    filepath = os.path.join(_DATA_DIR, f"{subject}_g{grade}.json")
    if not os.path.exists(filepath):
        _textbook_cache[key] = None
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    _textbook_cache[key] = data
    return data


def get_semester_units(subject: str, grade: int, semester: str) -> list[dict]:
    """返回某册（上/下）的单元列表；无数据返回空列表。"""
    data = load_textbook(subject, grade)
    if not data:
        return []
    semester_data = data.get("semesters", {}).get(semester)
    if not semester_data:
        return []
    return semester_data.get("units", [])


def has_semester_data(subject: str, grade: int, semester: str) -> bool:
    return len(get_semester_units(subject, grade, semester)) > 0


def textbook_meta(subject: str, grade: int) -> dict:
    data = load_textbook(subject, grade)
    return {
        "version": (data or {}).get("version", "统编版" if subject == "chinese" else "PEP人教版"),
        "source_url": (data or {}).get("source_url", ""),
        "source_name": (data or {}).get(
            "source_name", "国家中小学智慧教育平台 / 人教社中小学教材电子版"
        ),
    }
