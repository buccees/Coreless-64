import json

from ai.interfaces import AIRequest, AIResult
from ai.registry import AICoreRegistry
from vigil.regional_ai import RegionalOpponent
from vigil.regional_game import RegionalGame
from vigil.regional_world import RegionalShip, RegionalWorld


class RecordingCore:
    def __init__(self, text, model_id="qwen3"):
        self.model_id = model_id
        self.text = text
        self.requests = []

    def infer(self, request: AIRequest) -> AIResult:
        self.requests.append(request)
        return AIResult(request_id=request.request_id, model_id=self.model_id, text=self.text)


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
        visible_ship_ids={"red", "blue"},
    )
    return game


def test_qwen3_proposal_is_sent_only_to_selected_registered_core_and_validated():
    game = make_game()
    core = RecordingCore(json.dumps({
        "operation": "set_heading",
        "arguments": {"ship_id": "red", "heading_deg": 270},
    }))
    unrelated = RecordingCore(json.dumps({
        "operation": "set_heading",
        "arguments": {"ship_id": "red", "heading_deg": 10},
    }), model_id="other-model")
    registry = AICoreRegistry()
    registry.register(core)
    registry.register(unrelated)
    result = RegionalOpponent(registry).take_turn(game, "opponent-secret")
    assert result["ok"] is True
    assert result["source"] == "qwen3"
    assert game.world.ships["red"].heading_deg == 270
    assert len(core.requests) == 1
    assert unrelated.requests == []
    context = core.requests[0].context
    assert context["task_kind"] == "RECOMMEND_COMMAND"
    assert "Blue Ship" in repr(context["observation"])
    assert core.requests[0].authority.value == "recommend"


def test_qwen3_cannot_command_an_enemy_ship_and_fallback_uses_visible_contact():
    game = make_game()
    core = RecordingCore(json.dumps({
        "operation": "set_heading",
        "arguments": {"ship_id": "blue", "heading_deg": 123},
    }))
    registry = AICoreRegistry()
    registry.register(core)
    result = RegionalOpponent(registry).take_turn(game, "opponent-secret")
    assert result["ok"] is True
    assert result["source"] == "fallback"
    assert game.world.ships["blue"].heading_deg == 0
    assert game.world.ships["red"].heading_deg != 0


def test_missing_or_unavailable_qwen3_uses_fallback_without_hidden_state():
    game = make_game()
    opponent = RegionalOpponent()
    result = opponent.take_turn(game, "opponent-secret")
    assert result["ok"] is True
    assert result["source"] == "fallback"

    # A separate game with no visible contact must not let fallback peek at world.ships.
    hidden_game = RegionalGame(RegionalWorld([
        RegionalShip.from_class(
            ship_id="red", name="Red Ship", ship_class="frigate",
            x=0.8, y=0.7, speed=0.01,
        ),
        RegionalShip.from_class(
            ship_id="blue", name="Secret Contact", ship_class="destroyer",
            x=0.2, y=0.3, speed=0.01,
        ),
    ]))
    hidden_game.register_player(
        player_id="opponent", token="token", controlled_ship_ids={"red"},
        visible_ship_ids={"red"},
    )
    no_contact = opponent.take_turn(hidden_game, "token")
    assert no_contact == {
        "ok": False, "source": "fallback", "reason": "no_visible_contact"
    }


def test_invalid_ai_output_degrades_safely_and_bad_token_is_rejected():
    game = make_game()
    registry = AICoreRegistry()
    registry.register(RecordingCore("not json"))
    result = RegionalOpponent(registry).take_turn(game, "opponent-secret")
    assert result["ok"] is True
    assert result["source"] == "fallback"
    assert RegionalOpponent(registry).take_turn(game, "invalid") == {
        "ok": False, "source": "none", "error": "unauthorized"
    }
