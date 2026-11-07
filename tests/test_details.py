"""Every question must carry a 詳しい解説 (detail) block in the data files."""

from pathlib import Path

from quiz import load_questions

ROOT = Path(__file__).resolve().parent.parent
BANK_FILES = ("questions.json", "questions_round2.json", "questions_round3.json", "questions_round4.json", "questions_round5.json")


def _all_questions() -> list[dict]:
    questions: list[dict] = []
    for name in BANK_FILES:
        questions.extend(load_questions(ROOT / "data" / name))
    return questions


def test_all_questions_have_detail_sections() -> None:
    questions = _all_questions()
    assert len(questions) == 250
    for question in questions:
        detail = question.get("detail")
        assert isinstance(detail, dict), question["id"]
        sections = detail.get("sections")
        assert isinstance(sections, list) and len(sections) >= 2, question["id"]
        for section in sections:
            assert section.get("heading"), question["id"]
            assert section.get("bullets") or section.get("table"), question["id"]
            table = section.get("table")
            if table:
                assert table["head"] and table["rows"], question["id"]
                assert all(len(row) == len(table["head"]) for row in table["rows"]), question["id"]


def test_detail_images_exist_with_credit() -> None:
    for question in _all_questions():
        image = (question.get("detail") or {}).get("image")
        if image is None:
            continue
        assert (ROOT / image["file"]).is_file(), f"{question['id']}: {image['file']}"
        assert "https://note.com/" in image["credit"], question["id"]
        assert "ドローン・パイロット" in image["credit"], question["id"]
