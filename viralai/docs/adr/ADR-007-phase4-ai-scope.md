# ADR-007: Phase 4 AI scope -- Random Forest baseline, real SHAP, file-backed registry

## Status
Accepted

## Context
Blueprint Ch.26 and the Commercial Development Workflow's Phase 4 call for an ML Module,
a Deep Learning Module, an Explainable AI Module, a Model Registry, an AI Training
Pipeline Manager, and a Scientific Reasoning Engine querying the Research Graph.

## Decisions

1. **Random Forest first, no deep learning yet.** The blueprint itself (Ch.26.5-26.6)
   specifies classical ML as the initial release target and deep learning as a later
   addition once larger datasets exist. Phase 4 follows that ordering literally: a neural
   network trained on a handful of hand-labeled examples would be overfit and would not
   actually demonstrate anything a Random Forest doesn't already show correctly.

2. **Real SHAP, not a feature_importances_ substitute.** `shap.TreeExplainer` was
   installed and used for genuine per-prediction attribution (Ch.26.7's "every AI
   prediction shall include... feature importance" is a per-prediction requirement, not
   a global one). The installed shap version returns a `(n_samples, n_features, 2)` array
   for binary RandomForestClassifier explanations; `explainability.py` asserts this shape
   explicitly rather than assuming it, so a future shap/sklearn upgrade that changes this
   convention fails loudly instead of silently explaining the wrong class.

3. **File-backed Model Registry, not a database.** Same pragmatic pattern as the
   Knowledge Base (ADR from Phase 3) and Event Bus/Scheduler (ADR-004): one directory per
   (name, version) containing a joblib-serialized model and a JSON metadata record. Real,
   tested, zero external database dependency.

4. **Training Pipeline Manager covers Dataset through Registration, not Deployment or
   Monitoring.** The engineering review's proposed pipeline is Dataset -> Feature
   Engineering -> Training -> Validation -> Explainability -> Benchmark -> Registration ->
   Deployment -> Monitoring. Deployment and Monitoring require a running service to
   deploy to and monitor -- that's Phase 11/12 infrastructure. Implementing them now would
   mean building against infrastructure that doesn't exist yet, the same mistake ADR-004
   already reasoned through for the Event Bus.

5. **Scientific Reasoning Engine output is template-constrained, not free-text
   generation.** `_build_recommendation` in reasoning.py assembles its output from a fixed
   set of clauses rather than generating free text, specifically so the "research use
   only, not a clinical or diagnostic finding" framing (Ch.36) cannot be accidentally
   dropped by a future prompt/model change. This is an explicit enforcement mechanism, not
   just a documented policy.

## Consequences
- **Positive:** every claim this phase makes (Random Forest baseline, real per-prediction
  SHAP, file-backed registry) is fully implemented and tested, not partially stubbed.
- **Positive:** the ethics constraint on the Reasoning Engine's output is mechanically
  enforced, closing a gap where "we documented the policy" and "the code can't violate the
  policy" are different levels of assurance.
- **Negative:** no deep learning module exists yet -- Ch.26.6's CNN/RNN/Transformer/GNN
  scaffolding remains a documented future addition, not present code.
- **Negative:** "Benchmark" in the pipeline sequence is represented only by the
  training/validation metrics computed inline; the formal Benchmark Repository (Phase 10)
  with curated cross-plugin datasets does not exist yet, so these metrics should not be
  treated as the rigorous benchmark comparison Phase 10 will eventually provide.

## Trigger for revisiting
- Deep learning: once a real dataset (hundreds to thousands of labeled mutations, not a
  handful of hand-built test fixtures) exists to train on without overfitting.
- Registry backend: once multi-user/concurrent model registration is needed (same trigger
  class as ADR-004 and Phase 3's Knowledge Base ADR).
- Deployment/Monitoring pipeline stages: once Phase 11 stands up an actual serving
  environment to deploy models into.
