"""Unit tests for Acme sandbox environment, tools, and fake data linting."""

import pytest
from agentbreak.sandbox.acme.env import AcmeEnv
from agentbreak.sandbox.acme.models import Email
from agentbreak.sandbox.acme.tools import (
    delete_file,
    list_files,
    list_inbox,
    read_email,
    read_file,
    read_memory,
    send_email,
    set_role,
    share_file,
    write_memory,
)

from scripts.lint_fake_data import lint_environment


@pytest.fixture
def env():
    return AcmeEnv.create_default()


def test_list_and_read_inbox(env):
    """Test listing and reading emails in inbox."""
    inbox = list_inbox(env=env)
    assert len(inbox) == 3
    assert inbox[0]["id"] == "e-1001"

    email = read_email("e-1001", env=env)
    assert email["subject"] == "Thursday sync"
    assert "Thursday at 10am" in email["body"]


def test_send_email_appends_to_outbox(env):
    """Test send_email appends to outbox with correct recipients and sender."""
    assert len(env.outbox) == 0
    res = send_email(to=["sam@acme.test"], subject="Status Update", body="All good.", env=env)
    assert res == "Email sent successfully."
    assert len(env.outbox) == 1
    assert env.outbox[0].sender == "alex@acme.test"
    assert env.outbox[0].recipients == ["sam@acme.test"]


def test_file_operations_and_tombstoning(env):
    """Test read_file, share_file deduplication, and delete_file tombstoning."""
    # Read file
    content = read_file("f-001", env=env)
    assert "1,284,300" in content

    # Share file (adds principal and deduplicates)
    res = share_file("f-001", "kim@acme.test", env=env)
    assert "successfully shared" in res
    assert "kim@acme.test" in env.drive["f-001"].shared_with

    # Share same principal again (should deduplicate)
    share_file("f-001", "kim@acme.test", env=env)
    assert env.drive["f-001"].shared_with.count("kim@acme.test") == 1

    # Delete file
    del_res = delete_file("f-001", env=env)
    assert "successfully deleted" in del_res
    assert "f-001" in env.deleted

    # After deletion, list_files omits it and read_file returns error
    remaining_files = list_files(env=env)
    assert all(f["id"] != "f-001" for f in remaining_files)
    read_deleted = read_file("f-001", env=env)
    assert "deleted" in read_deleted.lower()


def test_memory_tools(env):
    """Test read_memory and write_memory."""
    assert len(read_memory(env=env)) == 0
    write_memory("preference", "morning meetings", env=env)
    mem = read_memory(env=env)
    assert mem["preference"] == "morning meetings"


def test_set_role(env):
    """Test set_role adds or updates directory entries."""
    assert "mallory@evil.test" not in env.directory
    set_role("mallory@evil.test", "admin", env=env)
    assert env.directory["mallory@evil.test"] == "admin"


def test_fake_data_linter_clean(env):
    """Test that default AcmeEnv produces zero fake data violations."""
    violations = lint_environment(env)
    assert violations == []


def test_fake_data_linter_catches_violations():
    """Test that bad planted fixtures are caught by the linter."""
    bad_env = AcmeEnv.create_default()
    # Plant a real domain (.com instead of .test)
    bad_env.inbox.append(
        Email(
            id="bad-1",
            sender="attacker@evil.com",
            recipients=["alex@acme.test"],
            subject="Spam",
            body="Click here",
        )
    )
    violations = lint_environment(bad_env)
    assert len(violations) > 0
    assert any("evil.com" in v for v in violations)
