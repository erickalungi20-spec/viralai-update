from viralai.core.idm import Mutation, MutationType, ProteinMutationClass
from viralai.engines.protein_engine import ProteinAnalysisEngine, estimate_substitution_severity

# Reference gene "ATGCAATAA": codon0=ATG(M), codon1=CAA(Q), codon2=TAA(stop)
REFERENCE_GENOME = "ATGCAATAA"
GENE_ANNOTATIONS = [{"gene": "TESTGENE", "start": 1, "end": 9}]


def test_translate_gene_returns_reference_protein():
    engine = ProteinAnalysisEngine()
    protein = engine.translate_gene(REFERENCE_GENOME, GENE_ANNOTATIONS[0])
    assert protein == "MQ"  # stop not included by default


def test_missense_substitution_classified_correctly():
    # position 4 (0-based): second base of codon1 "CAA" -> "CTA" (Leu). Q -> L, missense.
    mutation = Mutation(
        position=4, reference_base="A", observed_base="T", mutation_type=MutationType.SUBSTITUTION
    )
    engine = ProteinAnalysisEngine()

    results = engine.analyze(REFERENCE_GENOME, [mutation], GENE_ANNOTATIONS)

    assert len(results) == 1
    pm = results[0]
    assert pm.classification == ProteinMutationClass.MISSENSE
    assert pm.reference_aa == "Q"
    assert pm.observed_aa == "L"
    assert pm.position_aa == 1
    assert pm.protein_id == "TESTGENE"


def test_synonymous_substitution_classified_correctly():
    # position 5 (0-based): third base of codon1 "CAA" -> "CAG" (still Gln). synonymous.
    mutation = Mutation(
        position=5, reference_base="A", observed_base="G", mutation_type=MutationType.SUBSTITUTION
    )
    engine = ProteinAnalysisEngine()

    results = engine.analyze(REFERENCE_GENOME, [mutation], GENE_ANNOTATIONS)

    assert results[0].classification == ProteinMutationClass.SYNONYMOUS
    assert results[0].reference_aa == results[0].observed_aa == "Q"


def test_nonsense_substitution_classified_correctly():
    # position 3 (0-based): first base of codon1 "CAA" -> "TAA" (stop). Q -> nonsense.
    mutation = Mutation(
        position=3, reference_base="C", observed_base="T", mutation_type=MutationType.SUBSTITUTION
    )
    engine = ProteinAnalysisEngine()

    results = engine.analyze(REFERENCE_GENOME, [mutation], GENE_ANNOTATIONS)

    assert results[0].classification == ProteinMutationClass.NONSENSE
    assert results[0].reference_aa == "Q"
    assert results[0].observed_aa == "*"


def test_indel_within_gene_classified_as_frameshift():
    mutation = Mutation(
        position=4, reference_base="A", observed_base="", mutation_type=MutationType.DELETION
    )
    engine = ProteinAnalysisEngine()

    results = engine.analyze(REFERENCE_GENOME, [mutation], GENE_ANNOTATIONS)

    assert results[0].classification == ProteinMutationClass.FRAMESHIFT


def test_three_base_deletion_is_classified_as_in_frame():
    mutation = Mutation(
        position=3, reference_base="CAA", observed_base="", mutation_type=MutationType.DELETION
    )
    engine = ProteinAnalysisEngine()

    results = engine.analyze(REFERENCE_GENOME, [mutation], GENE_ANNOTATIONS)

    assert results[0].classification == ProteinMutationClass.IN_FRAME_DELETION


def test_mutation_outside_any_gene_is_skipped():
    mutation = Mutation(
        position=100, reference_base="A", observed_base="T", mutation_type=MutationType.SUBSTITUTION
    )
    engine = ProteinAnalysisEngine()

    results = engine.analyze(REFERENCE_GENOME, [mutation], GENE_ANNOTATIONS)

    assert results == []


def test_estimate_substitution_severity_conservative_within_group():
    # both nonpolar
    assert estimate_substitution_severity("L", "I") == "conservative"


def test_estimate_substitution_severity_radical_across_groups():
    # acidic (D) vs basic (K)
    assert estimate_substitution_severity("D", "K") == "radical"


def test_estimate_substitution_severity_none_when_identical():
    assert estimate_substitution_severity("A", "A") == "none"


def test_estimate_substitution_severity_radical_for_stop_codon_involvement():
    assert estimate_substitution_severity("Q", "*") == "radical"
