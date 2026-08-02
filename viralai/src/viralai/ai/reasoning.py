"""
Scientific Reasoning Engine (Blueprint Ch.26.8, Ch.12.7).

Chains: observed mutation -> protein affected -> known literature (via the Research
Graph) -> evolutionary conservation -> AI prediction -> confidence -> a *research*
recommendation. This is the module that actually queries the Research Graph built in
Phase 3, closing the loop the strategic plan promised.

Ethics note (Ch.36, enforced here not just documented): every ReasoningRecord this engine
produces is tagged EvidenceLevel.LEVEL_IV_COMPUTATIONAL or lower, and `recommendation`
text is generated from a fixed template that never uses clinical/diagnostic language. This
is deliberate, not an oversight -- a downstream caller cannot accidentally get a
confident-sounding clinical claim out of this engine even if they wanted one.
"""

from __future__ import annotations

from pydantic import BaseModel

from viralai.ai.explainability import ShapExplainer
from viralai.ai.features import FeatureContext, extract_features, to_vector
from viralai.ai.hotspot_model import MutationHotspotModel
from viralai.core.idm import EvidenceLevel, Mutation
from viralai.graph.research_graph import ResearchGraph


class ReasoningRecord(BaseModel):
    """The structured output Ch.26.8 describes: every field a researcher would need to
    evaluate the prediction, not just a bare probability number.
    """

    virus: str
    mutation_summary: str
    affected_protein: str | None
    literature_citations: list[str]
    evolutionary_conservation: float | None
    ai_prediction_positive: bool
    ai_confidence: float
    top_contributing_features: list[tuple[str, float]]
    evidence_level: EvidenceLevel
    recommendation: str


class ScientificReasoningEngine:
    def __init__(self, graph: ResearchGraph) -> None:
        self._graph = graph

    def reason(
        self,
        virus: str,
        mutation: Mutation,
        context: FeatureContext,
        model: MutationHotspotModel,
        explainer: ShapExplainer,
    ) -> ReasoningRecord:
        mutation_id = f"{virus}:mutation:{mutation.position}:{mutation.reference_base}>{mutation.observed_base}"

        affected_protein = self._find_affected_protein(mutation_id)
        citations = self._find_citations(mutation_id)

        feature_vector = to_vector([extract_features(mutation, context)])
        prediction = bool(model.predict(feature_vector)[0])
        confidence = float(model.predict_proba(feature_vector)[0])
        top_features = explainer.top_features(feature_vector[0], n=3)

        recommendation = _build_recommendation(
            prediction=prediction,
            confidence=confidence,
            has_literature=bool(citations),
            affected_protein=affected_protein,
        )

        return ReasoningRecord(
            virus=virus,
            mutation_summary=(
                f"{mutation.reference_base}{mutation.position}{mutation.observed_base} "
                f"({mutation.mutation_type.value})"
            ),
            affected_protein=affected_protein,
            literature_citations=citations,
            evolutionary_conservation=context.entropy_at_position,
            ai_prediction_positive=prediction,
            ai_confidence=confidence,
            top_contributing_features=top_features,
            evidence_level=EvidenceLevel.LEVEL_IV_COMPUTATIONAL,
            recommendation=recommendation,
        )

    def _find_affected_protein(self, mutation_id: str) -> str | None:
        if not self._graph.has_node(mutation_id):
            return None
        neighbors = self._graph.neighbors(mutation_id, direction="out")
        protein_neighbors = [
            n
            for n in neighbors
            if self._graph.has_node(n) and self._graph.get_node(n).get("protein_name")
        ]
        return protein_neighbors[0] if protein_neighbors else None

    def _find_citations(self, mutation_id: str) -> list[str]:
        if not self._graph.has_node(mutation_id):
            return []
        return self._graph.publications_for_mutation(mutation_id)


def _build_recommendation(
    *, prediction: bool, confidence: float, has_literature: bool, affected_protein: str | None
) -> str:
    """Fixed-template recommendation text -- deliberately not free-form generation, so
    the language stays within research-use bounds every time (Ch.36). No diagnosis, no
    treatment language, ever.
    """
    parts: list[str] = []

    if prediction:
        parts.append(
            f"This mutation is computationally flagged as a potential hotspot "
            f"(model confidence: {confidence:.0%})."
        )
    else:
        parts.append(
            f"This mutation is not flagged as a hotspot by the current model "
            f"(model confidence in that assessment: {confidence:.0%})."
        )

    if affected_protein:
        parts.append(f"It maps to protein '{affected_protein}'.")

    if has_literature:
        parts.append(
            "Published literature already describes this position -- review the cited sources."
        )
    else:
        parts.append(
            "No published literature is linked to this position in the current Knowledge Base; "
            "this is a computational prediction only and requires experimental or literature "
            "validation before any further inference is drawn."
        )

    parts.append(
        "This is a research-use computational assessment, not a clinical or diagnostic finding."
    )
    return " ".join(parts)
