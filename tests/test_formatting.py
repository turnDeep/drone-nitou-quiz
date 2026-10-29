"""Emphasis preserves wording and renders stored text as text rather than HTML."""

from html.parser import HTMLParser

from formatting import explanation_html, question_html


class TextReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def displayed_text(markup):
    reader = TextReader()
    reader.feed(markup)
    return "".join(reader.parts)


def test_negative_instruction_is_underlined_without_changing_the_prompt():
    prompt = "説明として、誤っているものを1つ選びなさい。"
    markup = question_html(prompt)
    assert '<u class="question-focus">誤っているもの</u>' in markup
    assert displayed_text(markup) == prompt
    assert "<u " not in question_html("正しいものを1つ選びなさい。")


def test_explanation_emphasis_keeps_negation_and_special_characters_intact():
    text = "100g未満も対象に含みます。<script>alert(1)</script> & 5m/s"
    markup = explanation_html(text, ["100g未満も対象に含みます", "5m/s"])
    assert '<strong class="explanation-key">100g未満も対象に含みます</strong>' in markup
    assert '<script>' not in markup
    assert displayed_text(markup) == text


def test_overlapping_and_repeated_terms_do_not_duplicate_or_drop_text():
    text = "原則として事前通報。例外では事後通報。事前通報が原則です。"
    markup = explanation_html(text, ["事前通報", "原則として事前通報", "事後通報"])
    assert displayed_text(markup) == text
    assert markup.count('<strong class="explanation-key">') == 3
