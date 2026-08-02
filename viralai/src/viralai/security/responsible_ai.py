"""
Responsible AI Framework (Blueprint Ch.36).

Phase 4's ScientificReasoningEngine already generates research-use-only recommendation
text (see ai/reasoning.py's fixed-template `_build_recommendation`), and Phase 6's report
exporters unconditionally append a disclaimer. This module closes the remaining gap:
mechanically wrapping AI and simulation API *responses* so a disclosure is structurally
present in the payload itself, not just in accompanying prose that a client could ignore
or a future code change could accidentally drop.

`ResponsibleAIEnvelope` is a generic wrapper -- any AI or simulation response gets
wrapped in one before leaving the API boundary, so the disclosure travels with the data
no matter what shape the data itself takes.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

RESEARCH_USE_DISCLOSURE = (
    "This output is a research-use computational result. It is not a clinical or "
    "diagnostic finding and has not been validated for clinical decision-making."
)

AI_LIMITATIONS = (
    "AI predictions reflect patterns in the model's training data and may not "
    "generalize to sequences, populations, or conditions outside that training "
    "distribution. Confidence scores indicate model certainty, not biological or "
    "clinical validity."
)

SIMULATION_LIMITATIONS = (
    "Simulated data is synthetic and does not represent observed biological evidence. "
    "It reflects the assumptions of the simulation model (see Blueprint Ch.13.6), not "
    "empirical measurement."
)


class ResponsibleAIEnvelope(BaseModel, Generic[T]):
    """Wraps any AI or simulation response payload with a mandatory, structural
    disclosure. A client parsing this response cannot get the `result` field without
    the `disclosure`/`limitations` fields being present alongside it in the same object
    -- there is no code path that produces just the bare result.
    """

    result: T
    disclosure: str = RESEARCH_USE_DISCLOSURE
    limitations: str


def wrap_ai_result(result: T) -> ResponsibleAIEnvelope[T]:
    return ResponsibleAIEnvelope(result=result, limitations=AI_LIMITATIONS)


def wrap_simulation_result(result: T) -> ResponsibleAIEnvelope[T]:
    return ResponsibleAIEnvelope(result=result, limitations=SIMULATION_LIMITATIONS)
