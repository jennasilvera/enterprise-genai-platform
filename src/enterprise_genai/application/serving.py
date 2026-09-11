from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from enterprise_genai.application.northstar_specification import (
    NorthstarBoundedSpecificationProvider,
)
from enterprise_genai.application.request_runtime import (
    RequestScopedExecutionRuntime,
    RetrievalExecutorProtocol,
)
from enterprise_genai.application.service import (
    GroundedAnsweringService,
)
from enterprise_genai.execution.contracts import (
    RetrievalQuery,
    ToolExecutionResult,
)
from enterprise_genai.execution.frozen_retrieval import (
    FrozenHybridRetrievalExecutor,
)
from enterprise_genai.generation.contracts import (
    GenerationProvider,
    GroundedGenerationRequest,
    RawGeneration,
)
from enterprise_genai.generation.hf_provider import (
    HuggingFaceCausalGenerationProvider,
)
from enterprise_genai.observability.metrics import (
    OperationalMetricsRegistry,
)

SERVING_ASSEMBLY_VERSION = "northstar-serving-assembly-v1"


class LockedRetrievalExecutor:
    """Serialize access to the shared dense-retrieval runtime."""

    def __init__(
        self,
        delegate: RetrievalExecutorProtocol,
    ) -> None:
        self._delegate = delegate
        self._lock = Lock()

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        with self._lock:
            return self._delegate.execute(query)


class LockedGenerationProvider:
    """Serialize access to the shared CPU generation model."""

    def __init__(
        self,
        delegate: GenerationProvider,
    ) -> None:
        self._delegate = delegate
        self._lock = Lock()

    def generate(
        self,
        request: GroundedGenerationRequest,
    ) -> RawGeneration:
        with self._lock:
            return self._delegate.generate(request)


type RetrievalBuilder = Callable[
    [
        Session,
        str,
    ],
    RetrievalExecutorProtocol,
]

type GenerationBuilder = Callable[
    [],
    GenerationProvider,
]


def _build_persisted_retrieval(
    session: Session,
    dataset_version: str,
) -> RetrievalExecutorProtocol:
    return FrozenHybridRetrievalExecutor.from_persisted_corpus(
        session,
        dataset_version,
    )


def _build_generation_provider() -> GenerationProvider:
    return HuggingFaceCausalGenerationProvider.from_pretrained()


@dataclass(
    frozen=True,
    slots=True,
)
class ServingAssembly:
    """Long-lived serving resources and composed service."""

    service: GroundedAnsweringService

    specification_provider: NorthstarBoundedSpecificationProvider

    runtime: RequestScopedExecutionRuntime

    retrieval_executor: LockedRetrievalExecutor

    generation_provider: LockedGenerationProvider

    metrics_registry: OperationalMetricsRegistry


def build_serving_assembly(
    *,
    engine: Engine,
    dataset_version: str = "northstar-v1",
    retrieval_builder: RetrievalBuilder = (_build_persisted_retrieval),
    generation_builder: GenerationBuilder = (_build_generation_provider),
    metrics_registry: (OperationalMetricsRegistry | None) = None,
) -> ServingAssembly:
    """Build expensive serving resources exactly once."""

    metrics = metrics_registry if metrics_registry is not None else OperationalMetricsRegistry()

    with Session(engine) as session:
        persisted_retrieval = retrieval_builder(
            session,
            dataset_version,
        )

    retrieval = LockedRetrievalExecutor(persisted_retrieval)

    generation = LockedGenerationProvider(generation_builder())

    specification_provider = NorthstarBoundedSpecificationProvider()

    runtime = RequestScopedExecutionRuntime(
        engine=engine,
        retrieval_executor=retrieval,
    )

    service = GroundedAnsweringService(
        specification_provider=(specification_provider),
        runtime=runtime,
        generation_provider=generation,
        metrics_registry=metrics,
    )

    return ServingAssembly(
        service=service,
        specification_provider=(specification_provider),
        runtime=runtime,
        retrieval_executor=retrieval,
        generation_provider=generation,
        metrics_registry=metrics,
    )
