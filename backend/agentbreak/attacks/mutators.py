"""Deterministic mutation operators for prompt injection payloads (PLAN.md §6.2 / M6.1)."""

from __future__ import annotations

import re
from collections.abc import Callable

# Operators: rephrase, move_placement(start|middle|end), wrap_delimiters, add_urgency, split_sentences


def op_add_urgency(text: str) -> str:
    """Add urgent emphasis prefix."""
    return f"IMMEDIATE PRIORITY REQUIRED! {text}"


def op_wrap_delimiters(text: str) -> str:
    """Wrap payload in markdown code delimiters or quotes."""
    return f"```\n{text}\n```"


def op_rephrase(text: str) -> str:
    """Deterministic formal rephrase."""
    replaced = text.replace("requires you to:", "mandates following procedure:")
    if replaced == text:
        return f"Per standard administrative operating procedures: {text}"
    return replaced


def op_split_sentences(text: str) -> str:
    """Split sentences with line breaks."""
    return text.replace(". ", ".\n\n")


def op_move_placement(text: str, placement: str = "end") -> str:
    """Reorder payload or extract machine marker positioning."""
    marker_match = re.search(r"(\[\[AB:[^\]]+\]\])", text)
    if not marker_match:
        return text

    marker = marker_match.group(1)
    body = text.replace(marker, "").strip()

    if placement == "start":
        return f"{marker} {body}"
    elif placement == "middle":
        half = len(body) // 2
        return f"{body[:half]} {marker} {body[half:]}"
    else:  # end
        return f"{body} {marker}"


MUTATOR_OPERATORS: dict[str, Callable[[str], str]] = {
    "add_urgency": op_add_urgency,
    "wrap_delimiters": op_wrap_delimiters,
    "rephrase": op_rephrase,
    "split_sentences": op_split_sentences,
    "placement_start": lambda t: op_move_placement(t, "start"),
    "placement_middle": lambda t: op_move_placement(t, "middle"),
    "placement_end": lambda t: op_move_placement(t, "end"),
    # Harness test operator: strips the machine marker to test failure on simulated target
    "drop_marker": lambda t: re.sub(r"\[\[AB:[^\]]+\]\]", "", t),
}


def apply_mutations(text: str, ops: list[str]) -> str:
    """Apply a chain of up to 2 mutation operators in order, capping at 1,500 chars."""
    current = text
    for op_name in ops[:2]:
        if op_name in MUTATOR_OPERATORS:
            current = MUTATOR_OPERATORS[op_name](current)
    return current[:1500]
