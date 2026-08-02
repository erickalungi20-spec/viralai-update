# HPV16 reference genome

This directory does not contain the real reference sequence. That's deliberate — see
`docs/PLUGIN_DEVELOPMENT_STANDARD.md` §4: real reference genomes aren't committed to
source control by default.

## What to fetch

- **Accession:** NC_001526.4 (RefSeq), legacy GenBank accession K02718.1
- **Expected length:** 7906 bp
- **Source:** NCBI GenBank/RefSeq

## How to fetch it

From a machine with normal internet access (this sandbox's network policy does not permit
fetching from NCBI, so this step has to happen on your own machine):

```bash
# Using NCBI E-utilities (efetch) — requires internet access to eutils.ncbi.nlm.nih.gov
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=NC_001526.4&rettype=fasta&retmode=text" \
  -o reference.fasta
```

Or download manually from the NCBI Nucleotide page for `NC_001526.4` and save the FASTA as
`reference.fasta` in this directory.

## After fetching

Once `reference.fasta` is in place, run the plugin's test suite
(`plugins/hpv16/tests/test_hpv16_plugin.py`) — it will validate the file's length against
the manifest's declared `reference_genome_accession` expectation and fail clearly if
something doesn't match (wrong accession, truncated download, etc).

## Why this matters

Every mutation this plugin ever reports is only as trustworthy as this reference file. If
you substitute the wrong accession or a corrupted download, every downstream coordinate is
silently wrong. That's why `viralai.plugins.reference.load_reference_genome()` refuses to
proceed on a length mismatch rather than trying to be lenient about it.
