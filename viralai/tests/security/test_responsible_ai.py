import pytest
from pydantic import BaseModel, ValidationError

from viralai.security.responsible_ai import (
    AI_LIMITATIONS,
    RESEARCH_USE_DISCLOSURE,
    SIMULATION_LIMITATIONS,
    ResponsibleAIEnvelope,
    wrap_ai_result,
    wrap_simulation_result,
)


class _SamplePayload(BaseModel):
    value: int


def test_wrap_ai_result_includes_disclosure_and_ai_limitations():
    envelope = wrap_ai_result(_SamplePayload(value=42))

    assert envelope.result.value == 42
    assert envelope.disclosure == RESEARCH_USE_DISCLOSURE
    assert envelope.limitations == AI_LIMITATIONS


def test_wrap_simulation_result_includes_disclosure_and_simulation_limitations():
    envelope = wrap_simulation_result(_SamplePayload(value=7))

    assert envelope.result.value == 7
    assert envelope.disclosure == RESEARCH_USE_DISCLOSURE
    assert envelope.limitations == SIMULATION_LIMITATIONS


def test_envelope_cannot_be_constructed_without_limitations():
    with pytest.raises(ValidationError):
        ResponsibleAIEnvelope(result=_SamplePayload(value=1))  # missing required 'limitations'


def test_envelope_serializes_with_all_fields():
    envelope = wrap_ai_result(_SamplePayload(value=1))
    dumped = envelope.model_dump()

    assert set(dumped.keys()) == {"result", "disclosure", "limitations"}
