from __future__ import annotations

from concurrent.futures import (
    ThreadPoolExecutor,
)
from threading import Lock
from time import sleep
from typing import cast

from sqlalchemy import (
    create_engine,
)

from enterprise_genai.application.serving import (
    SERVING_ASSEMBLY_VERSION,
    LockedGenerationProvider,
    LockedRetrievalExecutor,
    ServingAssembly,
    build_serving_assembly,
)
from enterprise_genai.execution.contracts import (
    RetrievalPayload,
    RetrievalQuery,
    ToolExecutionResult,
)
from enterprise_genai.generation.contracts import (
    GroundedGenerationRequest,
    RawGeneration,
)


class EmptyRetrieval:
    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool="retrieval",
            status="empty",
            payload=RetrievalPayload(hits=()),
            duration_ms=0.0,
        )


class UnusedGenerationProvider:
    def generate(
        self,
        request: GroundedGenerationRequest,
    ) -> RawGeneration:
        raise AssertionError("generation should not be invoked")


def test_serving_assembly_version_is_frozen() -> None:
    assert SERVING_ASSEMBLY_VERSION == "northstar-serving-assembly-v1"


def test_serving_assembly_builds_expensive_resources_once() -> None:
    engine = create_engine("sqlite://")

    retrieval_calls = []
    generation_calls = []

    retrieval = EmptyRetrieval()
    generation = UnusedGenerationProvider()

    def build_retrieval(
        session,
        dataset_version,
    ):
        retrieval_calls.append(
            (
                session,
                dataset_version,
            )
        )

        return retrieval

    def build_generation():
        generation_calls.append(True)

        return generation

    assembly = build_serving_assembly(
        engine=engine,
        retrieval_builder=(build_retrieval),
        generation_builder=(build_generation),
    )

    assert isinstance(
        assembly,
        ServingAssembly,
    )

    assert len(retrieval_calls) == 1

    assert retrieval_calls[0][1] == "northstar-v1"

    assert generation_calls == [True]


def test_shared_retrieval_execution_is_serialized() -> None:
    tracker_lock = Lock()

    active = 0
    max_active = 0

    class SlowRetrieval:
        def execute(
            self,
            query: RetrievalQuery,
        ) -> ToolExecutionResult:
            nonlocal active
            nonlocal max_active

            with tracker_lock:
                active += 1

                max_active = max(
                    max_active,
                    active,
                )

            sleep(0.05)

            with tracker_lock:
                active -= 1

            return ToolExecutionResult(
                tool="retrieval",
                status="empty",
                payload=RetrievalPayload(hits=()),
                duration_ms=0.0,
            )

    wrapped = LockedRetrievalExecutor(SlowRetrieval())

    query = RetrievalQuery(question="Test?")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(
                wrapped.execute,
                query,
            ),
            executor.submit(
                wrapped.execute,
                query,
            ),
        )

        for future in futures:
            future.result()

    assert max_active == 1


def test_shared_generation_execution_is_serialized() -> None:
    tracker_lock = Lock()

    active = 0
    max_active = 0

    result = cast(
        RawGeneration,
        object(),
    )

    class SlowGenerationProvider:
        def generate(
            self,
            request: GroundedGenerationRequest,
        ) -> RawGeneration:
            nonlocal active
            nonlocal max_active

            with tracker_lock:
                active += 1

                max_active = max(
                    max_active,
                    active,
                )

            sleep(0.05)

            with tracker_lock:
                active -= 1

            return result

    wrapped = LockedGenerationProvider(SlowGenerationProvider())

    request = cast(
        GroundedGenerationRequest,
        object(),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(
                wrapped.generate,
                request,
            ),
            executor.submit(
                wrapped.generate,
                request,
            ),
        )

        observed = tuple(future.result() for future in futures)

    assert observed == (
        result,
        result,
    )

    assert max_active == 1


def test_serving_assembly_reuses_supplied_metrics_registry() -> None:
    from enterprise_genai.observability.metrics import (
        OperationalMetricsRegistry,
    )

    engine = create_engine("sqlite://")

    metrics = OperationalMetricsRegistry()

    assembly = build_serving_assembly(
        engine=engine,
        retrieval_builder=(lambda session, dataset_version: EmptyRetrieval()),
        generation_builder=(lambda: UnusedGenerationProvider()),
        metrics_registry=metrics,
    )

    assert assembly.metrics_registry is metrics

    assert assembly.service._metrics_registry is metrics


def test_supplied_retrieval_executor_skips_local_builder() -> None:
    engine = create_engine("sqlite://")

    retrieval = EmptyRetrieval()

    def forbidden_retrieval_builder(
        session,
        dataset_version,
    ):
        del session
        del dataset_version

        raise AssertionError("remote retrieval must not build the local retriever")

    assembly = build_serving_assembly(
        engine=engine,
        retrieval_builder=(forbidden_retrieval_builder),
        retrieval_executor=retrieval,
        generation_builder=(lambda: UnusedGenerationProvider()),
    )

    assert assembly.retrieval_executor is retrieval

    assert assembly.runtime._retrieval_executor is retrieval

    assert not isinstance(
        assembly.retrieval_executor,
        LockedRetrievalExecutor,
    )


def test_serving_assembly_builds_reviewed_service_from_shared_resources() -> None:
    from enterprise_genai.application import (
        ReviewedAnsweringService,
    )

    engine = create_engine("sqlite://")

    retrieval = EmptyRetrieval()

    generation = UnusedGenerationProvider()

    assembly = build_serving_assembly(
        engine=engine,
        retrieval_executor=retrieval,
        generation_builder=(lambda: generation),
    )

    assert isinstance(
        assembly.reviewed_service,
        ReviewedAnsweringService,
    )

    assert assembly.reviewed_service._specification_provider is assembly.specification_provider

    assert assembly.reviewed_service._runtime is assembly.runtime

    assert assembly.reviewed_service._generation_provider is assembly.generation_provider
