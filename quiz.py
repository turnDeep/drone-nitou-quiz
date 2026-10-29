"""Question validation and session-only quiz logic, independent of Streamlit."""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


class QuestionDataError(ValueError):
    """A readable data error that can be shown without a Python traceback."""


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive_integer(value: object) -> bool:
    return type(value) is int and value > 0


def _official_pdf(url: object) -> bool:
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        return (
            parsed.scheme == "https"
            and (host == "mlit.go.jp" or host.endswith(".mlit.go.jp"))
            and parsed.path.lower().endswith(".pdf")
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
        )
    except ValueError:
        return False


def validate_questions(document: object) -> list[dict]:
    """Validate all records; only reviewed records become eligible separately."""
    if not isinstance(document, dict):
        raise QuestionDataError("問題データの先頭はオブジェクトにしてください。")
    if type(document.get("schema_version")) is not int or document["schema_version"] != 1:
        raise QuestionDataError("問題データの schema_version は 1 が必要です。")
    questions = document.get("questions")
    if not isinstance(questions, list):
        raise QuestionDataError("問題データには questions の配列が必要です。")
    seen: set[str] = set()
    for number, question in enumerate(questions, start=1):
        prefix = f"問題データ {number} 件目"
        if not isinstance(question, dict):
            raise QuestionDataError(f"{prefix}: オブジェクトが必要です。")
        for key in ("id", "category", "prompt"):
            if not _text(question.get(key)):
                raise QuestionDataError(f"{prefix}: {key} を入力してください。")
        if question["id"] in seen:
            raise QuestionDataError(f"{prefix}: 問題IDが重複しています。")
        seen.add(question["id"])
        choices = question.get("choices")
        if not isinstance(choices, list) or len(choices) != 3 or not all(map(_text, choices)):
            raise QuestionDataError(f"{prefix}: 空欄のない選択肢を3個指定してください。")
        if len({choice.strip() for choice in choices}) != 3:
            raise QuestionDataError(f"{prefix}: 選択肢が重複しています。")
        origin = question.get("origin")
        if not isinstance(origin, dict) or origin.get("kind") not in ("photo", "original_sample"):
            raise QuestionDataError(f"{prefix}: 問題の出典種別が不正です。")
        if not isinstance(origin.get("source_file"), str) or not isinstance(origin.get("question_number"), str):
            raise QuestionDataError(f"{prefix}: 出典ファイル名・問題番号は文字列で指定してください。")
        review = question.get("review")
        if not isinstance(review, dict) or review.get("status") not in ("verified", "pending", "needs_revision"):
            raise QuestionDataError(f"{prefix}: 照合状態が不正です。")
        answer = question.get("answer_index")
        if answer is not None and (type(answer) is not int or answer not in range(3)):
            raise QuestionDataError(f"{prefix}: 正答番号は0・1・2のいずれかです。")
        if not isinstance(question.get("explanation"), str):
            raise QuestionDataError(f"{prefix}: 解説は文字列で指定してください。")
        highlights = question.get("explanation_highlights", [])
        if not isinstance(highlights, list) or not all(
            _text(term) and term in question["explanation"] for term in highlights
        ):
            raise QuestionDataError(f"{prefix}: 赤字にする語句は解説に含まれる文字列の配列で指定してください。")
        if review["status"] != "verified":
            continue
        if answer is None or not _text(question["explanation"]):
            raise QuestionDataError(f"{prefix}: 照合済み問題には正答と解説が必要です。")
        if type(review.get("edition")) is not int or review["edition"] != 5:
            raise QuestionDataError(f"{prefix}: 出題には教則第五版との照合が必要です。")
        try:
            checked_on = review.get("checked_on", "")
            checked = date.fromisoformat(checked_on)
            if checked.isoformat() != checked_on or checked > date.today():
                raise ValueError
        except (ValueError, TypeError):
            raise QuestionDataError(f"{prefix}: 有効な照合日（YYYY-MM-DD）が必要です。") from None
        reference = review.get("reference")
        if not isinstance(reference, dict) or not _official_pdf(reference.get("url")):
            raise QuestionDataError(f"{prefix}: 国土交通省の公式PDF（HTTPS）の根拠URLが必要です。")
        if not _text(reference.get("section")) or not all(
            _positive_integer(reference.get(key)) for key in ("printed_page", "pdf_page")
        ):
            raise QuestionDataError(f"{prefix}: 根拠の節・本文ページ・PDF通算ページが必要です。")
        if not _text(review.get("note")):
            raise QuestionDataError(f"{prefix}: 照合メモが必要です。")
        if origin["kind"] == "photo" and not _text(origin["source_file"]):
            raise QuestionDataError(f"{prefix}: 写真由来の照合済み問題には写真のファイル名が必要です。")
    return questions


def load_questions(path: str | Path) -> list[dict]:
    try:
        with Path(path).open(encoding="utf-8-sig") as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise QuestionDataError("問題ファイルを読み込めません。JSONの形式とファイルを確認してください。") from None
    return validate_questions(document)


def eligible_questions(questions: list[dict], origin_kind: str) -> list[dict]:
    return [
        question for question in questions
        if question["review"]["status"] == "verified"
        and question["review"].get("edition") == 5
        and question["origin"]["kind"] == origin_kind
    ]


def create_session(questions: list[dict], shuffle: bool = False) -> dict:
    order = [question["id"] for question in questions]
    if shuffle:
        random.shuffle(order)
    return {"order": order, "position": 0, "answers": {}}


def submit_answer(session: dict, question: dict, selection: int | None) -> bool:
    """Return True only for the first valid submission; never change a locked answer."""
    if session["position"] >= len(session["order"]) or session["order"][session["position"]] != question["id"]:
        raise ValueError("現在の問題ではありません。")
    if question["id"] in session["answers"]:
        return False
    if type(selection) is not int or selection not in range(3):
        raise ValueError("選択肢を1つ選んでから回答してください。")
    session["answers"][question["id"]] = selection
    return True


def advance(session: dict) -> None:
    if session["position"] >= len(session["order"]):
        return
    if session["order"][session["position"]] not in session["answers"]:
        raise ValueError("回答してから次の問題に進んでください。")
    session["position"] += 1


def score(session: dict, questions: list[dict]) -> tuple[int, int]:
    lookup = {question["id"]: question for question in questions}
    correct = sum(
        selection == lookup[question_id]["answer_index"]
        for question_id, selection in session["answers"].items()
    )
    return correct, len(session["answers"])


def missed_questions(session: dict, questions: list[dict]) -> list[dict]:
    lookup = {question["id"]: question for question in questions}
    return [
        lookup[question_id] for question_id in session["order"]
        if question_id in session["answers"]
        and session["answers"][question_id] != lookup[question_id]["answer_index"]
    ]
