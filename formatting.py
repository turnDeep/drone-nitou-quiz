"""Display emphasis without changing the question or explanation text."""

from html import escape
import re


QUESTION_FOCUS = ("誤っているもの", "適切でないもの", "含まれないもの")


def _emphasize(text: str, terms: list[str] | tuple[str, ...], opening: str, closing: str) -> str:
    terms = sorted({term for term in terms if term}, key=len, reverse=True)
    if not terms:
        return escape(text)
    pattern = re.compile("|".join(re.escape(term) for term in terms))
    parts = []
    previous = 0
    for match in pattern.finditer(text):
        parts.extend((escape(text[previous:match.start()]), opening, escape(match.group()), closing))
        previous = match.end()
    parts.append(escape(text[previous:]))
    return "".join(parts)


def question_html(prompt: str) -> str:
    body = _emphasize(prompt, QUESTION_FOCUS, '<u class="question-focus">', '</u>')
    return f'<h3 class="quiz-question">{body}</h3>'


def explanation_html(explanation: str, highlights: list[str]) -> str:
    body = _emphasize(explanation, highlights, '<strong class="explanation-key">', '</strong>')
    return f'<div class="quiz-explanation">{body}</div>'
