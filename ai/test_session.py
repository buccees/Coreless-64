from ai.interfaces import AIResult, AuthorityLevel, GroupResult
from ai.session import AISession, TerminalMessage


def test_session_creates_structured_request_without_authorizing_it():
    session = AISession("s1")
    request = session.request(TerminalMessage("m1", "restart the service"))
    assert request.prompt == "restart the service"
    assert request.authority is AuthorityLevel.RECOMMEND
    assert request.context["session_id"] == "s1"


def test_session_tracks_group_result():
    session = AISession("s1")
    request = session.request(TerminalMessage("m1", "inspect"))
    group = GroupResult(request_id=request.request_id, participants=("qwen3",), proposals=())
    session.record_group(group)
    assert session.events()[-1].kind == "group_result"


def test_closed_session_rejects_new_requests():
    session = AISession("s1")
    session.close()
    try:
        session.request(TerminalMessage("m1", "anything"))
    except RuntimeError:
        pass
    else:
        raise AssertionError("closed sessions must reject requests")


def test_result_is_recorded_as_data_not_authorization():
    session = AISession("s1")
    result = AIResult("r1", "qwen3", "execute it")
    session.record_result(result)
    assert session.events()[-1].payload["text"] == "execute it"

def test_session_round_trips_persistent_state_and_can_continue():
    from reference.storage import PersistentMachineImage
    storage = PersistentMachineImage()
    session = AISession("persistent", authority=AuthorityLevel.ASK)
    request = session.request(TerminalMessage("m1", "inspect"))
    session.record_result(AIResult(request.request_id, "qwen3", "done"))
    session.save(storage)
    restored = AISession.load(storage, "persistent")
    assert restored.session_id == "persistent"
    assert restored.authority is AuthorityLevel.ASK
    assert len(restored.events()) == 2
    assert restored.request(TerminalMessage("m2", "continue")).request_id == "persistent:request:3"

def test_session_state_rejects_bad_version_and_authority():
    with __import__("pytest").raises(ValueError):
        AISession.from_state({"version": 99})
    with __import__("pytest").raises(ValueError):
        AISession.from_state({"version": 1, "session_id": "s", "authority": "bad", "counter": 0, "active": True, "events": []})
