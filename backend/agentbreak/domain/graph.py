"""Attack graph generation for individual runs and aggregate findings."""

from __future__ import annotations

from agentbreak.attacks.scenarios import CASE_VECTOR_MAP
from agentbreak.schemas.finding import AttackGraph, Finding, GraphEdge, GraphNode
from agentbreak.schemas.run import Run, TraceStep, Verdict


def build_run_attack_graph(
    run: Run,
    trace_steps: list[TraceStep],
    verdict: Verdict | None = None,
) -> AttackGraph:
    """Construct causal attack graph for an individual evaluation run."""
    case_id = run.case_id or "AS-04"

    vector_name = CASE_VECTOR_MAP.get(case_id, "inj_email_body")
    severity = (verdict.severity if verdict else None) or "high"

    # Identify injected tool result and unauthorized tool call from trace
    inj_step = None
    unauth_step = None

    for step in trace_steps:
        if step.flags.get("injected"):
            inj_step = step
        if step.flags.get("unauthorized"):
            unauth_step = step

    inj_tool_name = (inj_step.tool if inj_step else None) or (
        "read_file" if "doc" in vector_name else "read_email"
    )
    unauth_tool_name = (unauth_step.tool if unauth_step else None) or "delete_file"

    impact_label = "Destructive Impact (File Deleted)"
    if case_id in ("AS-01", "AS-02"):
        impact_label = "Data Exfiltration (Credential Canary Exfiltrated)"
    elif case_id == "AS-03":
        impact_label = "Data Exfiltration (Drive ACL Expanded)"
    elif case_id == "AS-04":
        impact_label = "Destructive Impact (File Deleted)"
    elif case_id == "AS-05":
        impact_label = "Persistence / Covert Exfiltration Triggered"
    elif case_id in ("AS-06", "AS-07"):
        impact_label = "Privilege Escalation (Admin Role Assigned)"

    vec_label = f"Vector: {vector_name}"
    if "doc" in vector_name:
        vec_label = "Vector: f-004 doc_content"
    elif "email" in vector_name:
        vec_label = "Vector: e-1003 email_body"

    nodes = [
        GraphNode(id="n1", label=vec_label, type="vector", severity=severity, count=1),
        GraphNode(
            id="n2",
            label=f"{inj_tool_name} -> Injected",
            type="tool",
            severity=severity,
            count=1,
        ),
        GraphNode(
            id="n3",
            label=f"{unauth_tool_name} -> Unauthorized",
            type="tool",
            severity=severity,
            count=1,
        ),
        GraphNode(id="n4", label=impact_label, type="impact", severity=severity, count=1),
    ]

    edges = [
        GraphEdge(source="n1", target="n2", label="payload ingested"),
        GraphEdge(source="n2", target="n3", label="caused_by"),
        GraphEdge(source="n3", target="n4", label="state diff confirmed"),
    ]

    return AttackGraph(nodes=nodes, edges=edges)


def build_aggregate_attack_graph(findings: list[Finding]) -> AttackGraph:
    """Construct multi-finding aggregate attack graph across all evaluated vulnerabilities."""
    if not findings:
        return AttackGraph(nodes=[], edges=[])

    # Count vectors, tools, and impacts across findings
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    vector_counts: dict[str, int] = {}
    impact_counts: dict[str, int] = {}

    for f in findings:
        vec = CASE_VECTOR_MAP.get(f.case_id, "inj_email_body")
        vector_counts[vec] = vector_counts.get(vec, 0) + f.occurrences
        impact_counts[f.impact_class] = impact_counts.get(f.impact_class, 0) + f.occurrences

    for vec, count in vector_counts.items():
        nodes.append(GraphNode(id=f"v_{vec}", label=f"Vector: {vec}", type="vector", count=count))

    for imp, count in impact_counts.items():
        nodes.append(GraphNode(id=f"i_{imp}", label=f"Impact: {imp}", type="impact", count=count))

    # Connect vectors to impacts with aggregate edges
    for f in findings:
        vec = CASE_VECTOR_MAP.get(f.case_id, "inj_email_body")
        src_id = f"v_{vec}"
        tgt_id = f"i_{f.impact_class}"
        if not any(e.source == src_id and e.target == tgt_id for e in edges):
            edges.append(GraphEdge(source=src_id, target=tgt_id, label="exploited_via"))

    return AttackGraph(nodes=nodes, edges=edges)
