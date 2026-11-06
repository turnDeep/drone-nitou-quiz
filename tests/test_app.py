"""Exercise the actual UI with isolated test banks, without changing real data."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from quiz import encode_progress
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
    app = AppTest.from_file(str(tmp_path / "app.py"), default_timeout=10)
    app.session_state["source_mode"] = "第1回"
    return app


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


def fresh_app(tmp_path):
    """A brand-new AppTest (empty session state) against the same test files."""
    return AppTest.from_file(str(tmp_path / "app.py"), default_timeout=10)


def test_progress_saved_to_url_and_restored_after_session_loss(app, tmp_path):
    second_round(app)
    answer_radio(app).set_value(0)
    button(app, "回答する").click().run()
    button(app, "次の問題へ").click().run()
    assert app.session_state["quiz_session"]["position"] == 1
    token = app.query_params["p"]
    assert token

    resumed = fresh_app(tmp_path)
    resumed.query_params["p"] = token
    resumed.run()
    assert not resumed.exception
    assert resumed.session_state["source_mode"] == "第2回"
    assert resumed.session_state["quiz_session"]["order"] == ["round2-001", "round2-002"]
    assert resumed.session_state["quiz_session"]["position"] == 1
    assert resumed.session_state["quiz_session"]["answers"] == {"round2-001": 0}
    answer_radio(resumed).set_value(1)
    button(resumed, "回答する").click().run()
    button(resumed, "結果を見る").click().run()
    assert any("2問中 1問正解" in item.value for item in resumed.success)

    finished = fresh_app(tmp_path)
    finished.query_params["p"] = resumed.query_params["p"]
    finished.run()
    assert not finished.exception
    assert finished.session_state["quiz_session"]["position"] == 2
    assert any("2問中 1問正解" in item.value for item in finished.success)


def test_live_session_is_not_overwritten_by_url_token(app):
    second_round(app)
    answer_radio(app).set_value(1)
    button(app, "回答する").click().run()
    assert app.session_state["quiz_session"]["answers"] == {"round2-001": 1}
    app.query_params["p"] = encode_progress(
        1, "すべて", False,
        {"order": ["round2-001", "round2-002"], "position": 0, "answers": {}},
    )
    app.run()
    assert not app.exception
    assert app.session_state["quiz_session"]["answers"] == {"round2-001": 1}


def test_broken_progress_token_starts_fresh_without_error(app, tmp_path):
    (tmp_path / "data" / "questions_round3.json").write_text(json.dumps(document()), encoding="utf-8")
    fresh = fresh_app(tmp_path)
    fresh.query_params["p"] = "broken-token!!!"
    fresh.run()
    assert not fresh.exception
    if "quiz_session" in fresh.session_state:
        assert fresh.session_state["quiz_session"]["position"] == 0
        assert fresh.session_state["quiz_session"]["answers"] == {}


def test_progress_token_with_unknown_question_starts_fresh(app, tmp_path):
    fresh = fresh_app(tmp_path)
    fresh.query_params["p"] = encode_progress(
        1, "すべて", False,
        {"order": ["round2-001", "missing-999"], "position": 0, "answers": {}},
    )
    fresh.run()
    assert not fresh.exception
    assert fresh.session_state["quiz_session"]["order"] == ["round2-001", "round2-002"]
    assert fresh.session_state["quiz_session"]["answers"] == {}


def test_bad_verified_photo_shows_data_error_instead_of_quiz(app, tmp_path):
    invalid = example()
    invalid["review"]["reference"]["url"] = "https://example.com/guide.pdf"
    (tmp_path / "data" / "questions.json").write_text(json.dumps(document(invalid)), encoding="utf-8")
    app.run()
    assert not app.exception
    assert any("国土交通省の公式PDF" in item.value for item in app.error)
    assert not app.subheader
