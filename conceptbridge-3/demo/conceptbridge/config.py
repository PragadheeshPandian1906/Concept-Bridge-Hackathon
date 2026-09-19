"""All tunable domain parameters live here - never hard-coded in logic."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _i(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class DomainConfig:
    strength_threshold: float = 0.70
    gap_threshold: float = 0.60
    min_transfer_gap: float = 0.20
    effective_gain_threshold: float = 0.20
    min_group_size: int = 2
    max_group_size: int = 5
    max_teaching_load: int = 3
    hub_out_degree: int = 3
    bottleneck_ratio: float = 3.0
    questions_per_concept: int = 3
    weights: dict = field(
        default_factory=lambda: {
            "coverage": 0.30,
            "reciprocity": 0.15,
            "transfer_strength": 0.25,
            "fairness": 0.10,
            "observed_effectiveness": 0.20,
            "previous_match_penalty": 0.25,
            "teaching_load_penalty": 0.20,
        }
    )


@lru_cache(maxsize=1)
def get_config() -> DomainConfig:
    return DomainConfig(
        strength_threshold=_f("STRENGTH_THRESHOLD", 0.70),
        gap_threshold=_f("GAP_THRESHOLD", 0.60),
        min_transfer_gap=_f("MIN_TRANSFER_GAP", 0.20),
        effective_gain_threshold=_f("EFFECTIVE_GAIN_THRESHOLD", 0.20),
        min_group_size=_i("MIN_GROUP_SIZE", 2),
        max_group_size=_i("MAX_GROUP_SIZE", 5),
        max_teaching_load=_i("MAX_TEACHING_LOAD", 3),
        hub_out_degree=_i("HUB_OUT_DEGREE", 3),
        bottleneck_ratio=_f("BOTTLENECK_RATIO", 3.0),
        questions_per_concept=_i("QUESTIONS_PER_CONCEPT", 3),
    )
