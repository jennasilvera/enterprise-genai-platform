from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import cast

import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

from enterprise_genai.data.routing_models import (
    RouteLabel,
    ToolFamily,
)

MODEL_ID = "cross-encoder/nli-deberta-v3-xsmall"

MODEL_REVISION = "a150876415327c80daeff35ca6f68f5ed8cf5c24"

ROUTER_VERSION = "pretrained-nli-router-v1"

QUESTION_REPRESENTATION_VERSION = "question-text-v1"

SCORING_VERSION = "nli-entailment-probability-v1"

DECODING_VERSION = "seven-route-entailment-argmax-v1"

TIE_BREAK_VERSION = "route-order-first-v1"

MAX_LENGTH = 512

EXPECTED_LABEL2ID = {
    "contradiction": 0,
    "entailment": 1,
    "neutral": 2,
}

ROUTE_ORDER: tuple[RouteLabel, ...] = (
    "retrieval",
    "sql",
    "graph",
    "retrieval+sql",
    "retrieval+graph",
    "sql+graph",
    "retrieval+sql+graph",
)

ROUTE_HYPOTHESES: dict[
    RouteLabel,
    str,
] = {
    "retrieval": (
        "Answering the user request requires "
        "qualitative evidence from unstructured "
        "documents, but does not require structured "
        "numerical computation or traversal of "
        "relationships between entities."
    ),
    "sql": (
        "Answering the user request requires "
        "structured numerical data, filtering, "
        "comparison, aggregation, or arithmetic, "
        "but does not require qualitative document "
        "evidence or traversal of relationships "
        "between entities."
    ),
    "graph": (
        "Answering the user request requires "
        "following relationships between entities "
        "such as companies, customers, or suppliers, "
        "but does not require qualitative document "
        "evidence or structured numerical computation."
    ),
    "retrieval+sql": (
        "Answering the user request requires both "
        "qualitative evidence from unstructured "
        "documents and structured numerical "
        "computation, but does not require traversal "
        "of relationships between entities."
    ),
    "retrieval+graph": (
        "Answering the user request requires both "
        "qualitative evidence from unstructured "
        "documents and traversal of relationships "
        "between entities, but does not require "
        "structured numerical computation."
    ),
    "sql+graph": (
        "Answering the user request requires both "
        "structured numerical computation and "
        "traversal of relationships between entities, "
        "but does not require qualitative evidence "
        "from unstructured documents."
    ),
    "retrieval+sql+graph": (
        "Answering the user request requires "
        "qualitative evidence from unstructured "
        "documents, structured numerical computation, "
        "and traversal of relationships between "
        "entities."
    ),
}

FROZEN_ROUTER_CONFIG_SHA256 = "72d8ce61cdce386bb189cb70698d0f899bf94fa63b8f42796f1a19eaaca3e924"


def nli_router_config_payload() -> dict[
    str,
    object,
]:
    return {
        "router_version": (ROUTER_VERSION),
        "model_id": (MODEL_ID),
        "model_revision": (MODEL_REVISION),
        "question_representation_version": (QUESTION_REPRESENTATION_VERSION),
        "scoring_version": (SCORING_VERSION),
        "decoding_version": (DECODING_VERSION),
        "tie_break_version": (TIE_BREAK_VERSION),
        "max_length": (MAX_LENGTH),
        "label2id": (EXPECTED_LABEL2ID),
        "route_order": list(ROUTE_ORDER),
        "route_hypotheses": {route: (ROUTE_HYPOTHESES[route]) for route in ROUTE_ORDER},
    }


def nli_router_config_sha256() -> str:
    payload = json.dumps(
        nli_router_config_payload(),
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    ).encode()

    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class RouteScore:
    route_label: RouteLabel
    hypothesis: str
    entailment_probability: float


@dataclass(frozen=True)
class NliRoutePrediction:
    predicted_tools: tuple[ToolFamily, ...]
    route_label: RouteLabel
    route_scores: tuple[RouteScore, ...]


def route_label_to_tools(
    route_label: RouteLabel,
) -> tuple[ToolFamily, ...]:
    return cast(
        tuple[ToolFamily, ...],
        tuple(route_label.split("+")),
    )


def select_route_from_scores(
    scores: dict[
        RouteLabel,
        float,
    ],
) -> RouteLabel:
    if set(scores) != set(ROUTE_ORDER):
        raise ValueError("Scores must contain exactly the seven canonical route labels.")

    for route, score in scores.items():
        if not isinstance(
            score,
            (
                float,
                int,
            ),
        ):
            raise TypeError(f"Route score for {route!r} must be numeric.")

        if not math.isfinite(float(score)):
            raise ValueError(f"Route score for {route!r} must be finite.")

    return max(
        ROUTE_ORDER,
        key=lambda route: (
            float(scores[route]),
            -ROUTE_ORDER.index(route),
        ),
    )


class PretrainedNliRouter:
    def __init__(
        self,
    ) -> None:
        actual_config_sha256 = nli_router_config_sha256()

        if actual_config_sha256 != FROZEN_ROUTER_CONFIG_SHA256:
            raise RuntimeError(
                f"Frozen NLI router configuration fingerprint mismatch: {actual_config_sha256}."
            )

        self._tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            revision=MODEL_REVISION,
            trust_remote_code=False,
        )

        self._model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_ID,
            revision=MODEL_REVISION,
            trust_remote_code=False,
            use_safetensors=True,
        )

        self._model.to("cpu")

        self._model.eval()

        label2id = {
            str(key).casefold(): int(value) for key, value in self._model.config.label2id.items()
        }

        if label2id != EXPECTED_LABEL2ID:
            raise RuntimeError(f"Unexpected NLI label mapping: {label2id!r}.")

        self._entailment_index = label2id["entailment"]

    def predict(
        self,
        question: str,
    ) -> NliRoutePrediction:
        normalized = " ".join(question.split())

        if not normalized:
            raise ValueError("Routing question must not be blank.")

        hypotheses = [ROUTE_HYPOTHESES[route] for route in ROUTE_ORDER]

        features = self._tokenizer(
            [normalized for _ in ROUTE_ORDER],
            hypotheses,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )

        with torch.no_grad():
            logits = self._model(**features).logits

        if tuple(logits.shape) != (
            len(ROUTE_ORDER),
            3,
        ):
            raise RuntimeError(f"Unexpected NLI logits shape: {tuple(logits.shape)!r}.")

        probabilities = torch.softmax(
            logits,
            dim=-1,
        )

        entailment_scores = {
            route: float(
                probabilities[
                    index,
                    self._entailment_index,
                ].item()
            )
            for index, route in enumerate(ROUTE_ORDER)
        }

        selected = select_route_from_scores(entailment_scores)

        route_scores = tuple(
            RouteScore(
                route_label=route,
                hypothesis=(ROUTE_HYPOTHESES[route]),
                entailment_probability=(entailment_scores[route]),
            )
            for route in ROUTE_ORDER
        )

        return NliRoutePrediction(
            predicted_tools=(route_label_to_tools(selected)),
            route_label=selected,
            route_scores=(route_scores),
        )

    def metadata(
        self,
    ) -> dict[
        str,
        object,
    ]:
        parameters = sum(parameter.numel() for parameter in self._model.parameters())

        return {
            **nli_router_config_payload(),
            "router_config_sha256": (nli_router_config_sha256()),
            "model_class": (type(self._model).__name__),
            "tokenizer_class": (type(self._tokenizer).__name__),
            "device": "cpu",
            "parameters": (parameters),
            "training_performed": (False),
        }
