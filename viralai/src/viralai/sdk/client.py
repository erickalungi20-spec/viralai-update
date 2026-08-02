"""
Minimal Python SDK (Commercial Development Workflow Phase 8 item: "Python SDK, CLI").

A thin, typed wrapper over the REST API using httpx (already a dependency via FastAPI's
own test client) -- not a second implementation of the analysis logic, just HTTP calls
to the endpoints in api/routers/. Scope decision: covers the same six operation
categories as the API itself; does not attempt to wrap every possible query parameter
combination -- add methods as real usage patterns emerge rather than speculatively.

Phase 9 update: accepts an optional `api_key`, sent as the X-API-Key header on every
request. Required by the API for write operations (knowledge writes, AI predictions,
simulation runs) as of Phase 9's security wiring -- see ADR-012.
"""

from __future__ import annotations

import httpx

from viralai.core.idm import Genome, Mutation, ProteinMutation
from viralai.knowledge.models import LiteratureReference, MutationKnowledge
from viralai.simulation.laboratory import SimulationExperiment


class ViralAIClient:
    """Usage:
    client = ViralAIClient("http://localhost:8000", api_key="...")
    mutations = client.detect_mutations("ACGT...", "ACGA...")
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """`transport` is an advanced/testing hook for a custom *synchronous* httpx
        transport (e.g. `httpx.MockTransport` for unit tests that don't need a real
        server). It does NOT accept `httpx.ASGITransport` -- that's async-only and
        incompatible with this client's sync `httpx.Client`. To test against the real
        FastAPI app without a separate deployment, run it with uvicorn on a background
        thread and point this client at that real (if local) URL -- see
        tests/conftest.py's `live_server_url` fixture for the pattern.
        """
        headers = {"X-API-Key": api_key} if api_key else {}
        self._http = httpx.Client(
            base_url=base_url, timeout=timeout, transport=transport, headers=headers
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> ViralAIClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- analysis --------------------------------------------------------------------

    def detect_mutations(self, reference_genome: str | Genome, query_genome: str | Genome) -> list[Mutation]:
        response = self._http.post(
            "/analysis/mutations",
            json={"reference_genome": reference_genome, "query_genome": query_genome},
        )
        response.raise_for_status()
        return [Mutation(**m) for m in response.json()["mutations"]]

    def analyze_proteins(
        self, reference_genome: str | Genome, mutations: list[Mutation], gene_annotations: list[dict]
    ) -> list[ProteinMutation]:
        response = self._http.post(
            "/analysis/proteins",
            json={
                "reference_genome": reference_genome,
                "mutations": [m.model_dump(mode="json") for m in mutations],
                "gene_annotations": gene_annotations,
            },
        )
        response.raise_for_status()
        return [ProteinMutation(**pm) for pm in response.json()["protein_mutations"]]

    # -- plugins -------------------------------------------------------------------------

    def list_plugins(self) -> list[dict]:
        response = self._http.get("/plugins")
        response.raise_for_status()
        return response.json()

    # -- knowledge -----------------------------------------------------------------------

    def add_reference(self, reference: LiteratureReference) -> LiteratureReference:
        response = self._http.post("/knowledge/references", json=reference.model_dump(mode="json"))
        response.raise_for_status()
        return LiteratureReference(**response.json())

    def add_mutation_knowledge(self, entry: MutationKnowledge) -> MutationKnowledge:
        response = self._http.post("/knowledge/mutations", json=entry.model_dump(mode="json"))
        response.raise_for_status()
        return MutationKnowledge(**response.json())

    def query_mutation_knowledge(
        self, *, virus: str | None = None, gene: str | None = None
    ) -> list[MutationKnowledge]:
        params = {k: v for k, v in {"virus": virus, "gene": gene}.items() if v is not None}
        response = self._http.get("/knowledge/mutations", params=params)
        response.raise_for_status()
        return [MutationKnowledge(**m) for m in response.json()]

    # -- ai ------------------------------------------------------------------------------

    def predict(
        self, model_name: str, model_version: str, feature_vectors: list[list[float]]
    ) -> dict:
        """Returns the full ResponsibleAIEnvelope dict: {"result": {...}, "disclosure":
        ..., "limitations": ...} -- callers get the disclosure/limitations text
        alongside the predictions, not just the bare numbers.
        """
        response = self._http.post(
            f"/ai/models/{model_name}/{model_version}/predict",
            json={"feature_vectors": feature_vectors},
        )
        response.raise_for_status()
        return response.json()

    # -- simulation ------------------------------------------------------------------------

    def run_simulation(
        self,
        *,
        name: str,
        version: str,
        reference_genome: str,
        population_size: int,
        generations: int,
        mutation_rate: float,
        seed: int,
        notes: str = "",
    ) -> SimulationExperiment:
        response = self._http.post(
            "/simulation/experiments",
            json={
                "name": name,
                "version": version,
                "reference_genome": reference_genome,
                "population_size": population_size,
                "generations": generations,
                "mutation_rate": mutation_rate,
                "seed": seed,
                "notes": notes,
            },
        )
        response.raise_for_status()
        # response is a ResponsibleAIEnvelope -- the SimulationExperiment is nested
        # under "result"
        return SimulationExperiment(**response.json()["result"])

    # -- reports ---------------------------------------------------------------------------

    def export_report(self, report: dict, *, format: str = "markdown") -> str:  # noqa: A002
        response = self._http.post("/reports/export", json=report, params={"format": format})
        response.raise_for_status()
        return response.text
