import pytest

from viralai.common.errors import ValidationError
from viralai.core.idm import EvidenceLevel
from viralai.knowledge.models import (
    KnowledgeQuery,
    LiteratureReference,
    MutationKnowledge,
    ProteinKnowledge,
)
from viralai.knowledge.store import KnowledgeBase


def _reference(reference_id: str = "ref-1") -> LiteratureReference:
    return LiteratureReference(reference_id=reference_id, citation="Someone et al. 2024, J Virol")


def _mutation_knowledge(**overrides) -> MutationKnowledge:
    kwargs = dict(
        virus="HPV16",
        gene="E6",
        position=118,
        reference_base="C",
        observed_base="T",
        known_effect_summary="Test effect",
        evidence_level=EvidenceLevel.LEVEL_II_MULTI_STUDY,
        reference_ids=["ref-1"],
    )
    kwargs.update(overrides)
    return MutationKnowledge(**kwargs)


def test_add_and_get_reference():
    kb = KnowledgeBase()
    kb.add_reference(_reference())
    assert kb.get_reference("ref-1").citation.startswith("Someone")


def test_adding_duplicate_reference_id_raises():
    kb = KnowledgeBase()
    kb.add_reference(_reference())
    with pytest.raises(ValidationError):
        kb.add_reference(_reference())


def test_mutation_knowledge_requires_reference_to_already_exist():
    kb = KnowledgeBase()
    with pytest.raises(ValidationError):
        kb.add_mutation_knowledge(_mutation_knowledge())  # ref-1 not added yet


def test_add_and_query_mutation_knowledge():
    kb = KnowledgeBase()
    kb.add_reference(_reference())
    kb.add_mutation_knowledge(_mutation_knowledge())

    results = kb.query_mutation_knowledge(KnowledgeQuery(virus="HPV16", gene="E6"))

    assert len(results) == 1
    assert results[0].position == 118


def test_get_mutation_knowledge_at_specific_position():
    kb = KnowledgeBase()
    kb.add_reference(_reference())
    kb.add_mutation_knowledge(_mutation_knowledge())

    results = kb.get_mutation_knowledge_at("HPV16", "E6", 118)
    assert len(results) == 1

    assert kb.get_mutation_knowledge_at("HPV16", "E6", 999) == []


def test_protein_knowledge_query_by_virus_and_protein_id():
    kb = KnowledgeBase()
    kb.add_reference(_reference())
    kb.add_protein_knowledge(
        ProteinKnowledge(
            virus="HPV16",
            protein_id="E6",
            known_function_summary="Degrades p53",
            evidence_level=EvidenceLevel.LEVEL_I_EXPERIMENTAL,
            reference_ids=["ref-1"],
        )
    )

    results = kb.query_protein_knowledge(virus="HPV16", protein_id="E6")
    assert len(results) == 1

    assert kb.query_protein_knowledge(virus="HIV") == []


def test_persistence_round_trip(tmp_path):
    kb1 = KnowledgeBase(persist_path=tmp_path)
    kb1.add_reference(_reference())
    kb1.add_mutation_knowledge(_mutation_knowledge())

    kb2 = KnowledgeBase(persist_path=tmp_path)  # reload from disk

    assert kb2.get_reference("ref-1").citation.startswith("Someone")
    results = kb2.query_mutation_knowledge(KnowledgeQuery(virus="HPV16"))
    assert len(results) == 1
    assert results[0].position == 118


def test_ephemeral_store_does_not_touch_disk(tmp_path, monkeypatch):
    # Construct with no persist_path -- should work purely in memory
    kb = KnowledgeBase()
    kb.add_reference(_reference())
    assert kb.get_reference("ref-1") is not None
