import pytest

from vigil.multiplayer import BattleshipRooms, MultiplayerError


FLEET = [
    [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]],
    [[1, 0], [1, 1], [1, 2], [1, 3]],
    [[2, 0], [2, 1], [2, 2]],
    [[3, 0], [3, 1], [3, 2]],
    [[4, 0], [4, 1]],
]


def test_room_requires_second_player_before_turns_begin():
    rooms = BattleshipRooms()
    first = rooms.create_room(FLEET)
    view = rooms.view(first["player_token"])
    assert view["player"] == 1
    assert view["ready"] is False
    assert view["player_count"] == 1
    with pytest.raises(MultiplayerError, match="second player"):
        rooms.fire(first["player_token"], 0, 0)


def test_players_get_isolated_views_and_turns_are_server_authoritative():
    rooms = BattleshipRooms()
    first = rooms.create_room(FLEET)
    second = rooms.join_room(first["room_code"].lower(), FLEET)

    view1 = rooms.view(first["player_token"])
    view2 = rooms.view(second["player_token"])
    assert view1["ready"] and view2["ready"]
    assert view1["player"] == 1 and view2["player"] == 2
    assert view1["own_fleet"] == view2["own_fleet"]
    assert "opponent_fleet" not in view1 and "opponent_fleet" not in view2
    assert "player_token" not in view1 and "player_token" not in view2

    with pytest.raises(MultiplayerError, match="not your turn"):
        rooms.fire(second["player_token"], 9, 9)

    after_shot = rooms.fire(first["player_token"], 0, 0)
    assert after_shot["outgoing_shots"] == [{"row": 0, "column": 0, "hit": True}]
    opponent_view = rooms.view(second["player_token"])
    assert opponent_view["incoming_shots"] == [{"row": 0, "column": 0}]
    assert "hit" not in opponent_view["incoming_shots"][0]
    assert opponent_view["turn"] == 2

    after_miss = rooms.fire(second["player_token"], 9, 9)
    assert after_miss["outgoing_shots"] == [{"row": 9, "column": 9, "hit": False}]
    assert after_miss["turn"] == 1
    with pytest.raises(MultiplayerError, match="already been targeted"):
        rooms.fire(first["player_token"], 0, 0)


def test_room_rejects_invalid_fleets_and_unknown_sessions():
    rooms = BattleshipRooms()
    with pytest.raises(MultiplayerError, match="five ships"):
        rooms.create_room(FLEET[:4])
    overlapping = [ship[:] for ship in FLEET]
    overlapping[1][0] = [0, 0]
    with pytest.raises(MultiplayerError, match="overlap"):
        rooms.create_room(overlapping)
    with pytest.raises(MultiplayerError, match="not found"):
        rooms.view("not-a-valid-session")


def test_room_only_allows_one_opponent_and_expires_sessions():
    rooms = BattleshipRooms(ttl_seconds=60)
    first = rooms.create_room(FLEET)
    rooms.join_room(first["room_code"], FLEET)
    with pytest.raises(MultiplayerError, match="already has two players"):
        rooms.join_room(first["room_code"], FLEET)

    expired = BattleshipRooms(ttl_seconds=1)
    created = expired.create_room(FLEET)
    expired._rooms[created["room_code"]].created_at -= 2
    with pytest.raises(MultiplayerError, match="expired"):
        expired.view(created["player_token"])
