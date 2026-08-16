"""Versioned parameters that participate in chunk identity."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from typing import Any

from steadlith.chunk.stream import DEFAULT_TOKENIZER_ID, NORMALIZER_VERSION

CHUNKER_ID = "cdc-rabin"
BOUNDARY_RULE_VERSION = "tttd-v1"
ROLLING_HASH_ID = "rabin64-word-v1"


@dataclass(frozen=True)
class CDCParams:
    """Validated settings for Rabin/TTTD content-defined chunking."""

    window_words: int = 48
    min_tokens: int = 180
    max_tokens: int = 640
    primary_mask_bits: int = 8
    backup_mask_bits: int = 6
    snap_window_words: int = 24
    snap_to_boundaries: bool = False
    normalizer_version: str = NORMALIZER_VERSION
    tokenizer_id: str = DEFAULT_TOKENIZER_ID
    rolling_hash_id: str = ROLLING_HASH_ID
    boundary_rule_version: str = BOUNDARY_RULE_VERSION

    def __post_init__(self) -> None:
        if self.window_words < 1:
            raise ValueError("window_words must be positive")
        if self.min_tokens < 1:
            raise ValueError("min_tokens must be positive")
        if self.max_tokens < self.min_tokens:
            raise ValueError("max_tokens must be at least min_tokens")
        if not 1 <= self.backup_mask_bits < self.primary_mask_bits <= 63:
            raise ValueError("mask bits must satisfy 1 <= backup < primary <= 63")
        if self.snap_window_words < 0:
            raise ValueError("snap_window_words cannot be negative")
        if not self.normalizer_version:
            raise ValueError("normalizer_version cannot be empty")
        if not self.tokenizer_id:
            raise ValueError("tokenizer_id cannot be empty")

    @property
    def primary_mask(self) -> int:
        return (1 << self.primary_mask_bits) - 1

    @property
    def backup_mask(self) -> int:
        return (1 << self.backup_mask_bits) - 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def params_hash(self) -> str:
        encoded = json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @property
    def chunker_params_hash(self) -> str:
        return self.params_hash

    def with_snapping(self, enabled: bool = True) -> CDCParams:
        return replace(self, snap_to_boundaries=enabled)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> CDCParams:
        fields = {
            "window_words",
            "min_tokens",
            "max_tokens",
            "primary_mask_bits",
            "backup_mask_bits",
            "snap_window_words",
            "snap_to_boundaries",
            "normalizer_version",
            "tokenizer_id",
            "rolling_hash_id",
            "boundary_rule_version",
        }
        values = {key: item for key, item in value.items() if key in fields}
        strategy = value.get("strategy")
        if strategy is not None:
            values["snap_to_boundaries"] = str(strategy) == "cdc-rabin+snap"
        return cls(**values)

    @classmethod
    def from_config(cls, config: object) -> CDCParams:
        if isinstance(config, (str, bytes)):
            raise TypeError(
                "CDCParams.from_config expects a config object or mapping; "
                "load TOML with steadlith.config.load_config first"
            )
        chunker = getattr(config, "chunker", config)
        if isinstance(chunker, Mapping):
            return cls.from_mapping(chunker)
        values: dict[str, Any] = {}
        for name in (
            "window_words",
            "min_tokens",
            "max_tokens",
            "primary_mask_bits",
            "backup_mask_bits",
            "snap_window_words",
            "normalizer_version",
            "tokenizer_id",
            "rolling_hash_id",
            "boundary_rule_version",
        ):
            if hasattr(chunker, name):
                values[name] = getattr(chunker, name)
        if not values and not hasattr(chunker, "strategy"):
            raise TypeError("config must expose chunker settings or be a mapping")
        strategy = getattr(chunker, "strategy", "cdc-rabin")
        values["snap_to_boundaries"] = strategy == "cdc-rabin+snap"
        return cls(**values)


ChunkerParams = CDCParams
