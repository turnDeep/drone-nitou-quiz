"""Integration checks for the actual 50-question photo bank and its audit trail."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from quiz import eligible_questions, load_questions

ROOT = Path(__file__).resolve().parents[1]
# Independently transcribed from the answer table in photo 10, in question order.
ORIGINAL_KEY = (
    "ccabaaaaca"  # 1-10
    "caccabcbbc"  # 11-20
    "aaabbaccca"  # 21-30
    "accbaabccc"  # 31-40
    "baabbccacb"  # 41-50
)


def test_photo_bank_has_all_50_with_matching_original_key_and_evidence():
    questions = load_questions(ROOT / "data/questions.json")
    assert [q["id"] for q in questions] == [f"photo-{number:03}" for number in range(1, 51)]
    assert len(eligible_questions(questions, "photo")) == 50
    assert eligible_questions(questions, "original_sample") == []
    manifest = json.loads((ROOT / "docs/photo-manifest.json").read_text(encoding="utf-8"))
    photos = {item["file_name"] for item in manifest["photos"]}
    assert len(photos) == 20
    assert len(ORIGINAL_KEY) == 50
    for number, question in enumerate(questions, 1):
        original, audit = question["original"], question["audit"]
        assert original["answer_index"] == "abc".index(ORIGINAL_KEY[number - 1]), number
        assert original["prompt"] and len(original["choices"]) == 3
        assert original["explanation_summary"]
        assert question["origin"]["question_number"] == str(number)
        assert question["origin"]["source_file"] in photos
        assert question["origin"]["answer_source_file"] in photos
        assert question["review"]["reference"]["pdf_page"] == question["review"]["reference"]["printed_page"] + 6
        assert question["review"]["reference"]["url"] == "https://www.mlit.go.jp/common/002010809.pdf"
        assert audit["reason"] and audit["reference_excerpt"]
        assert audit["answer_changed"] == (original["answer_index"] != question["answer_index"])
        changed = original["prompt"] != question["prompt"] or original["choices"] != question["choices"]
        assert changed == (audit["verdict"] == "question_revised"), number


def test_real_bank_initial_question_and_answer_feedback():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=10).run()
    assert not app.exception
    assert len(app.session_state["quiz_session"]["order"]) == 50
    assert not app.error and not app.success
    assert not any("原本の正答表示" in str(item.value) for item in app.caption)
    answer = next(item for item in app.radio if item.label == "答えを1つ選んでください")
    assert answer.value is None
    answer.set_value(2)
    next(item for item in app.button if item.label == "回答する").click().run()
    assert not app.exception
    assert any("正解です" in item.value for item in app.success)
    assert any("教則第五版の該当箇所を開く" in item.value for item in app.markdown)
