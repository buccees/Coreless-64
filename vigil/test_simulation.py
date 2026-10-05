from vigil.provenance import EventProvenance
from vigil.simulation import ReplayEvent, ReplayLog


def _event(event_id, sequence=1):
    provenance = EventProvenance(
        source_type="camera",
        source_ids=("cam-1",),
        source_sequences=(sequence,),
        timestamp_ns=100,
        confidence=0.9,
    )
    return ReplayEvent(event_id, 100, "camera.frame", object(), provenance)


def test_replay_validation_accepts_identical_event_chain():
    original = ReplayLog((_event("one"), _event("two", 2)))
    replayed = original.replay()
    result = original.validate_replay(replayed)
    assert result.valid
    assert result.event_count == 2
    assert result.mismatches == ()


def test_replay_validation_detects_provenance_change():
    original = ReplayLog((_event("one"),))
    replayed = (_event("one", 9),)
    result = original.validate_replay(replayed)
    assert not result.valid
    assert "event[0] one" in result.mismatches[0]


def test_replay_validation_detects_missing_and_extra_events():
    original = ReplayLog((_event("one"), _event("two", 2)))
    missing = original.validate_replay((_event("one"),))
    extra = original.validate_replay((_event("one"), _event("two", 2), _event("three", 3)))
    assert not missing.valid
    assert not extra.valid


def test_replay_chain_digest_is_deterministic():
    first = ReplayLog((_event("one"), _event("two", 2)))
    second = ReplayLog((_event("one"), _event("two", 2)))
    assert first.chain_digest() == second.chain_digest()


def test_replay_chain_digest_changes_with_provenance():
    first = ReplayLog((_event("one"),))
    changed = ReplayLog((_event("one", 9),))
    assert first.chain_digest() != changed.chain_digest()


def test_replay_integrity_record_round_trips():
    log = ReplayLog((_event("one"), _event("two", 2)))
    record = log.integrity_record()
    assert log.verify_integrity(record).valid


def test_replay_integrity_detects_tampering():
    log = ReplayLog((_event("one"),))
    record = log.integrity_record()
    tampered = dict(record)
    tampered["chain_digest"] = "tampered"
    result = log.verify_integrity(tampered)
    assert not result.valid
    assert "integrity.chain_digest" in result.mismatches[0]


def test_replay_integrity_rejects_unknown_format_version():
    log = ReplayLog((_event("one"),))
    record = log.integrity_record()
    record["version"] = 2
    result = log.verify_integrity(record)
    assert not result.valid
    assert "integrity.version" in result.mismatches[0]


def test_replay_integrity_rejects_unknown_algorithm():
    log = ReplayLog((_event("one"),))
    record = log.integrity_record()
    record["algorithm"] = "md5"
    result = log.verify_integrity(record)
    assert not result.valid
    assert "integrity.algorithm" in result.mismatches[0]
