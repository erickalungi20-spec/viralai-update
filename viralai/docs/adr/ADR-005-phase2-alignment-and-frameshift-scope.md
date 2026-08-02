# ADR-005: Phase 2 alignment strategy and indel/frameshift scope

## Status
Accepted

## Context
The Mutation Engine (Ch.23) and Protein Engine (Ch.24) both need to compare a query
sequence against a reference. When sequences are the same length, positional comparison
is sufficient and fast. When they differ (insertions/deletions occurred), correspondence
between reference and query positions requires alignment — a real algorithmic problem, not
something to fake.

## Decision
1. **Equal-length fast path.** If reference and query are the same length, assume they are
   already positionally aligned (true for consensus genomes called against the same
   reference coordinate system, which is the common case) and skip alignment entirely.
2. **Unequal-length path.** Run a from-scratch Needleman-Wunsch global alignment
   (`viralai.engines.alignment`) — linear gap penalty, O(n*m) time/space, pure Python, no
   external dependency.
3. **Frameshift scope limitation.** The Protein Engine classifies every single-nucleotide
   insertion/deletion within a gene as FRAMESHIFT. It does not merge adjacent single-base
   indels into multi-base "Complex Mutations" (Ch.23.5) to detect genuinely in-frame
   indels (e.g. a clean 3-base deletion). This means a true in-frame indel will currently
   be reported as a small number of individual frameshift events rather than one correctly
   classified in-frame event.

## Consequences
- **Positive:** correct behavior for the overwhelmingly common case (SNPs against a
  consensus reference) with zero external dependencies, and honest, bounded incorrectness
  for the less common case (multi-base in-frame indels) rather than silently wrong or
  fabricated classifications.
- **Negative:** O(n*m) alignment does not scale to whole-genome-vs-whole-genome comparison
  at production volume — fine for gene-length sequences and test/research use now, but
  will need replacing for large-scale surveillance workloads.
- **Negative:** the frameshift-only indel classification will misclassify true in-frame
  indels until Complex Mutation merging is implemented.

## Trigger for revisiting
- Alignment performance: the first time whole-genome (not gene-length) alignment is
  needed at volume — swap in a proper library (parasail, edlib, or minimap2 bindings).
- Frameshift accuracy: the first time a real research use case needs correct in-frame
  indel classification — implement adjacent-indel merging into Complex Mutation events per
  Ch.23.5 before trusting frameshift calls near multi-base indels.

## Alternatives considered
- **Depend on Biopython/parasail from Phase 2.** Rejected for now — adds a dependency for
  a problem the from-scratch implementation already solves correctly at this scale;
  revisit when performance, not correctness, is the limiting factor.
