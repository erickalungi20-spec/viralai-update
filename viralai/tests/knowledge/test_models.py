import pytest
from pydantic import ValidationError as PydanticValidationError

from viralai.core.idm import EvidenceLevel
from viralai.knowledge.models import KnowledgeQuery, MutationKnowledge


def _sample_entry(**overrides) -> MutationKnowledge:
    kwargs = dict(
        virus="HPV16",
        gene="E6",
        position=118,
        reference_base="C",
        observed_base="T",
        known_effect_summary="Test effect summary",
        evidence_level=EvidenceLevel.LEVEL_II_MULTI_STUDY,
        reference_ids=["ref-1"],
    )
    kwargs.update(overrides)
    return MutationKnowledge(**kwargs)


def test_mutation_knowledge_requires_at_least_one_reference():
    with pytest.raises(PydanticValidationError):
        _sample_entry(reference_ids=[])


def test_knowledge_query_matches_on_virus_and_gene():
    entry = _sample_entry()
    assert KnowledgeQuery(virus="HPV16", gene="E6").matches_mutation_knowledge(entry)
    assert not KnowledgeQuery(virus="HIV").matches_mutation_knowledge(entry)
    assert not KnowledgeQuery(gene="E7").matches_mutation_knowledge(entry)


def test_knowledge_query_matches_min_evidence_level():
    strong_entry = _sample_entry(evidence_level=EvidenceLevel.LEVEL_I_EXPERIMENTAL)
    weak_entry = _sample_entry(evidence_level=EvidenceLevel.LEVEL_V_HYPOTHESIS)

    query = KnowledgeQuery(min_evidence_level=EvidenceLevel.LEVEL_III_LIMITED)

    assert query.matches_mutation_knowledge(strong_entry)  # Level I is stronger than III
    assert not query.matches_mutation_knowledge(weak_entry)  # Level V is weaker than III


def test_knowledge_query_with_no_filters_matches_everything():
    entry = _sample_entry()
    assert KnowledgeQuery().matches_mutation_knowledge(entry)
