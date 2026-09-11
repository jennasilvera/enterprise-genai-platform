from __future__ import annotations

import torch

from enterprise_genai.generation.contracts import (
    GenerationAuthority,
    GenerationEvidence,
    GroundedGenerationRequest,
)
from enterprise_genai.generation.hf_provider import (
    DEFAULT_MAX_NEW_TOKENS,
    HF_CAUSAL_PROVIDER_VERSION,
    QWEN25_05B_INSTRUCT_MODEL_ID,
    QWEN25_05B_INSTRUCT_REVISION,
    HuggingFaceCausalGenerationProvider,
    render_generation_messages,
)


def _request() -> GroundedGenerationRequest:
    return GroundedGenerationRequest(
        question=("What was total portfolio revenue in 2026 Q2?"),
        authority=GenerationAuthority(
            outcome="answer",
            answer_type="number",
            value=735_000_000,
            unit="USD",
            supporting_record_ids=("SQL:VALUE:portfolio_metric_sum",),
            source_fact_ids=("FIN-PC-001-2026Q2",),
        ),
        evidence=(
            GenerationEvidence(
                record_id=("SQL:VALUE:portfolio_metric_sum"),
                tool="sql",
                kind="structured_value",
                content=("Structured operation portfolio_metric_sum returned 735000000 USD."),
                source_fact_ids=("FIN-PC-001-2026Q2",),
            ),
        ),
        allowed_citation_ids=("SQL:VALUE:portfolio_metric_sum",),
    )


def test_pinned_qwen_identity() -> None:
    assert QWEN25_05B_INSTRUCT_MODEL_ID == "Qwen/Qwen2.5-0.5B-Instruct"

    assert QWEN25_05B_INSTRUCT_REVISION == "7ae557604adf67be50417f59c2c2f167def9a775"


def test_prompt_marks_authority_immutable() -> None:
    messages = render_generation_messages(_request())

    assert len(messages) == 2

    system = messages[0]["content"]

    user = messages[1]["content"]

    assert "AUTHORITY object is immutable" in system

    assert "Preserve numeric values and units exactly as supplied" in system

    assert '"value":735000000' in user

    assert '"unit":"USD"' in user


def test_prompt_contains_only_allowed_evidence() -> None:
    rendered = "\n".join(message["content"] for message in render_generation_messages(_request()))

    assert "SQL:VALUE:portfolio_metric_sum" in rendered

    assert "735000000 USD" in rendered


class _FakeTokenizer:
    eos_token_id = 99

    def __init__(
        self,
    ) -> None:
        self.messages = None

    def apply_chat_template(
        self,
        messages,
        *,
        tokenize,
        add_generation_prompt,
        return_tensors,
        return_dict,
    ):
        self.messages = messages

        assert tokenize is True
        assert add_generation_prompt is True
        assert return_tensors == "pt"
        assert return_dict is True

        return {
            "input_ids": torch.tensor(
                [
                    [
                        1,
                        2,
                        3,
                    ]
                ]
            ),
            "attention_mask": torch.tensor(
                [
                    [
                        1,
                        1,
                        1,
                    ]
                ]
            ),
        }

    def decode(
        self,
        tokens,
        *,
        skip_special_tokens,
    ) -> str:
        assert skip_special_tokens is True

        assert tokens.tolist() == [
            7,
            8,
        ]

        return "Total portfolio revenue was 735000000 USD."


class _FakeModel:
    def __init__(
        self,
    ) -> None:
        self._parameter = torch.nn.Parameter(
            torch.ones(
                1,
                dtype=torch.float32,
            )
        )

        self.eval_called = False

        self.requires_grad_value = None

        self.generate_kwargs = None

    def parameters(
        self,
    ):
        yield self._parameter

    def eval(
        self,
    ):
        self.eval_called = True

        return self

    def requires_grad_(
        self,
        value,
    ):
        self.requires_grad_value = value

        self._parameter.requires_grad_(value)

        return self

    def generate(
        self,
        **kwargs,
    ):
        self.generate_kwargs = kwargs

        return torch.tensor(
            [
                [
                    1,
                    2,
                    3,
                    7,
                    8,
                ]
            ]
        )


def test_provider_uses_greedy_cpu_generation() -> None:
    tokenizer = _FakeTokenizer()

    model = _FakeModel()

    provider = HuggingFaceCausalGenerationProvider(
        tokenizer=tokenizer,
        model=model,
        model_id=(QWEN25_05B_INSTRUCT_MODEL_ID),
        model_revision=(QWEN25_05B_INSTRUCT_REVISION),
    )

    result = provider.generate(_request())

    assert model.eval_called is True

    assert model.requires_grad_value is False

    assert result.text == ("Total portfolio revenue was 735000000 USD.")

    assert result.metadata.provider_id == HF_CAUSAL_PROVIDER_VERSION

    assert result.metadata.device == "cpu"

    assert result.metadata.dtype == "float32"

    kwargs = model.generate_kwargs

    assert kwargs is not None

    assert kwargs["do_sample"] is False

    assert kwargs["max_new_tokens"] == DEFAULT_MAX_NEW_TOKENS

    assert kwargs["use_cache"] is True

    assert kwargs["pad_token_id"] == 99


def test_provider_rejects_non_float32_model() -> None:
    tokenizer = _FakeTokenizer()

    model = _FakeModel()

    model._parameter = torch.nn.Parameter(
        torch.ones(
            1,
            dtype=torch.float64,
        )
    )

    try:
        HuggingFaceCausalGenerationProvider(
            tokenizer=tokenizer,
            model=model,
            model_id="test",
            model_revision="revision",
        )

    except ValueError as exc:
        assert "requires float32" in str(exc)

    else:
        raise AssertionError("Expected non-float32 model rejection.")
