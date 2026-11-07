import json

import pytest

from quiz import (
    RANDOM_BATCH_SIZE, QuestionDataError, advance, create_random_session, create_session,
    decode_progress, draw_questions, eligible_questions, encode_progress,
    extend_random_session, load_questions, missed_questions, score, session_from_progress,
    submit_answer, validate_questions,
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


def test_progress_round_trip_restores_order_position_and_answers():
    first, second = example(), example("photo-002")
    session = create_session([first, second])
    submit_answer(session, first, 0)
    advance(session)
    token = encode_progress(1, "すべて", False, session)
    progress = decode_progress(token)
    assert progress == {
        "bank_index": 1, "category": "すべて", "shuffle": False,
        "order": ["photo-001", "photo-002"], "position": 1, "answers": [0, None],
    }
    assert session_from_progress(progress, [first, second]) == session


def test_progress_round_trip_for_finished_and_retry_sessions():
    first, second = example(), example("photo-002")
    session = create_session([first, second])
    submit_answer(session, first, 1)
    advance(session)
    submit_answer(session, second, 1)
    advance(session)
    progress = decode_progress(encode_progress(0, "確認用", True, session))
    assert session_from_progress(progress, [first, second]) == session
    retry = create_session([first])
    retry_progress = decode_progress(encode_progress(0, "確認用", False, retry))
    assert session_from_progress(retry_progress, [first, second]) == retry


def test_decode_progress_rejects_broken_or_tampered_tokens():
    first, second = example(), example("photo-002")
    session = create_session([first, second])
    submit_answer(session, first, 0)
    advance(session)
    valid = decode_progress(encode_progress(1, "すべて", False, session))

    def token(**changes):
        payload = {
            "bank_index": valid["bank_index"], "category": valid["category"],
            "shuffle": valid["shuffle"], "order": valid["order"],
            "position": valid["position"], "answers": valid["answers"],
        }
        payload.update(changes)
        return encode_progress(
            payload["bank_index"], payload["category"], payload["shuffle"],
            {"order": payload["order"], "position": payload["position"],
             "answers": {qid: sel for qid, sel in zip(payload["order"], payload["answers"]) if sel is not None}},
        )

    assert decode_progress(None) is None
    assert decode_progress("") is None
    assert decode_progress("!!!not-a-token!!!") is None
    assert decode_progress("aGVsbG8") is None  # base64 of non-JSON text
    assert decode_progress(token(position=0, answers=[0, 1])) is None  # answer beyond position
    assert decode_progress(token(answers=[None, None])) is None  # gap before position
    assert decode_progress(token(position=3)) is None
    assert decode_progress(token(order=["photo-001", "photo-001"], answers=[0, None])) is None


def test_session_from_progress_rejects_unknown_question_ids():
    first, second = example(), example("photo-002")
    session = create_session([first, second])
    progress = decode_progress(encode_progress(2, "すべて", False, session))
    progress["order"] = ["photo-001", "missing-999"]
    assert session_from_progress(progress, [first, second]) is None


def test_random_draw_never_repeats_and_skips_excluded_ids():
    pool = [example(f"photo-{number:03}") for number in range(1, 26)]
    drawn = draw_questions(pool, 10)
    assert len(drawn) == 10
    assert len({question["id"] for question in drawn}) == 10
    rest = draw_questions(pool, 100, excluded_ids=[question["id"] for question in drawn])
    assert len(rest) == 15
    assert {question["id"] for question in drawn}.isdisjoint(
        question["id"] for question in rest
    )


def test_random_session_extends_until_pool_is_exhausted():
    pool = [example(f"photo-{number:03}") for number in range(1, 26)]
    session = create_random_session(pool)
    assert len(session["order"]) == RANDOM_BATCH_SIZE
    assert session["position"] == 0 and session["answers"] == {}
    assert extend_random_session(session, pool) == 10
    assert extend_random_session(session, pool) == 5
    assert extend_random_session(session, pool) == 0
    assert len(session["order"]) == 25
    assert len(set(session["order"])) == 25
    assert set(session["order"]) == {question["id"] for question in pool}


def test_random_session_progress_round_trip_keeps_drawn_order_after_extend():
    pool = [example(f"photo-{number:03}") for number in range(1, 13)]
    session = create_random_session(pool)
    lookup = {question["id"]: question for question in pool}
    for _ in range(2):
        current = lookup[session["order"][session["position"]]]
        assert submit_answer(session, current, 1)
        advance(session)
    assert extend_random_session(session, pool) == 2
    progress = decode_progress(encode_progress(5, "すべて", False, session))
    assert progress is not None
    assert session_from_progress(progress, pool) == session


def test_load_utf8_bom(tmp_path):
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(document(example()), ensure_ascii=False), encoding="utf-8-sig")
    assert load_questions(path)[0]["id"] == "photo-001"
