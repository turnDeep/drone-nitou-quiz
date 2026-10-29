"""Japanese three-choice study app for verified fifth-edition questions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import streamlit as st

from quiz import (
    QuestionDataError, advance, create_session, eligible_questions,
    load_questions, missed_questions, score, submit_answer,
)

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="二等ドローン学科 | 三択レッスン", page_icon="✈️", layout="centered")
st.markdown(
    """<style>
    .block-container {max-width: 800px; padding-top: 2rem;}
    div[data-testid="stRadio"] label {padding: .35rem 0;}
    div[data-testid="stMetricValue"] {font-size: 1.65rem;}
    h1 {font-size: clamp(1.7rem, 5vw, 2.3rem) !important;}
    </style>""",
    unsafe_allow_html=True,
)

st.caption("無人航空機操縦士 / 二等学科の学習")
st.title("三択で、ひとつずつ。")
st.write("選んで回答すると、正誤と解説・教則第五版の根拠を確認できます。")

with st.sidebar:
    st.header("学習メニュー")
    mode = st.radio("問題の種類", ["写真の問題", "操作サンプル"], key="source_mode")
    st.caption("教則第五版との照合済み問題だけを出題します。")
    st.divider()
    st.caption("学習履歴はこのセッション内だけに保存します。ブラウザーを閉じたり接続が切れたりすると、履歴が失われる場合があります。")

is_demo = mode == "操作サンプル"
if st.session_state.get("active_source") != mode:
    st.session_state.active_source = mode
    st.session_state.pop("quiz_signature", None)
    st.session_state.pop("quiz_session", None)
origin_kind = "original_sample" if is_demo else "photo"
path = ROOT / "data" / ("demo_questions.json" if is_demo else "questions.json")
if is_demo:
    st.warning("操作サンプルは写真由来ではありません。アプリの使い方を確認するための独自問題です。")

try:
    all_questions = load_questions(path)
except QuestionDataError as error:
    st.error(str(error))
    st.stop()

source_questions = [question for question in all_questions if question["origin"]["kind"] == origin_kind]
questions = eligible_questions(all_questions, origin_kind)
pending_count = len(source_questions) - len(questions)

if not source_questions:
    st.info("写真の問題は未登録です。写真の受領後、問題文・正答・解説を教則第五版と照合して登録します。" if not is_demo else "操作サンプルはまだ登録されていません。")
    st.caption("サイドバーの「操作サンプル」で、回答と解説表示の流れを試せます。" if not is_demo else "問題ファイルを確認してください。")
    st.stop()

if pending_count:
    st.info(f"確認待ち・修正待ちの {pending_count} 問は出題していません。")
if not questions:
    st.info("第五版との照合済み問題がまだありません。照合完了後に学習できます。")
    st.stop()

with st.sidebar:
    categories = sorted({question["category"] for question in questions})
    category = st.selectbox("出題分野", ["すべて"] + categories)
    shuffle = st.checkbox("問題の順番をランダムにする", value=False)

if category != "すべて":
    questions = [question for question in questions if question["category"] == category]

signature = hashlib.sha256(json.dumps([mode, category, shuffle, questions], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
if st.session_state.get("quiz_signature") != signature:
    st.session_state.quiz_signature = signature
    st.session_state.quiz_session = create_session(questions, shuffle)
    st.session_state.quiz_generation = st.session_state.get("quiz_generation", 0) + 1

session = st.session_state.quiz_session
lookup = {question["id"]: question for question in questions}
correct, answered = score(session, questions)
total = len(session["order"])
columns = st.columns(3)
columns[0].metric("回答済み", f"{answered} / {total}")
columns[1].metric("正解", f"{correct} 問")
columns[2].metric("正答率", f"{correct / answered:.0%}" if answered else "—")
st.progress(answered / total, text=f"{answered}問を回答しました")
st.caption("出題分野や問題の種類を変更すると、学習を最初から開始します。")


def restart(selected: list[dict]) -> None:
    st.session_state.quiz_session = create_session(selected, shuffle)
    st.session_state.quiz_generation += 1
    st.rerun()


if session["position"] >= total:
    st.success(f"おつかれさまでした。{total}問中 {correct}問正解です。")
    missed = missed_questions(session, questions)
    if missed:
        st.write("間違えた問題をもう一度確認しましょう。")
        if st.button("間違いだけ再挑戦", type="primary", use_container_width=True):
            restart(missed)
    else:
        st.write("すべて正解です。解説で確認した内容を、実際の学習にも役立ててください。")
    if st.button("最初から学習する", use_container_width=True):
        restart(questions)
    st.stop()

question = lookup[session["order"][session["position"]]]
question_id = question["id"]
is_answered = question_id in session["answers"]
st.divider()
st.caption(f"第{session['position'] + 1}問 / {total}問 · {question['category']}")
st.subheader(question["prompt"])

if not is_answered:
    with st.form(f"answer_form_{st.session_state.quiz_generation}_{question_id}"):
        selection = st.radio(
            "答えを1つ選んでください",
            options=list(range(3)),
            index=None,
            format_func=lambda value: f"{['A', 'B', 'C'][value]}. {question['choices'][value]}",
            key=f"choice_{st.session_state.quiz_generation}_{question_id}",
        )
        submitted = st.form_submit_button("回答する", type="primary", use_container_width=True)
    if submitted:
        try:
            submit_answer(session, question, selection)
        except ValueError as error:
            st.warning(str(error))
        else:
            st.rerun()
else:
    selected = session["answers"][question_id]
    answer = question["answer_index"]
    if selected == answer:
        st.success("正解です！")
    else:
        st.error("不正解です。解説を確認してみましょう。")
    st.write(f"**あなたの回答：{['A', 'B', 'C'][selected]}. {question['choices'][selected]}**")
    st.write(f"**正答：{['A', 'B', 'C'][answer]}. {question['choices'][answer]}**")
    with st.container(border=True):
        st.markdown("### 解説")
        st.write(question["explanation"])
        review = question["review"]
        reference = review["reference"]
        st.markdown(f"[教則第五版の該当箇所を開く]({reference['url']}#page={reference['pdf_page']})")
        st.caption(f"{reference['section']} / 本文 {reference['printed_page']}ページ / PDF通算 {reference['pdf_page']}ページ")
        st.caption(f"照合日：{review['checked_on']}")
        st.write(f"照合メモ：{review['note']}")
    if st.button("結果を見る" if session["position"] + 1 == total else "次の問題へ", type="primary", use_container_width=True):
        advance(session)
        st.rerun()

with st.sidebar:
    st.divider()
    if st.button("この学習をやり直す", use_container_width=True):
        restart(questions)
