"""Regenerate the human-readable audit from the reviewed question bank."""

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quiz import load_questions  # noqa: E402

LABELS = {
    "unchanged": "正答・設問を維持",
    "explanation_updated": "解説を補足",
    "question_revised": "設問・選択肢を修正",
    "hold": "確認保留",
}


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def main():
    questions = load_questions(ROOT / "data/questions.json")
    counts = Counter(q["audit"]["verdict"] for q in questions)
    changed_answers = sum(q["audit"]["answer_changed"] for q in questions)
    lines = [
        "# 写真問題50問の第五版照合結果", "",
        "確認日：2026年10月29日。対象：提供写真20枚にある第1回の問題1〜50と正答・解説。", "",
        f"照合した問題は{len(questions)}問です。正答番号の変更は{changed_answers}問です。",
        "原文・元の正答・元の解説の要点は `data/questions.json` の `original` に残しています。",
        "アプリの解説は第五版の該当本文を確認して書き直したものです。原本画像はGitHubにアップロードしていません。", "",
        "## 判定の件数", "", "| 判定 | 件数 |", "| --- | ---: |",
    ]
    lines.extend(f"| {label} | {counts[key]} |" for key, label in LABELS.items())
    lines += [
        "", "『正答・設問を維持』でも解説は学習用に言い換えています。『解説を補足』は第五版の例外条件や原本解説の限定不足などを明示的に補ったものです。",
        "『設問・選択肢を修正』には、版改訂に加え、原本のままでは唯一の正答が成立しない場合や時点依存の断定を避けたものを含みます。", "",
        "## 全問題の照合一覧", "",
        "ページは第五版の印刷ページです。根拠リンクは該当するPDF通算ページを開きます。", "",
        "| 問題 | 原本の正答 | アプリの正答 | 判定 | 理由・確認内容 | 第五版の根拠 |",
        "| ---: | :---: | :---: | --- | --- | --- |",
    ]
    for q in questions:
        ref, audit = q["review"]["reference"], q["audit"]
        link = f"[{cell(ref['section'])} p.{ref['printed_page']}]({ref['url']}#page={ref['pdf_page']})"
        lines.append(
            f"| {q['origin']['question_number']} | {'ABC'[q['original']['answer_index']]} | "
            f"{'ABC'[q['answer_index']]} | {LABELS[audit['verdict']]} | {cell(audit['reason'])} | {link} |"
        )
    lines += ["", "## 修正した問題の原文とアプリの表現", ""]
    for q in questions:
        if q["audit"]["verdict"] != "question_revised":
            continue
        lines += [f"### 問題{q['origin']['question_number']}", "", q["audit"]["reason"], "", "**原本**", "", q["original"]["prompt"], ""]
        lines.extend(f"- {'ABC'[i]}. {choice}" for i, choice in enumerate(q["original"]["choices"]))
        lines += ["", "**アプリ**", "", q["prompt"], ""]
        lines.extend(f"- {'ABC'[i]}. {choice}" for i, choice in enumerate(q["choices"]))
        lines += ["", f"**アプリの解説：** {q['explanation']}", ""]
    lines += [
        "## 照合の範囲", "",
        "これは提供された50問の確認記録です。第五版の全論点を網羅した新規問題集、公式過去問、法令適合の認証を意味するものではありません。",
        "参考資料の版・URL・SHA-256は `docs/sources.json`、受領した写真の識別情報は `docs/photo-manifest.json` を参照してください。", "",
    ]
    target = ROOT / "docs/question-audit.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"Reviewed {len(questions)} questions; wrote {target.name}; {dict(counts)}")


if __name__ == "__main__":
    main()
