import subprocess

from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.sandbox import (
    SandboxUnavailableError,
    isolated_python_command,
)
from beat_arc_agi_3.workspace import SessionWorkspace


MAX_RUN_PYTHON_OUTPUT = 50_000


class RunPythonQuery(BaseModel):
    """Canonical request for isolated ad hoc Python analysis."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1)
    timeout_seconds: int = Field(default=10, ge=1, le=60)


class RunPythonError(RuntimeError):
    """Raised when isolated analytical Python cannot complete."""


def execute_run_python(
    workspace: SessionWorkspace,
    query: RunPythonQuery,
) -> str:
    try:
        command = isolated_python_command(
            workspace_root=workspace.root,
            python_arguments=["-c", query.code],
        )
    except SandboxUnavailableError as exc:
        raise RunPythonError(f"ERROR: {exc}") from exc

    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=query.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RunPythonError(
            f"ERROR: Python timed out after {query.timeout_seconds}s."
        ) from exc

    stdout = _cap(completed.stdout.rstrip())
    stderr = _cap(completed.stderr.rstrip())
    if completed.returncode != 0:
        diagnostic = stderr or stdout or "(no diagnostic output)"
        raise RunPythonError(
            f"ERROR: Python exited with status {completed.returncode}.\n"
            f"{diagnostic}"
        )

    sections: list[str] = []
    if stdout:
        sections.append(f"STDOUT:\n{stdout}")
    if stderr:
        sections.append(f"STDERR:\n{stderr}")
    return "\n".join(sections) if sections else "Python completed with no output."


def _cap(output: str) -> str:
    if len(output) <= MAX_RUN_PYTHON_OUTPUT:
        return output
    return (
        output[:MAX_RUN_PYTHON_OUTPUT]
        + f"\n... output capped at {MAX_RUN_PYTHON_OUTPUT} characters"
    )
