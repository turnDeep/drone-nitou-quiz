import json

import pytest

from quiz import (
    QuestionDataError, advance, create_session, eligible_questions,
    load_questions, missed_questions, score, submit_answer, validate_questions,
)


def example(question_id="photo-001", kind="photo"):
    return {
        "id": question_id, "category": "確認用", "prompt": "選択してください。",
        "choices": ["選択肢A", "選択肢B", "選択肢C"], "answer_index": 1,
        "explanation": "テスト用の解説です。",
        "origin": {"kind": kind, "source_file": "test.jpg", "question_number": "1"},
        "review": {
            "status": "verified", "edition": 5, "checked_on": "2026-07-14",
            "reference": {"url": "https://www.mlit.go.jp/common/002010809.pdf", "section": "2.1", "printed_page": 2, "pdf_page": 8},
            "note": "テスト用の照合記録です。",
        },
    }


def document(*questions):
    return {"schema_version": 1, "questions": list(questions)}


def test_empty_production_bank_is_valid():
    assert validate_questions(document()) == []


def test_only_verified_fifth_edition_with_matching_origin_is_eligible():
    photo = example()
    pending = example("pending")
    pending["review"]["status"] = "pending"
    pending["answer_index"] = None
    pending["explanation"] = ""
    pending["review"]["reference"] = {}
    revised = example("revised")
    revised["review"]["status"] = "needs_revision"
    demo = example("demo", "original_sample")
    questions = validate_questions(document(photo, pending, revised, demo))
    assert eligible_questions(questions, "photo") == [photo]
    assert eligible_questions(questions, "original_sample") == [demo]


@pytest.mark.parametrize("change", [
    lambda q: q.update(choices=["a", "b"]),
    lambda q: q.update(choices=["a", " a ", "b"]),
    lambda q: q.update(answer_index=True),
    lambda q: q.update(answer_index=3),
    lambda q: q.update(answer_index=None),
    lambda q: q["review"].update(edition=4),
    lambda q: q["review"].update(checked_on="2099-01-01"),
    lambda q: q["review"].update(checked_on="invalid"),
    lambda q: q["review"].update(checked_on="20260714"),
    lambda q: q["review"].update(status=[]),
    lambda q: q["origin"].update(kind=[]),
    lambda q: q["review"].update(note=""),
    lambda q: q["review"]["reference"].update(url="https://mlit.go.jp.example.com/guide.pdf"),
    lambda q: q["review"]["reference"].update(url="https://user:pass@www.mlit.go.jp/guide.pdf"),
    lambda q: q["review"]["reference"].update(url="http://www.mlit.go.jp/guide.pdf"),
    lambda q: q["review"]["reference"].update(pdf_page=True),
    lambda q: q["origin"].update(source_file=""),
])
def test_invalid_or_incomplete_verified_record_is_rejected(change):
    question = example()
    change(question)
    with pytest.raises(QuestionDataError):
        validate_questions(document(question))


def test_duplicate_ids_are_rejected():
    with pytest.raises(QuestionDataError, match="重複"):
        validate_questions(document(example(), example()))


def test_invalid_json_is_readable_error(tmp_path):
    path = tmp_path / "bank.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(QuestionDataError, match="読み込めません"):
        load_questions(path)


def test_first_answer_locks_and_next_question_starts_unanswered():
    first, second = example(), example("photo-002")
    session = create_session([first, second])
    with pytest.raises(ValueError, match="選択肢"):
        submit_answer(session, first, None)
    with pytest.raises(ValueError, match="回答して"):
        advance(session)
    assert score(session, [first, second]) == (0, 0)
    assert submit_answer(session, first, 0)
    assert not submit_answer(session, first, 1)
    assert score(session, [first, second]) == (0, 1)
    advance(session)
    assert second["id"] not in session["answers"]
    assert submit_answer(session, second, 1)
    assert score(session, [first, second]) == (1, 2)
    advance(session)
    assert session["position"] == 2
    assert missed_questions(session, [first, second]) == [first]
    retry = create_session(missed_questions(session, [first, second]))
    assert retry["order"] == [first["id"]]
    assert retry["answers"] == {}


def test_wrong_question_cannot_be_submitted():
    first, second = example(), example("photo-002")
    with pytest.raises(ValueError, match="現在の問題"):
        submit_answer(create_session([first, second]), second, 1)


def test_load_utf8_bom(tmp_path):
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(document(example()), ensure_ascii=False), encoding="utf-8-sig")
    assert load_questions(path)[0]["id"] == "photo-001"
