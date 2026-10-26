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
