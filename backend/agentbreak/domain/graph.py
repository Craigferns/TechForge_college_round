"""Pure attack graph domain generator for runs and multi-finding aggregates (PLAN.md §8.4 / M7.2)."""

from __future__ import annotations

import sqlite3

from agentbreak.attacks.scenarios import CASE_VECTOR_MAP, get_attack_case, get_scenario
from agentbreak.repo.finding_repo import FindingRepo
from agentbreak.repo.run_repo import RunRepo
from agentbreak.schemas.finding import AttackGraph, GraphEdge, GraphNode


def build_run_graph(run_id: str, conn: sqlite3.Connection) -> AttackGraph:
    """Build causal attack graph for a single run: vector -> tool_result(injected) -> tool_call(unauthorized) -> impact."""
    run_repo = RunRepo(conn)
    run = run_repo.get(run_id)
    if not run:
        return AttackGraph(nodes=[], edges=[])

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    # 1. Vector node
    vector = "inj_email_body"
    if run.case_id:
        vector = CASE_VECTOR_MAP.get(run.case_id, vector)
    vector_node_id = f"vec_{vector}"
    nodes.append(GraphNode(id=vector_node_id, label=f"Vector: {vector}", type="vector", count=1))

    # 2. Inspect trace steps for injected tool result and unauthorized tool call
    trace = run_repo.get_trace(run_id)
    injected_step = next((s for s in trace if s.flags.get("injected")), None)
    unauthorized_step = next((s for s in trace if s.flags.get("unauthorized")), None)

    last_node_id = vector_node_id

    if injected_step:
        inj_node_id = f"step_{injected_step.idx}"
        inj_label = f"{injected_step.tool or 'carrier'} result (injected)"
        nodes.append(GraphNode(id=inj_node_id, label=inj_label, type="tool", count=1))
        edges.append(GraphEdge(source=last_node_id, target=inj_node_id, label="carried_by"))
        last_node_id = inj_node_id

    if unauthorized_step:
        unauth_node_id = f"step_{unauthorized_step.idx}"
        denied = bool(unauthorized_step.flags.get("denied"))
        unauth_label = (
            f"{unauthorized_step.tool} call ({'denied by policy' if denied else 'unauthorized'})"
        )
        nodes.append(GraphNode(id=unauth_node_id, label=unauth_label, type="tool", count=1))
        edges.append(GraphEdge(source=last_node_id, target=unauth_node_id, label="triggered"))
        last_node_id = unauth_node_id

    # 3. Impact node
    impact_class = "unauthorized_action"
    severity = "medium"
    if run.scenario_id:
        try:
            sc = get_scenario(run.scenario_id)
            impact_class = sc.impact_class
            severity = sc.severity
        except KeyError:
            pass

    # Only a confirmed verdict earns an impact node: no edge is drawn for harm that did not happen.
    verdict = run_repo.get_verdict(run_id)
    if not (verdict and verdict.success):
        return AttackGraph(nodes=nodes, edges=edges)

    impact_node_id = f"impact_{impact_class}"
    nodes.append(
        GraphNode(
            id=impact_node_id,
            label=f"Impact: {impact_class}",
            type="impact",
            severity=severity,
            count=1,
        )
    )
    edges.append(GraphEdge(source=last_node_id, target=impact_node_id, label="caused"))

    return AttackGraph(nodes=nodes, edges=edges)


def build_aggregate_graph(conn: sqlite3.Connection, target_id: str | None = None) -> AttackGraph:
    """Build aggregated attack graph with nodes keyed by (vector), (tool), and (impact_class) with counts across findings."""
    finding_repo = FindingRepo(conn)
    findings, _ = finding_repo.list_findings(target_id=target_id, limit=500)

    vector_counts: dict[str, int] = {}
    tool_counts: dict[str, int] = {}
    impact_counts: dict[str, tuple[int, str]] = {}  # impact -> (count, severity)
    vector_to_tool: dict[tuple[str, str], int] = {}
    tool_to_impact: dict[tuple[str, str], int] = {}

    for f in findings:
        case = None
        try:
            case = get_attack_case(f.case_id)
            get_scenario(f.scenario_id)
        except KeyError:
            continue

        vector = CASE_VECTOR_MAP.get(case.id, "inj_email_body")
        impact = f.impact_class
        severity = f.severity

        vector_counts[vector] = vector_counts.get(vector, 0) + f.occurrences
        cur_imp = impact_counts.get(impact, (0, severity))
        impact_counts[impact] = (cur_imp[0] + f.occurrences, severity)

        # Primary enabling tool or carrier tool
        tool = f.enabling_permissions[0] if f.enabling_permissions else "agent_tools"
        tool_counts[tool] = tool_counts.get(tool, 0) + f.occurrences

        vector_to_tool[(vector, tool)] = vector_to_tool.get((vector, tool), 0) + f.occurrences
        tool_to_impact[(tool, impact)] = tool_to_impact.get((tool, impact), 0) + f.occurrences

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    for vec, count in vector_counts.items():
        nodes.append(GraphNode(id=f"vec_{vec}", label=f"Vector: {vec}", type="vector", count=count))

    for tool, count in tool_counts.items():
        nodes.append(GraphNode(id=f"tool_{tool}", label=f"Tool: {tool}", type="tool", count=count))

    for imp, (count, sev) in impact_counts.items():
        nodes.append(
            GraphNode(
                id=f"impact_{imp}",
                label=f"Impact: {imp}",
                type="impact",
                severity=sev,
                count=count,
            )
        )

    for (vec, tool), count in vector_to_tool.items():
        edges.append(
            GraphEdge(
                source=f"vec_{vec}",
                target=f"tool_{tool}",
                label=f"exploits ({count})",
            )
        )

    for (tool, imp), count in tool_to_impact.items():
        edges.append(
            GraphEdge(
                source=f"tool_{tool}",
                target=f"impact_{imp}",
                label=f"causes ({count})",
            )
        )

    return AttackGraph(nodes=nodes, edges=edges)
