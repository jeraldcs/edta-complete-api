from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompletionUsage:
    provider: str
    operation: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_units: float
    latency_ms: int = 0


def estimate_tokens(text: str) -> int:
    cleaned = (text or "").strip()
    if not cleaned:
        return 0
    return max(1, len(cleaned) // 4)


def estimate_cost_units(
    *,
    input_tokens: int,
    output_tokens: int,
    cost_per_1k_input: float,
    cost_per_1k_output: float,
) -> float:
    input_cost = (input_tokens / 1000.0) * cost_per_1k_input
    output_cost = (output_tokens / 1000.0) * cost_per_1k_output
    return round(input_cost + output_cost, 6)
