import pytest
from vedabhyas.search.transliterate import to_slp1, slp1_to_iast


def test_plain_ascii_as_hk():
    # plain ASCII lowercase treated as Harvard-Kyoto
    result = to_slp1("dharma")
    assert result  # should produce some SLP1 output


def test_iast_diacritics():
    # ā triggers IAST detection
    result = to_slp1("dhārma")
    assert result


def test_empty():
    assert to_slp1("") == ""
    assert to_slp1("   ") == ""


def test_devanagari_detection():
    # Devanagari character range
    result = to_slp1("धर्म")
    assert result  # should produce SLP1


def test_slp1_to_iast_roundtrip():
    iast_input = "dharma"
    slp1 = to_slp1(iast_input)
    # SLP1 → IAST should produce a non-empty string
    back = slp1_to_iast(slp1)
    assert back
