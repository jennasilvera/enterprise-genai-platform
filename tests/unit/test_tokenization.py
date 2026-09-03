from enterprise_genai.retrieval.tokenization import (
    normalize_lexical_text,
    tokenize,
)


def test_tokenizer_preserves_compound_identifier() -> None:
    assert tokenize("Failure in ORBIS-IDX-7.") == (
        "failure",
        "in",
        "orbis-idx-7",
    )


def test_tokenizer_normalizes_case() -> None:
    assert tokenize("TitaniumWorks GmbH") == (
        "titaniumworks",
        "gmbh",
    )


def test_lexical_normalization_is_deterministic() -> None:
    assert normalize_lexical_text("HELIOGRID") == "heliogrid"
