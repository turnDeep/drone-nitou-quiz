"""Integration checks for both photographed exam rounds and their audit trails."""

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
ROUND2_ORIGINAL_KEY = (
    "ababccabba"  # 1-10
    "abbcbacaca"  # 11-20
    "aaccbcbccb"  # 21-30
    "cacaaaccbb"  # 31-40
    "bcbaabacbb"  # 41-50
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
        assert 2 <= len(question["explanation_highlights"]) <= 4
        assert all(term in question["explanation"] for term in question["explanation_highlights"])
        assert audit["answer_changed"] == (original["answer_index"] != question["answer_index"])
        changed = original["prompt"] != question["prompt"] or original["choices"] != question["choices"]
        assert changed == (audit["verdict"] == "question_revised"), number


def test_real_bank_initial_question_and_answer_feedback():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=10).run()
    assert not app.exception
    assert len(app.session_state["quiz_session"]["order"]) == 50
    assert not app.error and not app.success
    assert not any("原本の正答表示" in str(item.value) for item in app.caption)
    assert any('<u class="question-focus">適切でないもの</u>' in item.value for item in app.markdown)
    assert not any('<strong class="explanation-key">' in item.value for item in app.markdown)
    answer = next(item for item in app.radio if item.label == "答えを1つ選んでください")
    assert answer.value is None
    answer.set_value(2)
    next(item for item in app.button if item.label == "回答する").click().run()
    assert not app.exception
    assert any("正解です" in item.value for item in app.success)
    assert any('<strong class="explanation-key">' in item.value for item in app.markdown)
    assert any("教則第五版の該当箇所を開く" in item.value for item in app.markdown)


def test_second_round_has_all_50_with_matching_original_key_and_evidence():
    questions = load_questions(ROOT / "data/questions_round2.json")
    assert [q["id"] for q in questions] == [f"round2-{number:03}" for number in range(1, 51)]
    assert len(eligible_questions(questions, "photo")) == 50
    first_ids = {q["id"] for q in load_questions(ROOT / "data/questions.json")}
    assert first_ids.isdisjoint({q["id"] for q in questions})
    manifest = json.loads((ROOT / "docs/photo-manifest-round2.json").read_text(encoding="utf-8"))
    photos = {item["file_name"] for item in manifest["photos"]}
    assert len(photos) == 19 and manifest["round"] == 2
    assert len(ROUND2_ORIGINAL_KEY) == 50
    for number, question in enumerate(questions, 1):
        original, audit = question["original"], question["audit"]
        assert original["answer_index"] == "abc".index(ROUND2_ORIGINAL_KEY[number - 1]), number
        assert original["prompt"] and len(original["choices"]) == 3
        assert original["explanation_summary"]
        assert question["origin"]["round"] == 2
        assert question["origin"]["question_number"] == str(number)
        assert question["origin"]["source_file"] in photos
        assert question["origin"]["answer_source_file"] in photos
        reference = question["review"]["reference"]
        assert reference["pdf_page"] == reference["printed_page"] + 6
        assert reference["url"] == "https://www.mlit.go.jp/common/002010809.pdf"
        assert audit["reason"] and audit["reference_excerpt"]
        assert 2 <= len(question["explanation_highlights"]) <= 4
        assert all(term in question["explanation"] for term in question["explanation_highlights"])
        assert audit["answer_changed"] == (original["answer_index"] != question["answer_index"])
        changed = original["prompt"] != question["prompt"] or original["choices"] != question["choices"]
        assert changed == (audit["verdict"] == "question_revised"), number


def test_both_rounds_switch_cleanly_and_second_round_grades_all_50():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=10).run()
    assert not app.exception
    assert app.sidebar.radio[0].options == ["第1回", "第2回"]
    first = next(item for item in app.radio if item.label == "答えを1つ選んでください")
    first.set_value(0)
    next(item for item in app.button if item.label == "回答する").click().run()
    assert app.session_state["quiz_session"]["answers"] == {"photo-001": 0}
    app.sidebar.radio[0].set_value("第2回").run()
    assert not app.exception
    assert app.session_state["quiz_session"]["answers"] == {}
    assert app.session_state["quiz_session"]["order"][0] == "round2-001"
    questions = load_questions(ROOT / "data/questions_round2.json")
    for number, question in enumerate(questions, 1):
        assert not app.success and not app.error
        assert not any('<strong class="explanation-key">' in item.value for item in app.markdown)
        answer = next(item for item in app.radio if item.label == "答えを1つ選んでください")
        assert answer.value is None
        answer.set_value(question["answer_index"])
        next(item for item in app.button if item.label == "回答する").click().run()
        assert not app.exception
        assert any("正解です" in item.value for item in app.success)
        assert any('<strong class="explanation-key">' in item.value for item in app.markdown)
        next(item for item in app.button if item.label == ("結果を見る" if number == 50 else "次の問題へ")).click().run()
        assert not app.exception
    assert any("50問中 50問正解" in item.value for item in app.success)
    app.sidebar.radio[0].set_value("第1回").run()
    assert not app.exception
    assert app.session_state["quiz_session"]["order"][0] == "photo-001"
    assert app.session_state["quiz_session"]["answers"] == {}
    assert not (ROOT / "data/demo_questions.json").exists()
