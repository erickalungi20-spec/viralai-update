import numpy as np

from viralai.ai.features import FEATURE_NAMES, FeatureContext, extract_features, to_vector
from viralai.core.idm import Mutation, MutationType, ProteinMutation, ProteinMutationClass


def _mutation(**overrides) -> Mutation:
    kwargs = dict(
        position=100,
        reference_base="A",
        observed_base="G",
        mutation_type=MutationType.SUBSTITUTION,
        confidence_score=0.9,
    )
    kwargs.update(overrides)
    return Mutation(**kwargs)


def test_extract_features_returns_all_expected_keys():
    features = extract_features(_mutation(), FeatureContext(genome_length=1000))
    assert set(features.keys()) == set(FEATURE_NAMES)


def test_position_is_normalized_by_genome_length():
    features = extract_features(_mutation(position=500), FeatureContext(genome_length=1000))
    assert features["position_normalized"] == 0.5


def test_mutation_type_one_hot_encoding():
    sub_features = extract_features(
        _mutation(mutation_type=MutationType.SUBSTITUTION), FeatureContext(genome_length=100)
    )
    assert sub_features["is_substitution"] == 1.0
    assert sub_features["is_insertion"] == 0.0
    assert sub_features["is_deletion"] == 0.0

    del_features = extract_features(
        _mutation(mutation_type=MutationType.DELETION), FeatureContext(genome_length=100)
    )
    assert del_features["is_deletion"] == 1.0
    assert del_features["is_substitution"] == 0.0


def test_missing_context_defaults_to_neutral_values():
    features = extract_features(_mutation(), FeatureContext(genome_length=100))
    assert features["entropy_at_position"] == 0.0
    assert features["population_frequency"] == 0.0
    assert features["affects_protein"] == 0.0


def test_protein_mutation_context_sets_classification_flags():
    source = _mutation()
    protein_mutation = ProteinMutation(
        source_mutation=source,
        protein_id="E6",
        position_aa=10,
        reference_aa="Q",
        observed_aa="L",
        classification=ProteinMutationClass.MISSENSE,
    )
    context = FeatureContext(genome_length=1000, protein_mutation=protein_mutation)

    features = extract_features(source, context)

    assert features["affects_protein"] == 1.0
    assert features["is_missense"] == 1.0
    assert features["is_synonymous"] == 0.0
    assert features["is_nonsense"] == 0.0
    assert features["is_frameshift"] == 0.0


def test_to_vector_preserves_feature_order():
    features_list = [
        extract_features(_mutation(position=10), FeatureContext(genome_length=100)),
        extract_features(_mutation(position=50), FeatureContext(genome_length=100)),
    ]

    X = to_vector(features_list)

    assert isinstance(X, np.ndarray)
    assert X.shape == (2, len(FEATURE_NAMES))
    position_col = FEATURE_NAMES.index("position_normalized")
    assert X[0, position_col] == 0.1
    assert X[1, position_col] == 0.5
