"""Japanese three-choice study app for verified fifth-edition questions."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import streamlit as st

from formatting import explanation_html, question_html
from quiz import (
    QuestionDataError, advance, create_session, eligible_questions,
    load_questions, missed_questions, score, submit_answer,
)

ROOT = Path(__file__).resolve().parent
BANK_FILES = {"第1回": "questions.json", "第2回": "questions_round2.json"}

st.set_page_config(
    page_title="二等ドローン学科 | 三択レッスン", page_icon="✈️",
    layout="centered", initial_sidebar_state="collapsed",
)
st.markdown(f"<style>{(ROOT / 'styles.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

if "source_mode" not in st.session_state:
    st.session_state.source_mode = random.choice(list(BANK_FILES))

with st.sidebar:
    st.header("二等ドローン学科")
    mode = st.radio("問題集", list(BANK_FILES), key="source_mode")
    st.caption("教則第五版との照合済み問題だけを出題します。")
    st.divider()
    st.caption("学習履歴はこのセッション内だけに保存します。ブラウザーを閉じたり接続が切れたりすると、履歴が失われる場合があります。")

if st.session_state.get("active_source") != mode:
    st.session_state.active_source = mode
    st.session_state.pop("quiz_signature", None)
    st.session_state.pop("quiz_session", None)
path = ROOT / "data" / BANK_FILES[mode]

try:
    all_questions = load_questions(path)
except QuestionDataError as error:
    st.error(str(error))
    st.stop()

source_questions = [question for question in all_questions if question["origin"]["kind"] == "photo"]
questions = eligible_questions(all_questions, "photo")
pending_count = len(source_questions) - len(questions)

with st.sidebar:
    st.caption(f"収録 {len(source_questions)} 問 / 第五版照合済み {len(questions)} 問")

if not source_questions:
    st.info(f"{mode}の問題は未登録です。")
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
with st.sidebar:
    st.divider()
    columns = st.columns(3)
    columns[0].metric("回答済み", f"{answered}/{total}")
    columns[1].metric("正解", f"{correct}問")
    columns[2].metric("正答率", f"{correct / answered:.0%}" if answered else "—")
    st.progress(answered / total, text=f"{answered}問を回答しました")
    st.caption("出題分野や問題集を変更すると、学習を最初から開始します。")


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
st.markdown(f"<h1 class='question-heading'>{session['position'] + 1}. 問題</h1>", unsafe_allow_html=True)
with st.sidebar:
    st.caption(f"第{session['position'] + 1}問 / {total}問 · {question['category']}")
    st.caption(f"問題集：{mode}・問題{question['origin']['question_number']}")
st.markdown(question_html(question["prompt"]), unsafe_allow_html=True)

if not is_answered:
    with st.form(f"answer_form_{st.session_state.quiz_generation}_{question_id}"):
        selection = st.radio(
            "答えを1つ選んでください",
            options=list(range(3)),
            index=None,
            format_func=lambda value: question['choices'][value],
            key=f"choice_{st.session_state.quiz_generation}_{question_id}",
            label_visibility="collapsed",
            width="stretch",
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
        st.markdown(
            explanation_html(question["explanation"], question.get("explanation_highlights", [])),
            unsafe_allow_html=True,
        )
        review = question["review"]
        reference = review["reference"]
        st.markdown(f"[教則第五版の該当箇所を開く]({reference['url']}#page={reference['pdf_page']})")
        st.caption(f"{reference['section']} / 本文 {reference['printed_page']}ページ / PDF通算 {reference['pdf_page']}ページ")
    if st.button("結果を見る" if session["position"] + 1 == total else "次の問題へ", type="primary", use_container_width=True):
        advance(session)
        st.rerun()

with st.sidebar:
    st.divider()
    if st.button("この学習をやり直す", use_container_width=True):
        restart(questions)
