# ViralAI Plugin Development Standard

Every plugin — official, community, or experimental — must follow this standard. It exists
so that a plugin someone else wrote is exactly as trustworthy and predictable to load as
one you wrote yourself.

## 1. Directory structure

```
plugins/<plugin-name>/
    manifest.json          # required — see §2
    __init__.py            # required — must define a top-level `Plugin` class
    data/
        gene_annotations.json
        protein_annotations.json
        reference/
            README.md       # how to obtain the real reference FASTA (never commit real
                             # sequence data directly unless license/size make that
                             # appropriate — default to fetch-on-demand)
    tests/
        test_<plugin-name>.py
```

## 2. Manifest (`manifest.json`)

Must deserialize into `viralai.plugins.manifest.PluginManifest`. Required fields:

- `name`, `version` — plugin identity
- `supported_viruses` — at least one
- `compatible_core_engine_versions` — a version specifier (`">=0.1.0"`, `"==0.1.0"`, or `"*"`)
- `authors`, `license`
- `reference_genome_accession` and `reference_genome_citations` — **required before a
  plugin can be promoted above `experimental`**. No gene coordinate, protein domain, or
  reference sequence ships without a traceable source. If you can't cite it, don't include
  it — mark it as a TODO in the plugin's README instead of guessing.

## 3. The `Plugin` class

`__init__.py` must define a class literally named `Plugin` that:
- subclasses `viralai.plugins.base.VirusPlugin`
- accepts `(manifest: PluginManifest, plugin_dir: Path)` in `__init__`
- implements `get_reference_genome()`, `get_gene_annotations()`, `get_protein_annotations()`

Plugins supply **data**, not logic that reaches into engine internals (Blueprint Ch.5.10).
If you find yourself wanting a plugin to call back into the Mutation Engine or modify
Core Engine state, that's a sign the capability belongs in the engine, not the plugin.

## 4. Reference genome handling

Real reference sequences are **not committed to source control** by default policy —
`data/reference/README.md` documents the accession number and how to fetch it (typically
via NCBI E-utilities or manual download from GenBank/RefSeq). `viralai.plugins.reference`
validates whatever the developer places locally against the manifest's declared accession,
expected length, and (once pinned) checksum. A missing file fails loudly with instructions,
never silently substitutes placeholder data.

Exception: small, clearly-synthetic fixtures used only by the plugin's own test suite are
fine to commit, as long as they are unmistakably labeled as synthetic (e.g. a docstring
saying "SYNTHETIC TEST FIXTURE — not a real biological sequence") so nobody mistakes them
for real reference data later.

## 5. Certification tiers

| Tier | Requirements |
|---|---|
| `experimental` | Manifest validates, `Plugin.validate()` passes, no citations required yet |
| `community` | All of the above, plus: reference genome citations present, automated test suite passes, reference sequence checksum pinned in the manifest |
| `official` | All of the above, plus: scientific review by the (eventual) AI/Scientific Review Committee, benchmark dataset comparison recorded in the Benchmark Repository |

A plugin's `certification_tier` field in its manifest is a claim, not a proof — the Sci-CI
pipeline (Phase 10) is what actually enforces these requirements before a tier bump is
accepted into `main`.

## 6. Testing

Minimum bar for any plugin, regardless of tier:
- `Plugin.validate()` returns no problems against real (or clearly-synthetic, for CI)
  reference data
- Every declared gene annotation coordinate is covered by at least one test asserting it
  falls within the reference genome's length
- If the plugin's data includes any published mutation examples, at least one test should
  assert the plugin's own annotations agree with them
