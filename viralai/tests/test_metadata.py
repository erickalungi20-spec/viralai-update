from viralai.core.idm import Mutation, MutationType
from viralai.core.metadata import attach_metadata, metadata_summary


def _sample_mutation() -> Mutation:
    return Mutation(
        position=1, reference_base="A", observed_base="G", mutation_type=MutationType.SUBSTITUTION
    )


def test_attach_metadata_generates_uuid_and_timestamp():
    tracked = attach_metadata(_sample_mutation(), created_by="mutation_engine")
    assert tracked.metadata.uuid
    assert tracked.metadata.created_by == "mutation_engine"
    assert tracked.metadata.created_at is not None


def test_attach_metadata_two_objects_get_different_uuids():
    t1 = attach_metadata(_sample_mutation())
    t2 = attach_metadata(_sample_mutation())
    assert t1.metadata.uuid != t2.metadata.uuid


def test_attach_metadata_carries_plugin_and_workflow_info():
    tracked = attach_metadata(
        _sample_mutation(),
        created_by="mutation_engine",
        plugin_name="hpv-plugin",
        plugin_version="1.0.0",
        workflow_version="0.1.0",
        evidence_level="IV",
        confidence_score=0.87,
    )
    assert tracked.metadata.plugin_name == "hpv-plugin"
    assert tracked.metadata.plugin_version == "1.0.0"
    assert tracked.metadata.confidence_score == 0.87


def test_metadata_summary_is_report_ready():
    tracked = attach_metadata(
        _sample_mutation(),
        created_by="mutation_engine",
        plugin_name="hpv-plugin",
        plugin_version="1.0.0",
    )
    summary = metadata_summary(tracked)
    assert summary["created_by"] == "mutation_engine"
    assert summary["plugin"] == "hpv-plugin@1.0.0"
    assert "id" in summary and "created" in summary


def test_payload_is_untouched_by_metadata_wrapping():
    mutation = _sample_mutation()
    tracked = attach_metadata(mutation)
    assert tracked.payload.position == mutation.position
    assert tracked.payload.reference_base == mutation.reference_base
