"""Model architecture boundary for Coreless AI execution.

External ecosystems may describe models differently. This module converts
those descriptions into a small Coreless-native configuration so execution
does not depend on an external framework.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransformerConfig:
    hidden_size: int
    intermediate_size: int
    num_layers: int
    num_heads: int
    vocab_size: int
    max_sequence_length: int

    def __post_init__(self) -> None:
        values = (
            self.hidden_size,
            self.intermediate_size,
            self.num_layers,
            self.num_heads,
            self.vocab_size,
            self.max_sequence_length,
        )
        if any(value <= 0 for value in values):
            raise ValueError("Transformer dimensions must be positive")
        if self.hidden_size % self.num_heads:
            raise ValueError("hidden_size must be divisible by num_heads")


def from_mapping(config: dict[str, int]) -> TransformerConfig:
    """Translate common architecture metadata into Coreless configuration.

    The aliases cover common model metadata conventions without importing any
    external framework.
    """
    aliases = {
        "hidden_size": ("hidden_size", "d_model", "n_embd"),
        "intermediate_size": ("intermediate_size", "ffn_dim", "n_inner"),
        "num_layers": ("num_layers", "num_hidden_layers", "n_layer"),
        "num_heads": ("num_heads", "num_attention_heads", "n_head"),
        "vocab_size": ("vocab_size",),
        "max_sequence_length": (
            "max_sequence_length",
            "max_position_embeddings",
            "n_positions",
        ),
    }

    values: dict[str, int] = {}
    for target, names in aliases.items():
        for name in names:
            if name in config:
                values[target] = int(config[name])
                break
        else:
            raise ValueError(f"missing Transformer configuration field: {target}")
    return TransformerConfig(**values)
