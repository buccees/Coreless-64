from vigil.factions import FACTIONS, public_faction_catalog
from vigil.regional_game import RegionalGame
from vigil.regional_world import RegionalShip, RegionalWorld


def test_corporate_factions_are_in_core_simulation_catalog():
    names = {faction.name for faction in FACTIONS}
    assert {"Prodigy", "Weyland-Yutani", "Lynch", "Dynamic", "Threshold"} <= names
    assert len({faction.faction_id for faction in FACTIONS}) == len(FACTIONS)


def test_regional_snapshot_exposes_core_factions_without_hidden_ships():
    world = RegionalWorld([
        RegionalShip.from_class(
            ship_id="visible", name="Visible", ship_class="destroyer",
            x=0.2, y=0.3, speed=0.0, faction_id="prodigy",
        ),
        RegionalShip.from_class(
            ship_id="hidden", name="Hidden", ship_class="frigate",
            x=0.8, y=0.7, speed=0.0, faction_id="weyland-yutani",
        ),
    ])
    game = RegionalGame(world)
    game.register_player(
        player_id="pilot", token="test-token",
        controlled_ship_ids=["visible"], visible_ship_ids=["visible"],
    )
    snapshot = game.snapshot("test-token")
    assert {item["name"] for item in snapshot["factions"]} >= {
        "Prodigy", "Weyland-Yutani", "Lynch", "Dynamic", "Threshold"
    }
    assert [ship["ship_id"] for ship in snapshot["ships"]] == ["visible"]
