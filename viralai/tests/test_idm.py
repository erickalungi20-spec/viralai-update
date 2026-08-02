import pytest
from pydantic import ValidationError as PydanticValidationError

from viralai.core.idm import (
    Analysis,
    AnalysisStatus,
    CDSRegion,
    EvidenceLevel,
    Genome,
    GenomeKind,
    GenomeStrandedness,
    GenomeTopology,
    GeneFeature,
    Mutation,
    MutationType,
    Protein,
    ProteinMutation,
    ProteinMutationClass,
    Variant,
)


def test_genome_accepts_valid_sequence():
    genome = Genome(genome_id="g1", virus_species="HPV16", sequence="ACGTACGTN")
    assert genome.sequence == "ACGTACGTN"


def test_genome_rejects_empty_sequence():
    with pytest.raises(PydanticValidationError):
        Genome(genome_id="g1", virus_species="HPV16", sequence="")


def test_genome_rejects_invalid_alphabet():
    with pytest.raises(PydanticValidationError):
        Genome(genome_id="g1", virus_species="HPV16", sequence="ACGTZZZ")


def test_genome_supports_viral_genome_metadata():
    genome = Genome(
        genome_id="g2",
        virus_species="InfluenzaA",
        sequence="ACGTACTG",
        genome_kind=GenomeKind.RNA,
        strandedness=GenomeStrandedness.SINGLE_STRANDED,
        topology=GenomeTopology.SEGMENTED,
        segment_count=8,
    )
    assert genome.genome_kind == GenomeKind.RNA
    assert genome.strandedness == GenomeStrandedness.SINGLE_STRANDED
    assert genome.topology == GenomeTopology.SEGMENTED
    assert genome.is_segmented is True
    assert genome.segment_count == 8


def test_genome_supports_cds_regions():
    genome = Genome(
        genome_id="g3",
        virus_species="HPV16",
        sequence="ACGTACGT",
        cds_regions=[
            CDSRegion(name="E6", start=0, end=5),
            CDSRegion(name="E7", start=6, end=11),
        ],
    )
    assert genome.cds_regions[0].name == "E6"
    assert genome.cds_regions[1].end == 11


def test_genome_supports_gene_features():
    genome = Genome(
        genome_id="g4",
        virus_species="HPV16",
        sequence="ACGTACGT",
        gene_features=[
            GeneFeature(name="E6", start=0, end=3, feature_type="orf"),
            GeneFeature(name="E7", start=4, end=7, feature_type="gene"),
        ],
    )
    assert genome.gene_features[0].feature_type == "orf"
    assert genome.gene_features[1].end == 7


def test_mutation_confidence_score_bounds():
    mutation = Mutation(
        position=100,
        reference_base="A",
        observed_base="G",
        mutation_type=MutationType.SUBSTITUTION,
        confidence_score=0.95,
    )
    assert 0.0 <= mutation.confidence_score <= 1.0
    assert mutation.evidence_level == EvidenceLevel.LEVEL_IV_COMPUTATIONAL

    with pytest.raises(PydanticValidationError):
        Mutation(
            position=100,
            reference_base="A",
            observed_base="G",
            mutation_type=MutationType.SUBSTITUTION,
            confidence_score=1.5,
        )


def test_protein_mutation_links_back_to_source_mutation():
    mutation = Mutation(
        position=10,
        reference_base="A",
        observed_base="T",
        mutation_type=MutationType.SUBSTITUTION,
    )
    protein_mutation = ProteinMutation(
        source_mutation=mutation,
        protein_id="E6",
        position_aa=4,
        reference_aa="K",
        observed_aa="N",
        classification=ProteinMutationClass.MISSENSE,
    )
    assert protein_mutation.source_mutation.position == 10
    assert protein_mutation.classification == ProteinMutationClass.MISSENSE


def test_protein_holds_multiple_mutations():
    m1 = Mutation(
        position=1, reference_base="A", observed_base="G", mutation_type=MutationType.SUBSTITUTION
    )
    m2 = Mutation(
        position=2, reference_base="C", observed_base="T", mutation_type=MutationType.SUBSTITUTION
    )
    protein = Protein(protein_id="p1", amino_acid_sequence="MKV", associated_mutations=[m1, m2])
    assert len(protein.associated_mutations) == 2


def test_variant_population_frequency_bounds():
    variant = Variant(variant_id="v1", population_frequency=0.42)
    assert variant.population_frequency == 0.42
    with pytest.raises(PydanticValidationError):
        Variant(variant_id="v1", population_frequency=1.2)


def test_analysis_default_status_is_pending():
    analysis = Analysis(analysis_id="a1", workflow_name="test-workflow")
    assert analysis.status == AnalysisStatus.PENDING
