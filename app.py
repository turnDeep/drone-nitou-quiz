"""Japanese three-choice study app for verified fifth-edition questions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import streamlit as st

from formatting import explanation_html, question_html
from quiz import (
    RANDOM_BATCH_SIZE, QuestionDataError, advance, create_random_session, create_session,
    decode_progress, eligible_questions, encode_progress, extend_random_session,
    load_questions, missed_questions, score, session_from_progress, submit_answer,
)

ROOT = Path(__file__).resolve().parent
CHOICE_LABELS = "ABC"
BANK_FILES = {"第1回": "questions.json", "第2回": "questions_round2.json", "第3回": "questions_round3.json", "第4回": "questions_round4.json", "第5回": "questions_round5.json"}
RANDOM_MODE = "ランダム"
# The random set stays last so progress tokens saved before it existed keep
# pointing at the same round (the token stores the index into this list).
SET_NAMES = [*BANK_FILES, RANDOM_MODE]

st.set_page_config(
    page_title="二等ドローン学科 | 三択レッスン", page_icon="✈️",
    layout="centered", initial_sidebar_state="collapsed",
)
st.markdown(f"<style>{(ROOT / 'styles.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# When the Streamlit session is gone (connection lost, browser reopened),
# the progress token in the URL is the only way back. It is consulted only
# on the very first run of a session state: if the app itself discarded a
# quiz mid-session (bank or filter change), the token must not resurrect it.
pending_restore = None
if "app_booted" not in st.session_state:
    st.session_state.app_booted = True
    pending_restore = decode_progress(st.query_params.get("p"))
    if pending_restore is not None and pending_restore["bank_index"] >= len(SET_NAMES):
        pending_restore = None

if "source_mode" not in st.session_state:
    if pending_restore is not None:
        st.session_state.source_mode = SET_NAMES[pending_restore["bank_index"]]
    else:
        st.session_state.source_mode = RANDOM_MODE
if pending_restore is not None:
    if "category_filter" not in st.session_state:
        st.session_state.category_filter = pending_restore["category"]
    if "shuffle_order" not in st.session_state:
        st.session_state.shuffle_order = pending_restore["shuffle"]

with st.sidebar:
    st.header("二等ドローン学科")
    mode = st.radio("問題集", SET_NAMES, key="source_mode")
    st.caption("教則第五版との照合済み問題だけを出題します。")
    st.divider()
    st.caption("学習の進み具合はURLに保存します。接続が切れても、同じブラウザーでこのURLを開けば続きから再開できます。")

if st.session_state.get("active_source") != mode:
    st.session_state.active_source = mode
    st.session_state.pop("quiz_signature", None)
    st.session_state.pop("quiz_session", None)

# The random set draws from every round's bank merged into one pool; the
# per-question source bank is remembered so the UI can still name it.
bank_loads = list(BANK_FILES.items()) if mode == RANDOM_MODE else [(mode, BANK_FILES[mode])]
try:
    all_questions = []
    source_bank_by_id = {}
    for bank_name, filename in bank_loads:
        bank_questions = load_questions(ROOT / "data" / filename)
        all_questions.extend(bank_questions)
        for bank_question in bank_questions:
            source_bank_by_id[bank_question["id"]] = bank_name
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

if mode == RANDOM_MODE:
    # The random set always serves the whole pool in drawn order, so the
    # category filter and the shuffle toggle do not apply to it.
    category = "すべて"
    shuffle = False
    with st.sidebar:
        st.caption("ランダムは全問題から重複なしで出題します。出題分野の絞り込みは使いません。")
else:
    with st.sidebar:
        categories = sorted({question["category"] for question in questions})
        if st.session_state.get("category_filter") not in ["すべて", *categories]:
            st.session_state.category_filter = "すべて"
        category = st.selectbox("出題分野", ["すべて"] + categories, key="category_filter")
        shuffle = st.checkbox("問題の順番をランダムにする", key="shuffle_order")

if category != "すべて":
    questions = [question for question in questions if question["category"] == category]

signature = hashlib.sha256(json.dumps([mode, category, shuffle, questions], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
if st.session_state.get("quiz_signature") != signature:
    restored = session_from_progress(pending_restore, questions) if pending_restore else None
    st.session_state.quiz_signature = signature
    if restored is not None:
        st.session_state.quiz_session = restored
    elif mode == RANDOM_MODE:
        st.session_state.quiz_session = create_random_session(questions)
    else:
        st.session_state.quiz_session = create_session(questions, shuffle)
    # Only sessions born here (fresh draw or URL restore) count as random-set
    # sessions; a missed-questions retry started from the result screen does not.
    st.session_state.random_session = mode == RANDOM_MODE
    st.session_state.quiz_generation = st.session_state.get("quiz_generation", 0) + 1

session = st.session_state.quiz_session


def save_progress() -> None:
    """Mirror the live session into the URL so a lost session can resume."""
    token = encode_progress(SET_NAMES.index(mode), category, shuffle, session)
    if st.query_params.get("p") != token:
        st.query_params["p"] = token


save_progress()
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
    st.session_state.random_session = False
    st.session_state.scroll_to_top = True
    st.rerun()


def restart_random() -> None:
    st.session_state.quiz_session = create_random_session(questions)
    st.session_state.quiz_generation += 1
    st.session_state.random_session = True
    st.session_state.scroll_to_top = True
    st.rerun()


def scroll_to_top_if_requested() -> None:
    if st.session_state.pop("scroll_to_top", False):
        # Wait for the new content to finish rendering, then reset the actual
        # Streamlit scroll container. Only app navigation requests this effect.
        st.html(
            """<script>
            requestAnimationFrame(() => requestAnimationFrame(() => {
                document.querySelector('[data-testid="stMain"]')?.scrollTo({
                    top: 0, behavior: "instant"
                });
                window.scrollTo({top: 0, behavior: "instant"});
            }));
            </script>""",
            unsafe_allow_javascript=True,
        )


if session["position"] >= total:
    st.success(f"おつかれさまでした。{total}問中 {correct}問正解です。")
    if mode == RANDOM_MODE and st.session_state.get("random_session", False):
        served = len(session["order"])
        if served < len(questions):
            st.write(
                f"全{len(questions)}問のうち、{served}問を出題済みです。"
                f"「追加で出題」を押すと、まだ出ていない問題から{RANDOM_BATCH_SIZE}問をランダムに追加します。"
            )
            if st.button("追加で出題", type="primary", use_container_width=True):
                extend_random_session(session, questions)
                st.session_state.scroll_to_top = True
                st.rerun()
        else:
            st.write(f"全{len(questions)}問をすべて出題しました。")
    missed = missed_questions(session, questions)
    if missed:
        st.write("間違えた問題をもう一度確認しましょう。")
        if st.button("間違いだけ再挑戦", type="primary", use_container_width=True):
            restart(missed)
    else:
        st.write("すべて正解です。解説で確認した内容を、実際の学習にも役立ててください。")
    if st.button("最初から学習する", use_container_width=True):
        if mode == RANDOM_MODE:
            restart_random()
        else:
            restart(questions)
    scroll_to_top_if_requested()
    st.stop()

question = lookup[session["order"][session["position"]]]
question_id = question["id"]
is_answered = question_id in session["answers"]
st.markdown(f"<h1 class='question-heading'>{session['position'] + 1}. 問題</h1>", unsafe_allow_html=True)
with st.sidebar:
    st.caption(f"第{session['position'] + 1}問 / {total}問 · {question['category']}")
    if mode == RANDOM_MODE:
        st.caption(f"問題集：ランダム（{source_bank_by_id.get(question_id, mode)}・問題{question['origin']['question_number']}）")
    else:
        st.caption(f"問題集：{mode}・問題{question['origin']['question_number']}")
st.markdown(question_html(question["prompt"]), unsafe_allow_html=True)

if not is_answered:
    with st.form(f"answer_form_{st.session_state.quiz_generation}_{question_id}"):
        selection = st.radio(
            "答えを1つ選んでください",
            options=list(range(3)),
            index=None,
            format_func=lambda value: f"{CHOICE_LABELS[value]}. {question['choices'][value]}",
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
    st.write(f"**あなたの回答：{CHOICE_LABELS[selected]}. {question['choices'][selected]}**")
    st.write(f"**正答：{CHOICE_LABELS[answer]}. {question['choices'][answer]}**")
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
        detail = question.get("detail")
        if detail:
            st.divider()
            st.markdown("### 詳しい解説")
            image = detail.get("image")
            if image and (ROOT / image["file"]).is_file():
                st.image(str(ROOT / image["file"]))
                st.caption(f"画像出典：{image['credit']}")
            for section in detail.get("sections", []):
                st.markdown(f"**{section['heading']}**")
                table = section.get("table")
                if table:
                    header = " | ".join(table["head"])
                    separator = " | ".join("---" for _ in table["head"])
                    lines = [f"| {header} |", f"| {separator} |"]
                    for row in table["rows"]:
                        cells = " | ".join(str(cell).replace("|", "｜") for cell in row)
                        lines.append(f"| {cells} |")
                    st.markdown("\n".join(lines))
                for bullet in section.get("bullets", []):
                    st.markdown(f"- {bullet}")
    if st.button("結果を見る" if session["position"] + 1 == total else "次の問題へ", type="primary", use_container_width=True):
        advance(session)
        st.session_state.scroll_to_top = True
        st.rerun()

with st.sidebar:
    st.divider()
    if st.button("この学習をやり直す", use_container_width=True):
        if mode == RANDOM_MODE:
            restart_random()
        else:
            restart(questions)

scroll_to_top_if_requested()
