import pytest

from viralai.common.errors import ValidationError
from viralai.engines.genetic_code import translate


def test_translate_simple_sequence():
    # ATG (Met) CTG (Leu) TAA (stop)
    assert translate("ATGCTGTAA") == "ML"


def test_translate_stops_at_stop_codon_by_default():
    assert translate("ATGTAACTG") == "M"  # stop halts translation; trailing CTG never reached


def test_translate_continues_past_stop_when_requested():
    result = translate("ATGTAACTG", stop_at_stop_codon=False)
    assert result == "M*L"


def test_translate_normalizes_rna_to_dna():
    assert translate("AUGCUGUAA") == "ML"


def test_translate_drops_incomplete_trailing_codon():
    assert translate("ATGCT") == "M"  # trailing "CT" is incomplete, dropped


def test_translate_raises_on_invalid_codon():
    with pytest.raises(ValidationError):
        translate("ATGNNN", stop_at_stop_codon=False)


def test_translate_is_cached_and_returns_consistent_results():
    first = translate("ATGCTGTAA")
    second = translate("ATGCTGTAA")
    assert first == second == "ML"
