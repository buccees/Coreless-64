"""Native Qwen3 tokenizer implementation.

Qwen3 uses a Hugging Face BPE tokenizer with NFC normalization, a Qwen-style
regex pre-tokenizer, byte-level BPE, and a byte-level decoder. This module
implements those native stages directly from tokenizer.json rather than
substituting another tokenizer implementation.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


def _bytes_to_unicode() -> dict[int, str]:
    direct = list(range(ord("!"), ord("~") + 1))
    direct += list(range(ord("¡"), ord("¬") + 1))
    direct += list(range(ord("®"), ord("ÿ") + 1))
    extra = [byte for byte in range(256) if byte not in direct]
    return {
        byte: chr(value)
        for byte, value in zip(range(256), direct + [256 + i for i in range(len(extra))])
    }


BYTE_TO_UNICODE = _bytes_to_unicode()
UNICODE_TO_BYTE = {char: byte for byte, char in BYTE_TO_UNICODE.items()}


def _is_letter_or_mark(char: str) -> bool:
    category = unicodedata.category(char)
    return category.startswith("L") or category.startswith("M")


def _is_number(char: str) -> bool:
    return unicodedata.category(char).startswith("N")


def _is_word(char: str) -> bool:
    return _is_letter_or_mark(char) or _is_number(char)


def _qwen_pretokenize(text: str) -> list[str]:
    """Implement the classic Qwen2/Qwen3 pre-tokenizer semantics."""
    chunks: list[str] = []
    i = 0
    n = len(text)
    contractions = ("'s", "'t", "'re", "'ve", "'m", "'ll", "'d")

    while i < n:
        lowered = text[i:].lower()
        contraction = next((c for c in contractions if lowered.startswith(c)), None)
        if contraction:
            chunks.append(text[i:i + len(contraction)])
            i += len(contraction)
            continue

        start = i
        if (
            text[i] not in "\r\n"
            and not _is_word(text[i])
            and not text[i].isspace()
            and i + 1 < n
            and _is_letter_or_mark(text[i + 1])
        ):
            i += 1
        if i < n and _is_letter_or_mark(text[i]):
            i += 1
            while i < n and _is_letter_or_mark(text[i]):
                i += 1
            chunks.append(text[start:i])
            continue

        if _is_number(text[i]):
            chunks.append(text[i])
            i += 1
            continue

        start = i
        if text[i] == " ":
            i += 1
        if i < n and not text[i].isspace() and not _is_word(text[i]):
            while i < n and not text[i].isspace() and not _is_word(text[i]):
                i += 1
            while i < n and text[i] in "\r\n":
                i += 1
            chunks.append(text[start:i])
            continue

        start = i
        if text[i] in "\r\n":
            while i < n and text[i] in "\r\n":
                i += 1
        else:
            while i < n and text[i].isspace():
                i += 1
        chunks.append(text[start:i])

    return chunks


def _merge_bpe(
    piece: str,
    vocab: dict[str, int],
    merge_ranks: dict[tuple[str, str], int],
) -> list[str]:
    symbols = [BYTE_TO_UNICODE[b] for b in piece.encode("utf-8")]
    while len(symbols) > 1:
        pairs = list(zip(symbols, symbols[1:]))
        best = min(pairs, key=lambda pair: merge_ranks.get(pair, float("inf")))
        if best not in merge_ranks:
            break
        merged: list[str] = []
        i = 0
        left, right = best
        while i < len(symbols):
            if i + 1 < len(symbols) and symbols[i] == left and symbols[i + 1] == right:
                merged.append(left + right)
                i += 2
            else:
                merged.append(symbols[i])
                i += 1
        symbols = merged

    for symbol in symbols:
        if symbol not in vocab:
            raise ValueError(f"tokenizer BPE produced unknown token: {symbol!r}")
    return symbols


@dataclass(frozen=True)
class Qwen3TokenizerArtifact:
    vocab_size: int
    model_type: str
    vocab: dict[str, int]
    merges: tuple[tuple[str, str], ...] = ()
    special_tokens: dict[str, int] | None = None

    @classmethod
    def load(
        cls,
        path: str | Path,
        expected_vocab_size: int | None = None,
    ) -> "Qwen3TokenizerArtifact":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("tokenizer artifact must be a JSON object")
        model = data.get("model")
        if not isinstance(model, dict):
            raise ValueError("tokenizer model metadata is missing")
        if model.get("type") != "BPE":
            raise ValueError("Qwen3 tokenizer requires a BPE model")

        vocab = model.get("vocab")
        if not isinstance(vocab, dict) or not vocab:
            raise ValueError("tokenizer vocabulary is missing")
        normalized = {str(token): int(index) for token, index in vocab.items()}
        if len(set(normalized.values())) != len(normalized):
            raise ValueError("tokenizer vocabulary contains duplicate token IDs")

        merges: list[tuple[str, str]] = []
        for merge in model.get("merges", []):
            if isinstance(merge, str):
                parts = merge.split(" ", 1)
            elif isinstance(merge, list) and len(merge) == 2:
                parts = [str(merge[0]), str(merge[1])]
            else:
                raise ValueError("invalid BPE merge entry")
            if len(parts) != 2:
                raise ValueError("invalid BPE merge entry")
            merges.append((parts[0], parts[1]))

        vocab_size = max(normalized.values()) + 1
        if expected_vocab_size is not None and vocab_size > expected_vocab_size:
            raise ValueError("tokenizer vocabulary exceeds Qwen3 model vocabulary")

        special_tokens: dict[str, int] = {}
        for entry in data.get("added_tokens", []):
            if isinstance(entry, dict) and entry.get("special") is True:
                special_tokens[str(entry["content"])] = int(entry["id"])

        return cls(
            vocab_size=vocab_size,
            model_type=str(model.get("type", "")),
            vocab=normalized,
            merges=tuple(merges),
            special_tokens=special_tokens,
        )

    @property
    def merge_ranks(self) -> dict[tuple[str, str], int]:
        return {pair: rank for rank, pair in enumerate(self.merges)}

    def encode(self, text: str, *, add_special_tokens: bool = False) -> list[int]:
        if not isinstance(text, str):
            raise TypeError("Qwen3 tokenizer input must be text")
        if add_special_tokens:
            raise ValueError("Qwen3 has no default BOS token to add")

        normalized = unicodedata.normalize("NFC", text)
        special = self.special_tokens or {}
        pieces: list[str] = []

        if special:
            pattern = re.compile(
                "(" + "|".join(re.escape(s) for s in sorted(special, key=len, reverse=True)) + ")"
            )
            parts = pattern.split(normalized)
            for part in parts:
                if not part:
                    continue
                if part in special:
                    pieces.append(part)
                else:
                    pieces.extend(_qwen_pretokenize(part))
        else:
            pieces = _qwen_pretokenize(normalized)

        ids: list[int] = []
        ranks = self.merge_ranks
        for piece in pieces:
            if piece in special:
                ids.append(special[piece])
                continue
            ids.extend(self.vocab[token] for token in _merge_bpe(piece, self.vocab, ranks))
        return ids

    def decode(self, token_ids: Iterable[int]) -> str:
        inverse = {index: token for token, index in self.vocab.items()}
        special_by_id = {
            index: token for token, index in (self.special_tokens or {}).items()
        }
        output: list[str] = []
        byte_buffer = bytearray()

        def flush() -> None:
            if byte_buffer:
                output.append(bytes(byte_buffer).decode("utf-8", errors="replace"))
                byte_buffer.clear()

        for token_id in token_ids:
            token_id = int(token_id)
            if token_id in special_by_id:
                flush()
                output.append(special_by_id[token_id])
                continue
            token = inverse.get(token_id)
            if token is None:
                raise ValueError(f"unknown Qwen3 token ID: {token_id}")
            for char in token:
                byte = UNICODE_TO_BYTE.get(char)
                if byte is None:
                    flush()
                    output.append(char)
                else:
                    byte_buffer.append(byte)
        flush()
        return "".join(output)


def load_qwen3_tokenizer(
    model_directory: str | Path,
    expected_vocab_size: int | None = None,
) -> Qwen3TokenizerArtifact:
    root = Path(model_directory)
    return Qwen3TokenizerArtifact.load(root / "tokenizer.json", expected_vocab_size)
