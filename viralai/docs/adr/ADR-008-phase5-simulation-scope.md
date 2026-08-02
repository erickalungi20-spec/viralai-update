# ADR-008: Phase 5 simulation model choices and scope

## Status
Accepted

## Context
Blueprint Ch.13 and Ch.27 specify a Simulation Laboratory with Mutation, Evolution,
Selection, and Population simulators, plus a "future" Environmental Simulator, wrapped by
a Digital Laboratory Manager (engineering review Recommendation 6) for experiment
tracking. Per project direction, "future" components are built now rather than deferred.

## Decisions

1. **Jukes-Cantor mutation model.** The simplest standard nucleotide substitution model
   (Jukes & Cantor, 1969): uniform per-site mutation rate, equally likely to become any of
   the other three bases. This is foundational population-genetics methodology, not a
   virus-specific empirical claim, so it needs no per-use citation the way a plugin's gene
   coordinates do -- same reasoning as Phase 2's standard genetic code table. More
   realistic models (transition/transversion bias -- Kimura 1980; among-site rate
   variation) are a documented future extension, not implemented.

2. **Wright-Fisher selection.** Standard population-genetics reproduction model (Fisher
   1930, Wright 1931): next generation sampled with replacement, weighted by fitness.
   Fitness == 1.0 for everyone (the default) reduces to pure genetic drift.

3. **Environmental Simulator built now, not deferred.** A simple multiplicative
   per-position fitness model (`EnvironmentalPressure`) -- no epistasis, no interaction
   between positions. Adequate for illustrating a selective sweep at known resistance
   positions; not a claim of mechanistic accuracy for any specific real mutation's fitness
   effect. Real-world position_effects values should be sourced from cited literature, the
   same discipline as Phase 1 plugin gene coordinates.

4. **Population-level summary statistics, not full lineage/genealogy tracking.** Each
   generation records nucleotide diversity and mean mutation count from a sample, not a
   full ancestry tree of which individual descended from which. Genuine phylogenetic
   lineage tracking is a real, separate feature.

5. **numpy-vectorized, not GPU-accelerated.** Population and genome-length arrays are
   numpy uint8 arrays; mutation and fitness calculations are vectorized. This is fast
   enough for gene-length sequences and populations in the hundreds-to-low-thousands over
   tens to low-hundreds of generations. Whole-genome-scale (thousands of bp), large
   population (10,000+), many-generation (1000+) simulations would need either further
   optimization or a compiled/GPU backend -- not implemented here.

6. **File-backed Digital Laboratory Manager, same pattern as Phase 4's ModelRegistry.**
   One directory per (experiment name, version), JSON metadata, no external database.
   Same pragmatic reasoning as every prior ADR in this series (0004, Knowledge Base,
   0007): real, tested, zero infrastructure, with a documented trigger for graduating to
   a database-backed version.

7. **Every simulation output is marked `is_synthetic=True`, unconditionally.** Ch.13.6
   requires simulated data to never be presented as real biological observation. This is
   a field on `SimulationResult`/`SimulationExperiment` that is always `True` and is
   never a caller-settable parameter -- there is no way to construct a simulation result
   that doesn't carry this flag.

## Consequences
- **Positive:** reproducibility is directly checkable, not just claimed -- the
  `DigitalLaboratoryManager.replay()` method re-runs a stored experiment's exact seed and
  parameters, and a test asserts the replay produces identical generation summaries to the
  original.
- **Positive:** the Environmental Simulator (originally a "future" component) is fully
  implemented and tested, closing that gap immediately rather than leaving it as a roadmap
  item.
- **Negative:** no lineage/genealogy tracking -- a researcher cannot ask "show me the
  ancestry of this specific mutated individual" from the current data model.
- **Negative:** simple multiplicative fitness model can't represent epistatic
  interactions between positions (where the fitness effect of one mutation depends on the
  presence of another) -- a real and well-documented phenomenon in viral evolution that
  this model cannot express.

## Trigger for revisiting
- Lineage tracking: the first time a research question specifically needs ancestry
  information, not just population-level summary statistics.
- Epistasis: the first time a real research use case (e.g. compensatory mutation
  pathways in drug resistance) needs interacting fitness effects, not independent ones.
- Performance: the first time simulation parameters exceed the numpy-vectorized scale
  this implementation handles comfortably (see Decision 5's stated bounds).
