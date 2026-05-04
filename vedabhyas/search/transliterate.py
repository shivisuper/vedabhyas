from __future__ import annotations

from indic_transliteration import sanscript

# Characters that indicate IAST diacritics (not present in plain ASCII or HK)
_IAST_MARKERS = set("āīūṛṝḷṃḥṭḍṇśṣ")


def to_slp1(text: str) -> str:
    """Normalize user input to SLP1 for querying.

    Accepts IAST, Harvard-Kyoto, plain ASCII (treated as HK), or Devanagari.
    SLP1 is ASCII-safe and unambiguous — used as the internal search normal form.
    """
    text = text.strip()
    if not text:
        return text

    # Devanagari: any char in Unicode block 0900–097F
    if any("ऀ" <= c <= "ॿ" for c in text):
        return sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.SLP1)

    # IAST: presence of diacritic markers
    if any(c in _IAST_MARKERS for c in text.lower()):
        return sanscript.transliterate(text, sanscript.IAST, sanscript.SLP1)

    # Plain ASCII / Harvard-Kyoto
    return sanscript.transliterate(text, sanscript.HK, sanscript.SLP1)


def slp1_to_iast(text: str) -> str:
    return sanscript.transliterate(text, sanscript.SLP1, sanscript.IAST)


def iast_to_devanagari(text: str) -> str:
    return sanscript.transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
