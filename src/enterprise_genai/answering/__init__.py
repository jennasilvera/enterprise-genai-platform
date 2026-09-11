"""Typed evidence, sufficiency, and grounded-answer contracts."""

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceRecord,
    GraphEntityEvidenceData,
    GraphRelationshipEvidenceData,
    StructuredEntityEvidenceData,
    StructuredValueEvidenceData,
    SufficiencyAssessment,
)
from enterprise_genai.answering.evidence import (
    evidence_bundle_from_snapshot,
    unsupported_request_bundle,
)
from enterprise_genai.answering.outcomes import (
    AbstentionOutcome,
    AnswerOutcome,
    GroundedAnswer,
    GroundedAnswerType,
)
from enterprise_genai.answering.sufficiency import (
    SUFFICIENCY_POLICY_VERSION,
    EvidenceRequirement,
    evaluate_sufficiency,
)
from enterprise_genai.answering.synthesis import (
    SYNTHESIS_VERSION,
    SynthesisInstruction,
    synthesize_answer,
)

__all__ = [
    "SUFFICIENCY_POLICY_VERSION",
    "SYNTHESIS_VERSION",
    "AbstentionOutcome",
    "AnswerOutcome",
    "EvidenceBundle",
    "EvidenceRecord",
    "EvidenceRequirement",
    "GraphEntityEvidenceData",
    "GraphRelationshipEvidenceData",
    "GroundedAnswer",
    "GroundedAnswerType",
    "StructuredEntityEvidenceData",
    "StructuredValueEvidenceData",
    "SufficiencyAssessment",
    "SynthesisInstruction",
    "evaluate_sufficiency",
    "evidence_bundle_from_snapshot",
    "synthesize_answer",
    "unsupported_request_bundle",
]
