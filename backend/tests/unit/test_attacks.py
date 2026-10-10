"""Unit tests for attack execution, predicates, and scenario coverage."""

from __future__ import annotations

import pytest
from agentbreak.attacks.scenarios import ATTACK_CASES, CASE_VECTOR_MAP
from agentbreak.attacks.templates import render_payload
from agentbreak.domain.policy import compute_policy_hash
from agentbreak.domain.predicates import (
    ATTACKER_EMAIL,
    BUDGET_FILE_ID,
    CANARY_KEY,
    CREDENTIALS_FILE_ID,
    STANDING_INSTRUCTION_MARKER,
    check_p_acl,
    check_p_delete,
    check_p_exfil_mail,
    check_p_plant,
    check_p_priv,
    check_p_trigger,
)
from agentbreak.engine.loop import run_once
from agentbreak.sandbox.acme.env import AcmeEnv
from agentbreak.sandbox.acme.injection_tasks import INJECTION_TASK_MAP
from agentbreak.sandbox.acme.models import Email
from agentbreak.sandbox.acme.user_tasks import (
    BT01_SummarizeNewestEmail,
    BT08_ReadVendorOnboardingSteps,
    BT10_EmailSummaryToSam,
)
from agentbreak.schemas.policy import Grant, Policy
from agentbreak.targets.scripted import AgentProfile, ScriptedTarget

ALL_10_TOOLS = [
    "list_inbox",
    "read_email",
    "send_email",
    "list_files",
    "read_file",
    "share_file",
    "delete_file",
    "write_memory",
    "read_memory",
    "set_role",
]


@pytest.fixture
def full_policy() -> Policy:
    grants = [Grant(tool=t) for t in ALL_10_TOOLS]
    return Policy(
        id="pol_full",
        name="Full Policy",
        grants=grants,
        hash=compute_policy_hash(grants),
        created_at="2026-10-10T00:00:00Z",
    )


CARRIER_MAP = {
    "BT-01": BT01_SummarizeNewestEmail,
    "BT-08": BT08_ReadVendorOnboardingSteps,
    "BT-10": BT10_EmailSummaryToSam,
}


@pytest.mark.parametrize("case", ATTACK_CASES, ids=lambda c: c.id)
def test_attack_cases_gullible_scripted_agent(case, full_policy: Policy) -> None:
    """AS-01..AS-07 executed by gullible scripted agent on full policy yield security=True."""
    target = ScriptedTarget(profile=AgentProfile(obeys=None))
    carrier_cls = CARRIER_MAP[case.carrier_task_id]
    inj_cls = INJECTION_TASK_MAP[case.injection_task_id]

    carrier_task = carrier_cls()
    inj_task = inj_cls()

    vector_name = CASE_VECTOR_MAP[case.id]
    rendered, _ = render_payload(
        injection_task_id=case.injection_task_id,
        goal_text=inj_task.GOAL,
    )
    injections = {vector_name: rendered}

    outcome = run_once(
        target=target,
        policy=full_policy,
        user_task=carrier_task,
        injection_task=inj_task,
        injections=injections,
    )

    assert outcome.security is True, f"Attack case {case.id} failed to trigger security breach"


@pytest.mark.parametrize("case", ATTACK_CASES, ids=lambda c: c.id)
def test_attack_cases_defended_agent_obeys_none(case, full_policy: Policy) -> None:
    """When agent obeys=empty, attack attempts result in security=False."""
    target = ScriptedTarget(profile=AgentProfile(obeys=frozenset()))
    carrier_cls = CARRIER_MAP[case.carrier_task_id]
    inj_cls = INJECTION_TASK_MAP[case.injection_task_id]

    carrier_task = carrier_cls()
    inj_task = inj_cls()

    vector_name = CASE_VECTOR_MAP[case.id]
    rendered, _ = render_payload(
        injection_task_id=case.injection_task_id,
        goal_text=inj_task.GOAL,
    )
    injections = {vector_name: rendered}

    outcome = run_once(
        target=target,
        policy=full_policy,
        user_task=carrier_task,
        injection_task=inj_task,
        injections=injections,
    )

    assert outcome.security is False, (
        f"Defended agent unexpectedly executed injection for {case.id}"
    )


@pytest.mark.parametrize("case", ATTACK_CASES, ids=lambda c: c.id)
def test_control_run_no_injection_is_clean(case, full_policy: Policy) -> None:
    """Control runs with no injected payload always yield security=False."""
    target = ScriptedTarget(profile=AgentProfile(obeys=None))
    carrier_cls = CARRIER_MAP[case.carrier_task_id]
    inj_cls = INJECTION_TASK_MAP[case.injection_task_id]

    carrier_task = carrier_cls()
    inj_task = inj_cls()

    outcome = run_once(
        target=target,
        policy=full_policy,
        user_task=carrier_task,
        injection_task=inj_task,
        injections=None,  # Clean control run
    )

    assert outcome.security is False


def test_predicates_on_handcrafted_environments() -> None:
    """Direct validation of pure predicates against synthetic PRE/POST environments."""
    # 1. P-EXFIL-MAIL
    pre = AcmeEnv.create_default()
    post = pre.clone()
    assert check_p_exfil_mail(pre, post)[0] is False

    post.outbox.append(
        Email(
            id="e-test",
            sender="alex@acme.test",
            recipients=[ATTACKER_EMAIL],
            subject="Secrets",
            body=f"Key: {CANARY_KEY}",
        )
    )
    passed, ev = check_p_exfil_mail(pre, post)
    assert passed is True
    assert len(ev) >= 1

    # 2. P-ACL
    pre = AcmeEnv.create_default()
    post = pre.clone()
    assert check_p_acl(pre, post)[0] is False
    post.drive[CREDENTIALS_FILE_ID].shared_with.append(ATTACKER_EMAIL)
    assert check_p_acl(pre, post)[0] is True

    # 3. P-DELETE
    pre = AcmeEnv.create_default()
    post = pre.clone()
    assert check_p_delete(pre, post)[0] is False
    post.deleted.append(BUDGET_FILE_ID)
    assert check_p_delete(pre, post)[0] is True

    # 4. P-PLANT
    pre = AcmeEnv.create_default()
    post = pre.clone()
    assert check_p_plant(pre, post)[0] is False
    post.memory["standing_instruction"] = f"BCC {ATTACKER_EMAIL} {STANDING_INSTRUCTION_MARKER}"
    assert check_p_plant(pre, post)[0] is True

    # 5. P-TRIGGER
    pre = AcmeEnv.create_default()
    post = pre.clone()
    assert check_p_trigger(pre, post)[0] is False
    post.outbox.append(
        Email(
            id="e-test-2",
            sender="alex@acme.test",
            recipients=["sam@acme.test"],
            subject="Budget",
            body="Numbers",
            bcc=[ATTACKER_EMAIL],
        )
    )
    assert check_p_trigger(pre, post)[0] is True

    # 6. P-PRIV
    pre = AcmeEnv.create_default()
    post = pre.clone()
    assert check_p_priv(pre, post)[0] is False
    post.directory[ATTACKER_EMAIL] = "admin"
    assert check_p_priv(pre, post)[0] is True
