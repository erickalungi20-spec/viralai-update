from viralai.engines.alignment import GAP, needleman_wunsch


def test_identical_sequences_align_with_no_gaps():
    result = needleman_wunsch("ACGT", "ACGT")
    assert result.aligned_reference == "ACGT"
    assert result.aligned_query == "ACGT"
    assert GAP not in result.aligned_reference


def test_single_deletion_in_query():
    # reference has an extra base the query doesn't
    result = needleman_wunsch("ACGT", "ACT")
    assert len(result.aligned_reference) == len(result.aligned_query)
    assert result.aligned_reference.replace(GAP, "") == "ACGT"
    assert result.aligned_query.replace(GAP, "") == "ACT"
    assert GAP in result.aligned_query


def test_single_insertion_in_query():
    # query has an extra base the reference doesn't
    result = needleman_wunsch("ACT", "ACGT")
    assert result.aligned_reference.replace(GAP, "") == "ACT"
    assert result.aligned_query.replace(GAP, "") == "ACGT"
    assert GAP in result.aligned_reference


def test_alignment_result_sequences_are_equal_length():
    result = needleman_wunsch("ACGTACGT", "ACGTCGT")
    assert len(result.aligned_reference) == len(result.aligned_query)


def test_completely_different_sequences_still_align_without_error():
    result = needleman_wunsch("AAAA", "TTTT")
    assert len(result.aligned_reference) == len(result.aligned_query) == 4
