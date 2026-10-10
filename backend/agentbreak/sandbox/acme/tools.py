"""The 10 mock tools comprising the Acme Corporation benchmark environment."""

from __future__ import annotations

from typing import Annotated, Any

from agentdojo.functions_runtime import Depends, Function, make_function

from agentbreak.sandbox.acme.env import AcmeEnv
from agentbreak.sandbox.acme.models import Email

EnvDep = Annotated[AcmeEnv, Depends(lambda e: e)]


def list_inbox(env: EnvDep) -> list[dict[str, str]]:
    """List emails currently available in the user's inbox."""
    return [{"id": e.id, "sender": e.sender, "subject": e.subject} for e in env.inbox]


def read_email(email_id: str, env: EnvDep) -> dict[str, Any]:
    """Read the full content and metadata of a specific email by ID.

    :param email_id: The ID of the email to read.
    """
    for e in env.inbox:
        if e.id == email_id:
            return e.model_dump()
    return {"error": f"Email with id '{email_id}' not found."}


def send_email(
    to: list[str],
    subject: str,
    body: str,
    bcc: list[str] | None = None,
    env: EnvDep = ...,  # type: ignore[assignment]
) -> str:
    """Send an email to recipients with optional blind carbon copy.

    :param to: List of recipient email addresses.
    :param subject: The subject line of the email.
    :param body: The text body of the email.
    :param bcc: Optional list of blind carbon copy email addresses.
    """
    bcc_list = bcc if bcc is not None else []
    new_email = Email(
        id=f"e-out-{len(env.outbox) + 1}",
        sender="alex@acme.test",
        recipients=to,
        subject=subject,
        body=body,
        bcc=bcc_list,
    )
    env.outbox.append(new_email)
    return "Email sent successfully."


def list_files(env: EnvDep) -> list[dict[str, str]]:
    """List non-deleted files available in the user's Google Drive storage."""
    return [{"id": f.id, "name": f.name} for f in env.drive.values() if f.id not in env.deleted]


def read_file(file_id: str, env: EnvDep) -> str:
    """Read the complete content of a file in Drive by its ID.

    :param file_id: The ID of the file in Drive.
    """
    if file_id in env.deleted:
        return f"Error: File '{file_id}' has been deleted."
    if file_id in env.drive:
        return env.drive[file_id].content
    return f"Error: File '{file_id}' not found."


def share_file(file_id: str, principal: str, env: EnvDep) -> str:
    """Share a file with another user or external email address.

    :param file_id: The ID of the file to share.
    :param principal: The user or email to share the file with.
    """
    if file_id in env.deleted:
        return f"Error: Cannot share deleted file '{file_id}'."
    if file_id not in env.drive:
        return f"Error: File '{file_id}' not found."

    file_obj = env.drive[file_id]
    if principal not in file_obj.shared_with:
        file_obj.shared_with.append(principal)
    return f"File '{file_id}' successfully shared with '{principal}'."


def delete_file(file_id: str, env: EnvDep) -> str:
    """Delete a file from the user's Drive storage (tombstoned).

    :param file_id: The ID of the file to delete.
    """
    if file_id in env.deleted:
        return f"File '{file_id}' is already deleted."
    if file_id not in env.drive:
        return f"Error: File '{file_id}' does not exist."

    env.deleted.append(file_id)
    return f"File '{file_id}' successfully deleted."


def read_memory(env: EnvDep) -> dict[str, str]:
    """Read persistent notes and memory saved by the assistant."""
    return env.memory


def write_memory(key: str, value: str, env: EnvDep) -> str:
    """Save an instruction, preference, or fact to the assistant's persistent memory.

    :param key: The memory key or identifier.
    :param value: The content or value to store in memory.
    """
    env.memory[key] = value
    return f"Saved memory key '{key}'."


def set_role(principal: str, role: str, env: EnvDep) -> str:
    """Assign or modify the administrative role for a user directory entry.

    :param principal: The user or email address to update.
    :param role: The role to assign, such as 'admin' or 'member'.
    """
    env.directory[principal] = role
    return f"Assigned role '{role}' to principal '{principal}'."


ALL_ACME_FUNCTIONS = [
    list_inbox,
    read_email,
    send_email,
    list_files,
    read_file,
    share_file,
    delete_file,
    read_memory,
    write_memory,
    set_role,
]


def get_acme_tools() -> list[Function]:
    """Return the list of AgentDojo Function objects for all 10 Acme tools."""
    return [make_function(fn) for fn in ALL_ACME_FUNCTIONS]
