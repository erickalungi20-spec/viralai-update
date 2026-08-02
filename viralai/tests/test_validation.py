from viralai.common.validation import is_valid_amino_acid_sequence, is_valid_nucleotide_sequence


def test_is_valid_nucleotide_sequence_accepts_iupac_codes():
    assert is_valid_nucleotide_sequence("ACGTUNRYSWKMBDHV-")
    assert is_valid_nucleotide_sequence("acgt")  # case-insensitive


def test_is_valid_nucleotide_sequence_rejects_bad_chars():
    assert not is_valid_nucleotide_sequence("ACGTZ")


def test_is_valid_nucleotide_sequence_rejects_empty():
    assert not is_valid_nucleotide_sequence("")


def test_is_valid_amino_acid_sequence_accepts_standard_codes():
    assert is_valid_amino_acid_sequence("MKVLAT*X")
    assert is_valid_amino_acid_sequence("mkv")  # case-insensitive


def test_is_valid_amino_acid_sequence_rejects_bad_chars():
    assert not is_valid_amino_acid_sequence("MKVB1")


def test_is_valid_amino_acid_sequence_rejects_empty():
    assert not is_valid_amino_acid_sequence("")
