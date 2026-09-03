import re
import unicodedata

TOKENIZER_VERSION = "lexical-tokenizer-v1"

_TOKEN_PATTERN = re.compile(
    r"[^\W_]+(?:[._-][^\W_]+)*",
    flags=re.UNICODE,
)


def normalize_lexical_text(text: str) -> str:
    """Normalize text deterministically for lexical retrieval."""

    return unicodedata.normalize(
        "NFKC",
        text,
    ).casefold()


def tokenize(text: str) -> tuple[str, ...]:
    """Tokenize while preserving compound identifiers.

    Examples:
        ORBIS-IDX-7 -> ("orbis-idx-7",)
        2026 Q2     -> ("2026", "q2")
    """

    normalized = normalize_lexical_text(text)

    return tuple(match.group(0) for match in _TOKEN_PATTERN.finditer(normalized))
