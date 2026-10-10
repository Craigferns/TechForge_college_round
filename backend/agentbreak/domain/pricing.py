"""Pure pricing and set-based Pareto dominance evaluation (PLAN.md §11.2 / M9.1)."""

from __future__ import annotations

from typing import Any


def compute_pareto_dominance(
    evals: list[dict[str, Any]],
) -> list[bool]:
    """Compute set-based Pareto dominance flags across a list of fix evaluations.

    Rule (PLAN.md §11.2):
    Fix F1 dominates F2 (F1 > F2) iff:
    Blocked(F2) subseteq Blocked(F1) AND Broken(F1) subseteq Broken(F2)
    with at least one strict inclusion.

    Non-dominated fixes receive pareto: true.
    """
    n = len(evals)
    is_dominated = [False] * n

    for i in range(n):
        blocked_i = set(evals[i].get("blocked_cases", []))
        broken_i = set(evals[i].get("broken_tasks", []))

        for j in range(n):
            if i == j:
                continue
            blocked_j = set(evals[j].get("blocked_cases", []))
            broken_j = set(evals[j].get("broken_tasks", []))

            # Does F_j strictly dominate F_i?
            if (
                blocked_i.issubset(blocked_j)
                and broken_j.issubset(broken_i)
                and (blocked_i != blocked_j or broken_j != broken_i)
            ):
                is_dominated[i] = True
                break

    return [not dom for dom in is_dominated]
