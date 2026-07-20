from pathlib import Path

import pytest

from beat_arc_agi_3.tools.run_python import (
    MAX_RUN_PYTHON_OUTPUT,
    RunPythonError,
    RunPythonQuery,
    execute_run_python,
)
from beat_arc_agi_3.workspace import SessionWorkspace


def test_run_python_analyzes_read_only_session_files(tmp_path: Path) -> None:
    (tmp_path / "evidence.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    workspace = SessionWorkspace(tmp_path)

    output = execute_run_python(
        workspace,
        RunPythonQuery(
            code=(
                "from pathlib import Path\n"
                "print(Path('evidence.txt').read_text().splitlines())\n"
            )
        ),
    )

    assert output == "STDOUT:\n['alpha', 'beta']"


def test_run_python_cannot_write_session_files(tmp_path: Path) -> None:
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(RunPythonError, match="Python exited with status"):
        execute_run_python(
            workspace,
            RunPythonQuery(
                code="open('created.txt', 'w').write('forbidden')",
            ),
        )

    assert not (tmp_path / "created.txt").exists()


def test_run_python_times_out(tmp_path: Path) -> None:
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(RunPythonError, match="timed out after 1s"):
        execute_run_python(
            workspace,
            RunPythonQuery(
                code="while True:\n    pass",
                timeout_seconds=1,
            ),
        )


def test_run_python_shares_one_output_bound_across_stdout_and_stderr(
    tmp_path: Path,
) -> None:
    workspace = SessionWorkspace(tmp_path)

    output = execute_run_python(
        workspace,
        RunPythonQuery(
            code=(
                "import sys\n"
                "print('o' * 30000)\n"
                "print('e' * 30000, file=sys.stderr)\n"
            )
        ),
    )

    assert len(output) <= MAX_RUN_PYTHON_OUTPUT
    assert "output capped at 50000 characters" in output
    assert output.startswith("STDOUT:\n")
    assert output.endswith("e" * 100)


def test_run_python_bounds_failure_diagnostics(tmp_path: Path) -> None:
    workspace = SessionWorkspace(tmp_path)

    with pytest.raises(RunPythonError) as exc_info:
        execute_run_python(
            workspace,
            RunPythonQuery(
                code=(
                    "import sys\n"
                    "print('e' * 60000, file=sys.stderr)\n"
                    "raise RuntimeError('boom')\n"
                )
            ),
        )

    message = str(exc_info.value)
    assert len(message) <= MAX_RUN_PYTHON_OUTPUT
    assert message.startswith("ERROR: Python exited with status 1.")
    assert "output capped at 50000 characters" in message
    assert message.endswith("RuntimeError: boom")
