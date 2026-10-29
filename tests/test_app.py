"""Exercise the actual UI with isolated test banks, without changing real data."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.test_quiz import document, example


@pytest.fixture
def app(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = (root / "app.py").read_text(encoding="utf-8")
    (tmp_path / "app.py").write_text(source, encoding="utf-8")
    if (root / "styles.css").exists():
        (tmp_path / "styles.css").write_text((root / "styles.css").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "questions.json").write_text(json.dumps(document()), encoding="utf-8")
    first, second = example("round2-001"), example("round2-002")
    second["prompt"] = "2問目を選択してください。"
    (tmp_path / "data" / "questions_round2.json").write_text(json.dumps(document(first, second)), encoding="utf-8")
    return AppTest.from_file(str(tmp_path / "app.py"), default_timeout=10)


def button(app, label):
    return next(item for item in app.button if item.label == label)


def answer_radio(app):
    return next(item for item in app.radio if item.label == "答えを1つ選んでください")


def second_round(app):
    app.run()
    assert not app.exception
    app.sidebar.radio[0].set_value("第2回").run()
    assert not app.exception
    return app


def test_default_has_no_photo_questions_and_no_answer_leak(app):
    app.run()
    assert not app.exception
    assert any("第1回の問題は未登録" in item.value for item in app.info)
    assert not app.subheader
    assert not app.success


def test_no_selection_is_not_scored_and_explanation_stays_hidden(app):
    second_round(app)
    assert answer_radio(app).value is None
    assert not any("テスト用の解説" in str(item.value) for item in app.markdown)
    button(app, "回答する").click().run()
    assert not app.exception
    assert app.session_state["quiz_session"]["answers"] == {}
    assert any("選択肢を1つ" in item.value for item in app.warning)
    assert not app.success


def test_wrong_answer_locked_next_question_correct_and_retry(app):
    second_round(app)
    answer_radio(app).set_value(0)
    button(app, "回答する").click().run()
    assert not app.exception
    assert any("不正解" in item.value for item in app.error)
    assert any("テスト用の解説" in str(item.value) for item in app.markdown)
    assert not any(item.label == "回答する" for item in app.button)
    assert app.session_state["quiz_session"]["answers"] == {"round2-001": 0}
    button(app, "次の問題へ").click().run()
    assert not app.exception
    assert answer_radio(app).value is None
    assert not app.error
    answer_radio(app).set_value(1)
    button(app, "回答する").click().run()
    assert any("正解です" in item.value for item in app.success)
    button(app, "結果を見る").click().run()
    assert any("2問中 1問正解" in item.value for item in app.success)
    button(app, "間違いだけ再挑戦").click().run()
    assert not app.exception
    assert app.session_state["quiz_session"]["order"] == ["round2-001"]
    assert app.session_state["quiz_session"]["answers"] == {}
    assert answer_radio(app).value is None


def test_round_change_does_not_mix_progress_between_banks(app):
    second_round(app)
    answer_radio(app).set_value(1)
    button(app, "回答する").click().run()
    app.sidebar.radio[0].set_value("第1回").run()
    assert not app.exception
    assert any("第1回の問題は未登録" in item.value for item in app.info)
    assert not app.success
    assert not app.subheader
    app.sidebar.radio[0].set_value("第2回").run()
    assert app.session_state["quiz_session"]["answers"] == {}


def test_pending_photo_is_excluded_from_ui(app, tmp_path):
    pending = example()
    pending["review"]["status"] = "pending"
    pending["review"]["reference"] = {}
    pending["answer_index"] = None
    pending["explanation"] = ""
    (tmp_path / "data" / "questions.json").write_text(json.dumps(document(pending)), encoding="utf-8")
    app.run()
    assert not app.exception
    assert any("確認待ち・修正待ち" in item.value for item in app.info)
    assert not app.subheader


def test_bad_verified_photo_shows_data_error_instead_of_quiz(app, tmp_path):
    invalid = example()
    invalid["review"]["reference"]["url"] = "https://example.com/guide.pdf"
    (tmp_path / "data" / "questions.json").write_text(json.dumps(document(invalid)), encoding="utf-8")
    app.run()
    assert not app.exception
    assert any("国土交通省の公式PDF" in item.value for item in app.error)
    assert not app.subheader
