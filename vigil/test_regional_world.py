import pytest

from vigil.regional_world import RegionalShip, RegionalWorld, RegionalWorldError


def ship(ship_id="blue", **kwargs):
    values = dict(name="Patrol Ship", x=0, y=0, speed=3, max_hull=5, weapon_damage=2)
    values.update(kwargs)
    return RegionalShip(ship_id=ship_id, **values)


def test_ship_moves_by_speed_allowance_and_refreshes_each_campaign_turn():
    world = RegionalWorld([ship()])
    result = world.move("blue", 2, 0)
    assert result.distance == 2
    assert result.movement_remaining == 1
    world.move("blue", 3, 0)
    with pytest.raises(RegionalWorldError, match="remaining movement"):
        world.move("blue", 4.1, 0)
    assert world.end_turn() == 2
    assert world.ships["blue"].movement_remaining == 3
    world.move("blue", 6, 0)
    assert world.ships["blue"].x == 6


def test_ship_sinking_depends_on_accumulated_weapon_damage_not_encounters():
    world = RegionalWorld([ship(max_hull=5, weapon_damage=2)])
    # Merely being present on the map does not cause damage.
    assert world.ships["blue"].hull == 5
    first = world.apply_hit("blue", damage=2)
    assert (first.hull_after, first.sunk) == (3, False)
    second = world.apply_hit("blue", damage=2, system="propulsion")
    assert (second.hull_after, second.sunk) == (1, False)
    final = world.apply_hit("blue", damage=2, system="hull")
    assert (final.hull_after, final.sunk) == (0, True)
    with pytest.raises(RegionalWorldError, match="already sunk"):
        world.apply_hit("blue", damage=1)


def test_movement_and_damage_validate_actions():
    world = RegionalWorld([ship()])
    with pytest.raises(RegionalWorldError, match="positive integer"):
        world.apply_hit("blue", damage=0)
    with pytest.raises(RegionalWorldError, match="unknown ship"):
        world.move("missing", 1, 1)
    with pytest.raises(RegionalWorldError, match="cannot move"):
        sunk = ship("wreck", hull=0)
        world.add_ship(sunk)
        world.move("wreck", 1, 0)


def test_public_map_only_returns_authorized_observations():
    world = RegionalWorld([ship("friendly"), ship("hidden", name="Unknown Contact", x=9, y=4)])
    view = world.public_map({"friendly"})
    assert len(view) == 1
    assert view[0]["ship_id"] == "friendly"
    assert "hidden" not in repr(view)



def test_ship_class_sets_hits_to_sink_for_single_spot_rts_ships():
    from vigil.regional_world import SHIP_CLASS_HULL

    expected = {
        "patrol": 3, "corvette": 4, "submarine": 4, "frigate": 5,
        "destroyer": 6, "cruiser": 8, "battleship": 10, "carrier": 12,
    }
    assert SHIP_CLASS_HULL == expected
    for ship_class, hits in expected.items():
        vessel = RegionalShip.from_class(
            ship_id=ship_class, name=ship_class.title(), ship_class=ship_class,
            x=0, y=0, speed=2,
        )
        assert vessel.max_hull == hits
        assert vessel.hits_to_sink_at_one_damage == hits
        world = RegionalWorld([vessel])
        for remaining in range(hits - 1, 0, -1):
            result = world.apply_hit(ship_class, damage=1)
            assert result.hull_after == remaining
            assert result.sunk is False
        result = world.apply_hit(ship_class, damage=1)
        assert result.hull_after == 0
        assert result.sunk is True


def test_unknown_ship_class_is_rejected():
    with pytest.raises(RegionalWorldError, match="unknown ship class"):
        RegionalShip.from_class(
            ship_id="x", name="Mystery", ship_class="super-ship",
            x=0, y=0, speed=2,
        )



def test_blueprint_dimensions_preserve_real_length_to_beam_aspect_ratio():
    vessel = RegionalShip.from_blueprint(
        ship_id="ddg-example", name="Example Destroyer", ship_class="destroyer",
        x=10, y=20, speed=4, length_m=155.0, beam_m=20.0,
        blueprint_source="Example naval architecture plan, drawing sheet 2",
        max_hull=6, heading_deg=90,
    )
    assert vessel.aspect_ratio == 7.75
    assert vessel.length_m == 155.0
    assert vessel.beam_m == 20.0
    assert vessel.heading_deg == 90
    assert vessel.blueprint_source


def test_blueprint_ship_requires_sourced_dimensions_and_valid_ratio():
    with pytest.raises(RegionalWorldError, match="blueprint_source is required"):
        RegionalShip.from_blueprint(
            ship_id="x", name="Unsourced", ship_class="custom", x=0, y=0,
            speed=1, length_m=100, beam_m=20, blueprint_source="",
            max_hull=5,
        )
    with pytest.raises(RegionalWorldError, match="length >= beam"):
        RegionalShip.from_blueprint(
            ship_id="x", name="Invalid", ship_class="custom", x=0, y=0,
            speed=1, length_m=10, beam_m=20, blueprint_source="source",
            max_hull=5,
        )


def test_realtime_tick_moves_all_afloat_ships_by_heading_and_elapsed_time():
    north = ship("north", x=0, y=0, speed=2, heading_deg=0)
    east = ship("east", x=5, y=5, speed=3, heading_deg=90)
    wreck = ship("wreck", x=9, y=9, speed=4, heading_deg=0, hull=0)
    world = RegionalWorld([north, east, wreck])
    results = world.advance_realtime_tick(2)
    assert [r.ship_id for r in results] == ["north", "east"]
    assert north.x == pytest.approx(0)
    assert north.y == pytest.approx(4)
    assert east.x == pytest.approx(11)
    assert east.y == pytest.approx(5)
    assert wreck.x == 9 and wreck.y == 9
    # Real-time movement does not consume the separate campaign allowance.
    assert north.movement_remaining == 2


@pytest.mark.parametrize("delta", [0, -1, float("inf"), float("nan")])
def test_realtime_tick_rejects_invalid_elapsed_time(delta):
    world = RegionalWorld([ship()])
    with pytest.raises(RegionalWorldError, match="finite positive number"):
        world.advance_realtime_tick(delta)


def test_public_snapshot_is_versioned_and_contains_only_authorized_ships():
    world = RegionalWorld([
        ship("friendly", x=0.25, y=0.75, speed=2.5, heading_deg=90),
        ship("hidden", name="Hidden Enemy", x=0.8, y=0.2),
    ])
    snapshot = world.public_snapshot({"friendly"})
    assert snapshot["schema_version"] == 1
    assert snapshot["turn"] == 1
    assert len(snapshot["ships"]) == 1
    visible = snapshot["ships"][0]
    assert visible["ship_id"] == "friendly"
    assert visible["x"] == 0.25 and visible["y"] == 0.75
    assert visible["speed"] == 2.5 and visible["heading_deg"] == 90
    assert "Hidden Enemy" not in repr(snapshot)


def test_public_snapshot_normalizes_world_coordinates_for_map():
    world = RegionalWorld([ship("visible", x=50, y=25), ship("outside", x=150, y=25)])
    snapshot = world.public_snapshot({"visible", "outside"}, world_bounds=(0, 0, 100, 100))
    assert snapshot["ships"][0]["normalized_position"] == [0.5, 0.25]
    assert [s["ship_id"] for s in snapshot["ships"]] == ["visible"]


def test_public_snapshot_rejects_invalid_map_bounds():
    world = RegionalWorld([ship()])
    with pytest.raises(RegionalWorldError, match="world_bounds"):
        world.public_snapshot({"blue"}, world_bounds=(0, 0, 0, 1))
