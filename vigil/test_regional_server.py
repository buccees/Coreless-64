import json

import pytest

from vigil.regional_server import RegionalTickRunner, load_game_config


def write_config(tmp_path, payload):
    path = tmp_path / "game.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def sample_config():
    return {
        "schema_version": 1,
        "world_bounds": [0, 0, 100, 100],
        "ships": [
            {
                "ship_id": "blue", "name": "Blue Ship", "ship_class": "destroyer",
                "x": 10, "y": 20, "speed": 0.5, "max_speed": 0.75, "heading_deg": 90,
                "length_m": 155, "beam_m": 20,
                "blueprint_source": "cited-plan-source",
            },
            {
                "ship_id": "red", "name": "Red Ship", "ship_class": "frigate",
                "x": 80, "y": 70, "speed": 0.25,
            },
        ],
        "players": [
            {
                "player_id": "host", "token_env": "VIGIL_TEST_HOST_TOKEN",
                "controlled_ship_ids": ["blue"], "visible_ship_ids": ["blue"],
            },
            {
                "player_id": "opponent", "token_env": "VIGIL_TEST_OPPONENT_TOKEN",
                "controlled_ship_ids": ["red"], "visible_ship_ids": ["red"],
            },
        ],
    }


def test_load_game_config_creates_authoritative_world_and_player_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIL_TEST_HOST_TOKEN", "host-secret")
    monkeypatch.setenv("VIGIL_TEST_OPPONENT_TOKEN", "opponent-secret")
    game = load_game_config(write_config(tmp_path, sample_config()))
    assert game.world.ships["blue"].aspect_ratio == 7.75
    assert game.world.ships["blue"].heading_deg == 90
    assert game.world.ships["blue"].max_speed == pytest.approx(0.75)
    assert [ship["ship_id"] for ship in game.snapshot("host-secret")["ships"]] == ["blue"]
    assert [ship["ship_id"] for ship in game.snapshot("opponent-secret")["ships"]] == ["red"]


def test_config_requires_supported_schema_and_environment_tokens(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="schema_version"):
        load_game_config(write_config(tmp_path, {"schema_version": 99}))
    monkeypatch.delenv("VIGIL_TEST_HOST_TOKEN", raising=False)
    monkeypatch.setenv("VIGIL_TEST_OPPONENT_TOKEN", "opponent-secret")
    with pytest.raises(ValueError, match="environment variable is missing"):
        load_game_config(write_config(tmp_path, sample_config()))


def test_config_rejects_partial_blueprint_dimensions_and_unknown_classes(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGIL_TEST_HOST_TOKEN", "host-secret")
    monkeypatch.setenv("VIGIL_TEST_OPPONENT_TOKEN", "opponent-secret")
    config = sample_config()
    config["ships"][0].pop("blueprint_source")
    with pytest.raises(ValueError, match="must be supplied together"):
        load_game_config(write_config(tmp_path, config))
    config = sample_config()
    config["ships"][0]["ship_class"] = "super-ship"
    with pytest.raises(ValueError, match="supported ship_class"):
        load_game_config(write_config(tmp_path, config))


def test_tick_runner_advances_authoritative_world():
    from vigil.regional_game import RegionalGame
    from vigil.regional_world import RegionalShip, RegionalWorld

    world = RegionalWorld([
        RegionalShip.from_class(
            ship_id="blue", name="Blue", ship_class="destroyer",
            x=0, y=0, speed=0.1,
        )
    ])
    game = RegionalGame(world)
    runner = RegionalTickRunner(game, tick_rate=20)
    runner.start()
    try:
        import time
        deadline = time.monotonic() + 1
        while game.simulation_tick == 0 and time.monotonic() < deadline:
            time.sleep(0.005)
    finally:
        runner.stop()
    assert game.simulation_tick >= 1
    assert world.ships["blue"].y > 0
    assert runner.last_error is None
    with pytest.raises(ValueError, match="between 0.1 and 60"):
        RegionalTickRunner(game, tick_rate=100)


def test_ship_faction_id_survives_config_and_authorized_snapshot(tmp_path):
    config = {
        "schema_version": 1,
        "ships": [
            {"ship_id": "blue", "name": "Blue Ship", "ship_class": "destroyer",
             "faction_id": "maritime-coalition", "x": 0.2, "y": 0.3, "speed": 0.01},
            {"ship_id": "red", "name": "Red Ship", "ship_class": "frigate",
             "faction_id": "extraction-directorate", "x": 0.7, "y": 0.8, "speed": 0.01},
        ],
        "players": [
            {"player_id": "host", "token_env": "VIGIL_TEST_HOST_TOKEN",
             "controlled_ship_ids": ["blue"], "visible_ship_ids": ["blue"]},
        ],
    }
    import os
    os.environ["VIGIL_TEST_HOST_TOKEN"] = "test-faction-token"
    try:
        game = load_game_config(write_config(tmp_path, config))
        snapshot = game.snapshot("test-faction-token")
    finally:
        os.environ.pop("VIGIL_TEST_HOST_TOKEN", None)
    assert [ship["faction_id"] for ship in snapshot["ships"]] == ["maritime-coalition"]
    assert "red" not in [ship["ship_id"] for ship in snapshot["ships"]]


def test_ai_player_gets_private_token_and_can_be_scheduled(tmp_path):
    config = {
        "schema_version": 1,
        "ships": [
            {"ship_id": "red", "name": "Red Ship", "ship_class": "frigate",
             "x": 0.2, "y": 0.3, "speed": 0.01},
        ],
        "players": [
            {"player_id": "computer", "ai": True, "controlled_ship_ids": ["red"],
             "visible_ship_ids": ["red"]},
        ],
    }
    ai_tokens = {}
    game = load_game_config(write_config(tmp_path, config), ai_tokens=ai_tokens)
    assert set(ai_tokens) == {"computer"}
    token = ai_tokens["computer"]
    assert len(token) >= 32
    assert game.snapshot(token)["player_id"] == "computer"

    from vigil.regional_ai import RegionalOpponent, RegionalOpponentRunner
    runner = RegionalOpponentRunner(
        game, {token: RegionalOpponent()}, decision_interval_seconds=0.1
    )
    runner.start()
    try:
        import time
        deadline = time.monotonic() + 1
        while not runner.last_results and time.monotonic() < deadline:
            time.sleep(0.005)
    finally:
        runner.stop()
    assert runner.last_results[token]["reason"] == "no_visible_contact"
