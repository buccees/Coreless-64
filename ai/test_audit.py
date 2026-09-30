from ai.audit import AuditLog


def test_audit_records_are_append_only():
    audit = AuditLog()
    record = audit.record(
        "e1", event="proposal", actor="qwen3",
        operation="schedule", outcome="pending",
        details={"cpu": 1},
    )
    assert audit.records() == (record,)


def test_audit_rejects_duplicate_event_ids():
    audit = AuditLog()
    audit.record("e1", event="proposal", actor="qwen3", operation="x", outcome="pending")
    try:
        audit.record("e1", event="proposal", actor="qwen3", operation="x", outcome="pending")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate audit IDs must be rejected")
