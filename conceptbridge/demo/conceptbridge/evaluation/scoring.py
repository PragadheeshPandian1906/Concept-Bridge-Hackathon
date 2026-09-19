"""Deterministic evaluation scoring and learning-gain arithmetic.

The LLM never computes a gain and never decides effectiveness.
"""
from __future__ import annotations


def learning_gain(pre_score: float, post_score: float) -> float:
    return round(post_score - pre_score, 4)


def is_effective(gain: float, threshold: float) -> bool:
    return gain >= threshold


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0
