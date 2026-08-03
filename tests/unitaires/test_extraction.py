"""Unit tests for PDF text extraction (no real PDF file)."""

from cahier_doleances.extraction.extract_text import (
    clean_page_text,
    needs_ocr_flag,
    wordfreq_quality_score,
)

GARBAGE_SAMPLE = (
    "y ftiA 'Aj-V ûi' V,*>><.AUi- V fila Ji.JA CAlTt ^ ejr eyif ^ju.*-» tla^"
)


def test_wordfreq_quality_score_empty():
    assert wordfreq_quality_score("") == 0.0


def test_wordfreq_quality_score_no_long_words():
    assert wordfreq_quality_score("ab cd ef") == 0.0


def test_wordfreq_quality_score_clean_text():
    score = wordfreq_quality_score(
        "Bonjour, je souhaite exprimer ma demande concernant la fiscalité locale."
    )
    assert score > 0.5


def test_wordfreq_quality_score_garbage_sample():
    score = wordfreq_quality_score(GARBAGE_SAMPLE)
    assert score < 0.2


def test_clean_page_text_strips_and_normalizes():
    assert clean_page_text("  hello  \r\n world  ") == "hello\nworld"


def test_clean_page_text_empty():
    assert clean_page_text("") == ""
    assert clean_page_text("   \n\t  ") == ""


def test_clean_page_text_collapses_spaces():
    assert clean_page_text("a    b\t\tc") == "a b c"


def test_needs_ocr_flag_empty_text():
    assert needs_ocr_flag("", 0.0) is False
    assert needs_ocr_flag("   \n  ", 0.0) is False


def test_needs_ocr_flag_garbage_ocr_example():
    score = wordfreq_quality_score(GARBAGE_SAMPLE)
    assert needs_ocr_flag(GARBAGE_SAMPLE, score) is True


def test_needs_ocr_flag_long_text_low_quality():
    long_garbage = " ".join(["ftiA", "Aj-V", "ûi'", "fila", "Ji.JA", "CAlTt"] * 50)
    score = wordfreq_quality_score(long_garbage)
    assert needs_ocr_flag(long_garbage, score) is True


def test_needs_ocr_flag_clean_text():
    text = "Bonjour, je souhaite exprimer ma demande concernant la fiscalité locale."
    score = wordfreq_quality_score(text)
    assert needs_ocr_flag(text, score) is False
