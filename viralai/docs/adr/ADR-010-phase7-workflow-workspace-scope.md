# ADR-010: Phase 7 workflow templates as shared compositions, and checkpoint scope

## Status
Accepted

## Context
Blueprint Ch.17.4 lists six named workflow templates (Mutation Analysis, Evolutionary
Analysis, Cancer Research, HIV Research, Pandemic Surveillance, Simulation). Ch.17.6
requires error recovery: checkpointing, retries, and partial workflow recovery. Ch.20
specifies a Research Workspace organizing projects as persistent units.

## Decisions

1. **Workflow templates are built from shared step factories, not six independent
   pipelines.** Cancer Research and HIV Research, in particular, are described in Ch.9.4
   and Ch.10.4 as compositions of the Mutation Engine, Protein Engine, Knowledge Base, and
   Reporting Engine -- not as separately-implemented analytical logic. `templates.py`
   reflects that directly: `cancer_research_workflow` and `hiv_research_workflow` are
   `mutation_analysis_workflow`/`evolutionary_analysis_workflow` plus a knowledge lookup
   step. This is a faithful implementation of what the blueprint describes, not a
   shortcut disguised as one.

2. **WorkflowRunner is built on top of CoreEngine, not a modification of it.** Phase 0's
   `CoreEngine.run_workflow` stays exactly as it was (tested, stable). `WorkflowRunner`
   composes a `CoreEngine` and adds checkpointing + retry as a separate layer. This
   follows the same "new capability on top, not surgery underneath" pattern used
   throughout this project.

3. **Checkpointed state is restricted to `ctx.analysis.results`, which must be
   JSON-serializable.** This is what makes "save it, reload it, keep going" actually
   reliable. A step that writes a non-JSON-safe object into results gets a clear
   `ValidationError` at checkpoint-save time, not a mysterious pickle failure later.

4. **Resumed workflow provenance is not stitched across attempts.** If a workflow fails
   at step 3 and is resumed, the resumed run's `ProvenanceRecord` only covers steps 3
   onward from the resume point -- it does not merge in the original attempt's
   before/after step records for steps 0-2. Full cross-attempt provenance stitching
   (showing "this workflow took 2 attempts, here's the complete history of both") is a
   real, separate feature, not implemented here.

5. **Research Workspace does not enforce strict project-status transitions.** Real
   research is not linear -- a researcher moving from `ANALYSIS_RUNNING` back to
   `WORKFLOW_DESIGNED` to redesign an approach is normal, not an error. The workspace
   records every status change in `status_history.jsonl` regardless of direction, rather
   than implementing a state machine that would reject legitimate non-linear research
   process.

## Consequences
- **Positive:** all six workflow templates are genuinely implemented and tested against
  the real Phase 2-5 engines, not stubbed.
- **Positive:** checkpointing and retry are real, tested behaviors -- a test simulates a
  step failing on its first attempt and succeeding on retry, and another test verifies a
  resumed workflow does not re-execute already-completed steps.
- **Negative:** a researcher inspecting a resumed workflow's provenance record will only
  see the resumed portion, not the full multi-attempt history -- they'd need to check the
  original failed run's logs separately for that.
- **Negative:** the Research Workspace's lenient status tracking means it cannot catch a
  genuinely invalid transition (e.g. `CREATED` -> `PUBLICATION` with nothing in between)
  as an error -- it will simply record it.

## Trigger for revisiting
- Cross-attempt provenance stitching: the first time a real audit or publication
  requirement needs the complete history of a multi-attempt workflow, not just its final
  successful run.
- Status transition enforcement: if project status data starts being used for automated
  reporting/compliance purposes where invalid transitions need to be actively rejected,
  not just recorded.
