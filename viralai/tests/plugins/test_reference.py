import hashlib

import pytest

from viralai.common.errors import ValidationError
from viralai.plugins.reference import (
    ReferenceGenomeNotFoundError,
    ReferenceGenomeSpec,
    load_reference_genome,
)


def test_missing_file_raises_not_found_with_helpful_message(tmp_path):
    spec = ReferenceGenomeSpec(accession="NC_000000.0", expected_length=100)
    with pytest.raises(ReferenceGenomeNotFoundError) as excinfo:
        load_reference_genome(tmp_path / "nope.fasta", spec)
    assert "NC_000000.0" in str(excinfo.value)


def test_valid_fasta_loads_successfully(tmp_path):
    sequence = "ACGT" * 25  # length 100
    fasta = tmp_path / "ref.fasta"
    fasta.write_text(f">synthetic-fixture\n{sequence}\n")

    spec = ReferenceGenomeSpec(accession="TEST.1", expected_length=100)
    loaded = load_reference_genome(fasta, spec)

    assert loaded == sequence


def test_length_mismatch_raises_validation_error(tmp_path):
    fasta = tmp_path / "ref.fasta"
    fasta.write_text(">synthetic\nACGT\n")

    spec = ReferenceGenomeSpec(accession="TEST.1", expected_length=100)
    with pytest.raises(ValidationError):
        load_reference_genome(fasta, spec)


def test_checksum_mismatch_raises_validation_error(tmp_path):
    sequence = "ACGT" * 25
    fasta = tmp_path / "ref.fasta"
    fasta.write_text(f">synthetic\n{sequence}\n")

    wrong_checksum = "0" * 64
    spec = ReferenceGenomeSpec(accession="TEST.1", expected_length=100, sha256=wrong_checksum)
    with pytest.raises(ValidationError):
        load_reference_genome(fasta, spec)


def test_correct_checksum_passes(tmp_path):
    sequence = "ACGT" * 25
    fasta = tmp_path / "ref.fasta"
    fasta.write_text(f">synthetic\n{sequence}\n")

    correct_checksum = hashlib.sha256(sequence.encode("ascii")).hexdigest()
    spec = ReferenceGenomeSpec(accession="TEST.1", expected_length=100, sha256=correct_checksum)

    loaded = load_reference_genome(fasta, spec)
    assert loaded == sequence


def test_multiline_fasta_is_concatenated(tmp_path):
    fasta = tmp_path / "ref.fasta"
    fasta.write_text(">synthetic\nACGT\nACGT\nACGT\n")

    spec = ReferenceGenomeSpec(accession="TEST.1", expected_length=12)
    loaded = load_reference_genome(fasta, spec)

    assert loaded == "ACGTACGTACGT"
