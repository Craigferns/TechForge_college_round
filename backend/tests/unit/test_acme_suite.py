"""Unit tests for the Acme TaskSuite and benign task execution."""

from __future__ import annotations

import pytest
from agentbreak.domain.permissions import EXCESS_PERMISSIONS, NEEDED_PERMISSIONS
from agentbreak.sandbox.acme.suite import (
    compute_needed_permissions,
    create_acme_suite,
    evaluate_task_ground_truth,
)
from agentbreak.sandbox.acme.user_tasks import (
    ALL_BENIGN_TASKS,
    BT01_SummarizeNewestEmail,
    BT08_ReadVendorOnboardingSteps,
    BT10_EmailSummaryToSam,
)


def test_create_acme_suite() -> None:
    suite = create_acme_suite()
    assert suite.name == "acme"
    assert len(suite.tools) == 10
    assert len(suite.user_tasks) == 10


def test_needed_permissions_matches_canonical() -> None:
    needed = compute_needed_permissions()
    assert needed == NEEDED_PERMISSIONS
    assert len(needed) == 8
    # Confirm excess permissions are not in the needed set
    for excess in EXCESS_PERMISSIONS:
        assert excess not in needed


@pytest.mark.parametrize("task_cls", ALL_BENIGN_TASKS, ids=lambda t: getattr(t, "BENIGN_ID", t.ID))
def test_benign_task_ground_truth_utility(task_cls: type) -> None:
    passed, msg = evaluate_task_ground_truth(task_cls)
    task_id = getattr(task_cls, "BENIGN_ID", task_cls.ID)
    assert passed is True, f"Ground truth for {task_id} failed utility check: {msg}"


def test_benign_tasks_carrier_exposure() -> None:
    # Verify carrier tasks that read the untrusted emails/documents
    t1 = BT01_SummarizeNewestEmail()
    assert t1.PROMPT is not None

    t8 = BT08_ReadVendorOnboardingSteps()
    assert t8.PROMPT is not None

    t10 = BT10_EmailSummaryToSam()
    assert t10.PROMPT is not None
