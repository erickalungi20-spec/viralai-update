from viralai.security.audit import AuditLogger


def test_record_and_read_all(tmp_path):
    logger = AuditLogger(tmp_path / "audit.jsonl")

    logger.record(actor="alice", action="knowledge.add_mutation", resource="HPV16/E6/118")

    entries = logger.read_all()
    assert len(entries) == 1
    assert entries[0].actor == "alice"
    assert entries[0].action == "knowledge.add_mutation"
    assert entries[0].outcome == "success"


def test_read_all_empty_when_no_entries(tmp_path):
    logger = AuditLogger(tmp_path / "audit.jsonl")
    assert logger.read_all() == []


def test_entries_persist_and_accumulate(tmp_path):
    logger = AuditLogger(tmp_path / "audit.jsonl")

    logger.record(actor="alice", action="action-1", resource="resource-1")
    logger.record(actor="bob", action="action-2", resource="resource-2")

    entries = logger.read_all()
    assert len(entries) == 2


def test_read_for_actor_filters(tmp_path):
    logger = AuditLogger(tmp_path / "audit.jsonl")
    logger.record(actor="alice", action="action-1", resource="r1")
    logger.record(actor="bob", action="action-2", resource="r2")
    logger.record(actor="alice", action="action-3", resource="r3")

    alice_entries = logger.read_for_actor("alice")

    assert len(alice_entries) == 2
    assert all(e.actor == "alice" for e in alice_entries)


def test_record_with_error_outcome_and_details(tmp_path):
    logger = AuditLogger(tmp_path / "audit.jsonl")

    logger.record(
        actor="alice",
        action="simulation.run",
        resource="exp-1",
        outcome="error",
        details={"reason": "timeout"},
    )

    entry = logger.read_all()[0]
    assert entry.outcome == "error"
    assert entry.details == {"reason": "timeout"}


def test_entries_survive_across_logger_instances(tmp_path):
    path = tmp_path / "audit.jsonl"
    AuditLogger(path).record(actor="alice", action="action-1", resource="r1")

    reloaded = AuditLogger(path)
    assert len(reloaded.read_all()) == 1
