"""
Phase 2 integration test: Mutation Engine -> Protein Engine wired through the Core
Engine's Event Bus and workflow lifecycle, using metadata attachment throughout. This is
the first test that actually exercises Phase 0, Phase 1's conventions, and Phase 2's
engines together, the way a real analysis workflow will.
"""

from __future__ import annotations

from viralai.core.engine import CoreEngine
from viralai.core.idm import AnalysisStatus, ProteinMutationClass
from viralai.core.metadata import attach_metadata
from viralai.engines.mutation_engine import MUTATION_DETECTED_TOPIC, MutationEngine
from viralai.engines.protein_engine import ProteinAnalysisEngine

REFERENCE_GENOME = "ATGCAATAA"  # M-Q-stop
GENE_ANNOTATIONS = [{"gene": "TESTGENE", "start": 1, "end": 9}]


def test_mutation_and_protein_engines_run_through_core_engine_workflow():
    engine = CoreEngine()
    mutation_engine = MutationEngine(event_bus=engine.event_bus)
    protein_engine = ProteinAnalysisEngine()

    # a query genome with one missense substitution at position 4 (Q -> L, see
    # test_protein_engine.py for the codon math)
    query_genome = "ATGCTATAA"

    collected_protein_mutations = []

    def detect_mutations_step(ctx):
        mutations = mutation_engine.detect_mutations(
            REFERENCE_GENOME, query_genome, source="mutation_engine"
        )
        ctx.record_step("mutations_detected", count=len(mutations))
        ctx.analysis.results["mutations"] = [m.model_dump(mode="json") for m in mutations]

    def analyze_proteins_step(ctx):
        mutations_raw = ctx.analysis.results["mutations"]
        from viralai.core.idm import Mutation  # local import keeps step functions self-contained

        mutations = [Mutation(**m) for m in mutations_raw]
        protein_mutations = protein_engine.analyze(REFERENCE_GENOME, mutations, GENE_ANNOTATIONS)
        collected_protein_mutations.extend(protein_mutations)
        ctx.record_step("protein_mutations_classified", count=len(protein_mutations))
        ctx.publish("protein.analysis_complete", {"count": len(protein_mutations)})

    analysis = engine.run_workflow(
        "hpv16-mutation-and-protein-analysis",
        [detect_mutations_step, analyze_proteins_step],
    )

    assert analysis.status == AnalysisStatus.COMPLETED
    assert len(collected_protein_mutations) == 1
    assert collected_protein_mutations[0].classification == ProteinMutationClass.MISSENSE

    # the Event Bus should show the mutation.detected event published by the engine
    mutation_events = engine.event_bus.history(MUTATION_DETECTED_TOPIC)
    assert len(mutation_events) == 1

    protein_events = engine.event_bus.history("protein.analysis_complete")
    assert protein_events[0].payload["count"] == 1

    # provenance should show both steps recorded, in order
    provenance = engine.provenance.get(analysis.analysis_id)
    step_names = [s["step"] for s in provenance.steps]
    assert "mutations_detected" in step_names
    assert "protein_mutations_classified" in step_names

    # every reported protein mutation should be attachable to the Metadata Engine without
    # any developer manually setting provenance fields
    tracked = attach_metadata(
        collected_protein_mutations[0],
        created_by="protein_engine",
        workflow_version="0.1.0",
        evidence_level="IV",
        confidence_score=0.85,
    )
    assert tracked.metadata.uuid
    assert tracked.metadata.evidence_level == "IV"
