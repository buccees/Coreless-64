"""Validated regional opponent policies, including an optional shared-Qwen3 adapter.

The AI only receives its player's authorized snapshot. Model text is treated as
an untrusted recommendation and must pass the same RegionalGame command checks
as a human command. No model output directly mutates simulation state.
"""
from __future__ import annotations

import json
from math import atan2, degrees
from typing import Mapping

from ai.interfaces import AIRequest, AuthorityLevel
from ai.registry import AICoreRegistry

from .regional_game import RegionalGame, RegionalGameError


class RegionalOpponent:
    """Optional Qwen3-backed opponent with a deterministic safe fallback."""

    def __init__(
        self,
        registry: AICoreRegistry | None = None,
        *,
        model_id: str = "qwen3",
    ) -> None:
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must not be empty")
        self.registry = registry
        self.model_id = model_id

    def available(self) -> bool:
        if self.registry is None:
            return False
        try:
            return self.registry.descriptor(self.model_id).enabled
        except KeyError:
            return False

    def take_turn(self, game: RegionalGame, token: str) -> dict[str, object]:
        """Request one action; validate it, or use the deterministic fallback."""
        try:
            observation = game.snapshot(token)
        except RegionalGameError:
            return {"ok": False, "source": "none", "error": "unauthorized"}
        player_id = str(observation["player_id"])
        controlled = list(observation["controlled_ship_ids"])
        if self.available():
            request_id = f"vigil-opponent-{player_id}-{observation['simulation_tick']}"
            request = AIRequest(
                request_id=request_id,
                authority=AuthorityLevel.RECOMMEND,
                prompt=(
                    "Choose exactly one legal VIGIL ship command for this turn. "
                    "Return only JSON with keys operation and arguments. "
                    'Allowed operations: fire_weapon with ship_id and target_id; '
                    'set_heading with ship_id and heading_deg; '
                    "campaign_move with ship_id, x, and y. Only command ships in "
                    "controlled_ship_ids. Use only the supplied observation; "
                    "do not invent unseen contacts or fields."
                ),
                context={
                    "source": "vigil-regional-opponent",
                    "task_kind": "RECOMMEND_COMMAND",
                    "observation": observation,
                    "controlled_ship_ids": controlled,
                },
            )
            try:
                results = self.registry.infer(request, model_ids=(self.model_id,))
                if results:
                    result = results[0]
                    if result.request_id == request_id and result.model_id == self.model_id:
                        proposal = self._parse_proposal(result.text)
                        if proposal is not None:
                            try:
                                applied = game.command(token, proposal[0], proposal[1])
                                return {"ok": True, "source": self.model_id, "result": applied}
                            except (RegionalGameError, ValueError):
                                pass
            except (KeyError, RuntimeError, TimeoutError, ValueError):
                pass
        fallback = self._fallback_command(game, token, observation)
        if fallback is None:
            return {"ok": False, "source": "fallback", "reason": "no_visible_contact"}
        try:
            applied = game.command(token, fallback[0], fallback[1])
            return {"ok": True, "source": "fallback", "result": applied}
        except (RegionalGameError, ValueError):
            return {"ok": False, "source": "fallback", "reason": "no_legal_action"}

    @staticmethod
    def _parse_proposal(text: object) -> tuple[str, Mapping[str, object]] | None:
        if not isinstance(text, str):
            return None
        try:
            proposal = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(proposal, dict):
            return None
        operation, arguments = proposal.get("operation"), proposal.get("arguments")
        if operation not in {"fire_weapon", "set_heading", "campaign_move"} or not isinstance(arguments, dict):
            return None
        return operation, arguments

    @staticmethod
    def _fallback_command(
        game: RegionalGame, token: str, observation: Mapping[str, object]
    ) -> tuple[str, Mapping[str, object]] | None:
        controlled = set(observation.get("controlled_ship_ids", []))
        ships = observation.get("ships", [])
        if not isinstance(ships, list):
            return None
        own = [item for item in ships if isinstance(item, dict) and item.get("ship_id") in controlled]
        contacts = [
            item for item in ships
            if isinstance(item, dict) and item.get("ship_id") not in controlled
            and item.get("afloat") is True
        ]
        if not own or not contacts:
            return None
        try:
            # Fire whenever an authorized visible target is in the ship's configured range.
            for ship in own:
                sx, sy = float(ship["x"]), float(ship["y"])
                for target in contacts:
                    tx, ty = float(target["x"]), float(target["y"])
                    if (tx - sx) ** 2 + (ty - sy) ** 2 <= float(ship.get("weapon_range", 0.15)) ** 2:
                        return "fire_weapon", {
                            "ship_id": ship["ship_id"], "target_id": target["ship_id"]
                        }
            target = contacts[0]
            tx, ty = float(target["x"]), float(target["y"])
            own.sort(key=lambda item: (
                (float(item["x"]) - tx) ** 2 + (float(item["y"]) - ty) ** 2
            ))
            ship = own[0]
            dx, dy = tx - float(ship["x"]), ty - float(ship["y"])
            heading = (degrees(atan2(dx, dy)) + 360.0) % 360.0
            return "set_heading", {"ship_id": ship["ship_id"], "heading_deg": heading}
        except (KeyError, TypeError, ValueError, OverflowError):
            return None
