from viralai.core.event_bus import EventBus
from viralai.core.idm import (
    Genome,
    GenomeKind,
    GenomeStrandedness,
    GenomeTopology,
    MutationType,
    ProteinMutationClass,
)
from viralai.engines.mutation_engine import (
    MUTATION_ANALYSIS_COMPLETE_TOPIC,
    MUTATION_DETECTED_TOPIC,
    MutationEngine,
)


def test_equal_length_detects_single_substitution():
    engine = MutationEngine()
    mutations = engine.detect_mutations(reference="ACGTACGT", query="ACGTAGGT")

    assert len(mutations) == 1
    mutation = mutations[0]
    assert mutation.position == 5
    assert mutation.reference_base == "C"
    assert mutation.observed_base == "G"
    assert mutation.mutation_type == MutationType.SUBSTITUTION


def test_equal_length_no_mutations_when_identical():
    engine = MutationEngine()
    mutations = engine.detect_mutations(reference="ACGTACGT", query="ACGTACGT")
    assert mutations == []


def test_equal_length_detects_multiple_substitutions():
    engine = MutationEngine()
    mutations = engine.detect_mutations(reference="AAAA", query="ATAT")
    positions = {m.position for m in mutations}
    assert positions == {1, 3}


def test_unequal_length_detects_deletion():
    engine = MutationEngine()
    mutations = engine.detect_mutations(reference="ACGTACGT", query="ACGTCGT")

    deletion_mutations = [m for m in mutations if m.mutation_type == MutationType.DELETION]
    assert len(deletion_mutations) == 1


def test_unequal_length_detects_insertion():
    engine = MutationEngine()
    mutations = engine.detect_mutations(reference="ACGTCGT", query="ACGTACGT")

    insertion_mutations = [m for m in mutations if m.mutation_type == MutationType.INSERTION]
    assert len(insertion_mutations) == 1


def test_unequal_length_coalesces_adjacent_indels():
    engine = MutationEngine()

    mutations = engine.detect_mutations(reference="ATGAAACCCTAA", query="ATGAAATAA")

    assert len(mutations) == 1
    deletion = mutations[0]
    assert deletion.mutation_type == MutationType.DELETION
    assert deletion.reference_base == "CCC"


def test_publishes_events_when_event_bus_provided():
    bus = EventBus()
    engine = MutationEngine(event_bus=bus)

    engine.detect_mutations(reference="ACGT", query="ACTT", source="test")

    detected_events = bus.history(MUTATION_DETECTED_TOPIC)
    complete_events = bus.history(MUTATION_ANALYSIS_COMPLETE_TOPIC)
    assert len(detected_events) == 1
    assert complete_events[0].payload["mutation_count"] == 1
    assert complete_events[0].source == "test"


def test_no_events_published_without_event_bus():
    engine = MutationEngine()  # no event_bus
    mutations = engine.detect_mutations(reference="ACGT", query="ACTT")
    assert len(mutations) == 1  # still works, just no events


def test_detects_mutations_for_segmented_genome_objects():
    reference = Genome(
        genome_id="ref-seg",
        virus_species="InfluenzaA",
        sequence="ACGT",
        segments=["ACGT", "TGCA"],
        genome_kind=GenomeKind.RNA,
        strandedness=GenomeStrandedness.SINGLE_STRANDED,
        topology=GenomeTopology.SEGMENTED,
        segment_count=2,
    )
    query = Genome(
        genome_id="query-seg",
        virus_species="InfluenzaA",
        sequence="ACGT",
        segments=["ACGT", "TGTA"],
        genome_kind=GenomeKind.RNA,
        strandedness=GenomeStrandedness.SINGLE_STRANDED,
        topology=GenomeTopology.SEGMENTED,
        segment_count=2,
    )

    mutations = MutationEngine().detect_mutations(reference, query)

    assert len(mutations) == 1
    assert mutations[0].supporting_evidence["segment_index"] == 1
    assert mutations[0].supporting_evidence["genome_kind"] == GenomeKind.RNA.value


def test_reverse_complement_matches_are_detected_as_transcriptional_equivalence():
    engine = MutationEngine()
    reference = Genome(
        genome_id="ref-rc",
        virus_species="InfluenzaA",
        sequence="ACGT",
        genome_kind=GenomeKind.RNA,
        strandedness=GenomeStrandedness.SINGLE_STRANDED,
        topology=GenomeTopology.LINEAR,
    )
    query = Genome(
        genome_id="query-rc",
        virus_species="InfluenzaA",
        sequence="ACGT",
        genome_kind=GenomeKind.RNA,
        strandedness=GenomeStrandedness.SINGLE_STRANDED,
        topology=GenomeTopology.LINEAR,
    )

    mutations = engine.detect_mutations(reference, query, reverse_complement=True)

    assert mutations == []


def test_rna_genomes_use_rna_specific_evidence():
    engine = MutationEngine()
    mutations = engine.detect_mutations(
        reference="AUG",
        query="AUA",
        genome_kind=GenomeKind.RNA,
        strandedness=GenomeStrandedness.SINGLE_STRANDED,
        topology=GenomeTopology.LINEAR,
    )

    assert len(mutations) == 1
    assert mutations[0].supporting_evidence["nucleic_acid_kind"] == GenomeKind.RNA.value


def test_mutations_are_tagged_with_cds_context():
    engine = MutationEngine()
    genome = Genome(
        genome_id="genome-cds",
        virus_species="HPV16",
        sequence="ACGTACGT",
        cds_regions=[
            {"name": "E6", "start": 0, "end": 3},
            {"name": "E7", "start": 4, "end": 7},
        ],
    )

    mutations = engine.detect_mutations(genome, "ACGTCCGT")

    assert len(mutations) == 1
    assert mutations[0].supporting_evidence["cds_name"] == "E7"
    assert mutations[0].supporting_evidence["cds_position"] == 0


def test_translates_cds_to_protein_mutations():
    engine = MutationEngine()
    genome = Genome(
        genome_id="genome-protein",
        virus_species="HPV16",
        sequence="ATGAAATTT",
        cds_regions=[{"name": "E6", "start": 0, "end": 8}],
    )

    protein_mutations = engine.translate_to_protein_mutations(genome, "ATGAAATCT")

    assert len(protein_mutations) == 1
    assert protein_mutations[0].classification == ProteinMutationClass.MISSENSE
    assert protein_mutations[0].protein_id == "E6"


def test_gene_features_are_used_for_contextual_annotation():
    engine = MutationEngine()
    genome = Genome(
        genome_id="genome-features",
        virus_species="HPV16",
        sequence="ACGTACGT",
        gene_features=[{"name": "E6", "start": 0, "end": 3, "feature_type": "orf"}],
    )

    mutations = engine.detect_mutations(genome, "ACGTCCGT")

    assert len(mutations) == 1
    assert mutations[0].supporting_evidence["gene_feature"] == "E6"
    assert mutations[0].supporting_evidence["gene_feature_type"] == "orf"
