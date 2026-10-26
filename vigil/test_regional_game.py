import pytest

from vigil.regional_game import RegionalGame, RegionalGameError
from vigil.regional_world import RegionalShip, RegionalWorld


def make_game():
    world = RegionalWorld([
        RegionalShip.from_class(
            ship_id="blue", name="Blue Ship", ship_class="destroyer",
            x=0.2, y=0.3, speed=0.01,
        ),
        RegionalShip.from_class(
            ship_id="red", name="Red Ship", ship_class="frigate",
            x=0.8, y=0.7, speed=0.01,
        ),
    ])
    game = RegionalGame(world)
    game.register_player(
        player_id="host", token="host-secret", controlled_ship_ids={"blue"},
        visible_ship_ids={"blue"},
    )
    game.register_player(
        player_id="opponent", token="opponent-secret", controlled_ship_ids={"red"},
        visible_ship_ids={"red"},
    )
    return game


def test_player_snapshot_only_contains_authorized_observations():
    game = make_game()
    host_view = game.snapshot("host-secret")
    opponent_view = game.snapshot("opponent-secret")
    assert [ship["ship_id"] for ship in host_view["ships"]] == ["blue"]
    assert [ship["ship_id"] for ship in opponent_view["ships"]] == ["red"]
    assert "Red Ship" not in repr(host_view)
    assert "Blue Ship" not in repr(opponent_view)
    assert host_view["controlled_ship_ids"] == ["blue"]
    assert host_view["simulation_tick"] == 0


def test_command_path_enforces_ownership_and_validates_heading():
    game = make_game()
    result = game.command(
        "host-secret", "set_heading", {"ship_id": "blue", "heading_deg": 90}
    )
    assert result["ok"] is True
    assert game.world.ships["blue"].heading_deg == 90
    with pytest.raises(RegionalGameError, match="does not control"):
        game.command(
            "host-secret", "set_heading", {"ship_id": "red", "heading_deg": 90}
        )
    for invalid in (-1, 360, float("inf"), True, "east"):
        with pytest.raises(RegionalGameError, match="heading_deg"):
            game.command(
                "host-secret", "set_heading",
                {"ship_id": "blue", "heading_deg": invalid},
            )


def test_campaign_move_uses_existing_world_movement_allowance():
    game = make_game()
    moved = game.command(
        "host-secret", "campaign_move", {"ship_id": "blue", "x": 0.205, "y": 0.3}
    )
    assert moved["position"] == pytest.approx([0.205, 0.3])
    with pytest.raises(ValueError, match="remaining movement"):
        game.command(
            "host-secret", "campaign_move", {"ship_id": "blue", "x": 0.3, "y": 0.3}
        )


def test_realtime_tick_advances_shared_world_and_sequence():
    game = make_game()
    result = game.advance_tick(2)
    assert result["simulation_tick"] == 1
    assert result["moved_ship_ids"] == ["blue", "red"]
    assert game.world.ships["blue"].x == pytest.approx(0.2)
    assert game.world.ships["blue"].y == pytest.approx(0.32)
    assert game.snapshot("host-secret")["simulation_tick"] == 1


def test_invalid_tokens_sessions_and_commands_are_rejected():
    game = make_game()
    with pytest.raises(RegionalGameError, match="unauthorized"):
        game.snapshot("wrong-token")
    with pytest.raises(RegionalGameError, match="already registered"):
        game.register_player(
            player_id="another", token="host-secret", controlled_ship_ids={"blue"}
        )
    with pytest.raises(RegionalGameError, match="unsupported command"):
        game.command("host-secret", "apply_hit", {"ship_id": "red", "damage": 10})
    with pytest.raises(RegionalGameError, match="only the host"):
        game.command("opponent-secret", "end_campaign_turn", {})
    assert game.world.ships["red"].hull == game.world.ships["red"].max_hull


def test_player_cannot_register_visibility_for_unknown_ships():
    game = RegionalGame(RegionalWorld([
        RegionalShip.from_class(
            ship_id="blue", name="Blue Ship", ship_class="destroyer",
            x=0.2, y=0.3, speed=0.01,
        )
    ]))
    with pytest.raises(RegionalGameError, match="unknown ship"):
        game.register_player(
            player_id="host", token="secret", controlled_ship_ids={"blue"},
            visible_ship_ids={"blue", "hidden"},
        )


def test_weapon_command_requires_visible_in_range_target_and_applies_hull_damage():
    world = RegionalWorld([
        RegionalShip.from_class(
            ship_id="blue", name="Blue Ship", ship_class="destroyer",
            x=0.2, y=0.3, speed=0.01, weapon_damage=2, weapon_range=0.2,
        ),
        RegionalShip.from_class(
            ship_id="red", name="Red Ship", ship_class="frigate",
            x=0.3, y=0.3, speed=0.01,
        ),
        RegionalShip.from_class(
            ship_id="hidden", name="Hidden Ship", ship_class="frigate",
            x=0.21, y=0.3, speed=0.01,
        ),
    ])
    game = RegionalGame(world)
    game.register_player(
        player_id="host", token="host-secret", controlled_ship_ids={"blue"},
        visible_ship_ids={"blue", "red"},
    )
    result = game.command(
        "host-secret", "fire_weapon", {"ship_id": "blue", "target_id": "red"}
    )
    assert result["damage"] == 2
    assert result["hull_after"] == world.ships["red"].max_hull - 2
    assert world.ships["red"].damage_by_system["hull"] == 2
    with pytest.raises(RegionalGameError, match="visible contact"):
        game.command(
            "host-secret", "fire_weapon", {"ship_id": "blue", "target_id": "hidden"}
        )
    world.ships["red"].x = 0.9
    with pytest.raises(RegionalGameError, match="outside weapon range"):
        game.command(
            "host-secret", "fire_weapon", {"ship_id": "blue", "target_id": "red"}
        )
