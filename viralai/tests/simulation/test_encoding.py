import numpy as np
import pytest

from viralai.common.errors import ValidationError
from viralai.simulation.encoding import decode, encode


def test_encode_decode_round_trip():
    sequence = "ACGTACGT"
    assert decode(encode(sequence)) == sequence


def test_encode_is_case_insensitive():
    assert list(encode("acgt")) == list(encode("ACGT"))


def test_encode_rejects_non_acgt_characters():
    with pytest.raises(ValidationError):
        encode("ACGTN")  # ambiguity codes not accepted for simulation


def test_encode_returns_uint8_array():
    encoded = encode("ACGT")
    assert isinstance(encoded, np.ndarray)
    assert encoded.dtype == np.uint8
