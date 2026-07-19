import shutil
import sys
from pathlib import Path


class SandboxUnavailableError(RuntimeError):
    """Raised when the required generated-code sandbox is unavailable."""


def isolated_python_command(
    *,
    workspace_root: Path,
    python_arguments: list[str],
    read_only_paths: tuple[Path, ...] = (),
) -> list[str]:
    """Build a read-only, networkless bubblewrap Python command."""

    bubblewrap = shutil.which("bwrap")
    if bubblewrap is None:
        raise SandboxUnavailableError(
            "bubblewrap is required to execute generated Python"
        )
    workspace = workspace_root.resolve()
    if not workspace.is_dir():
        raise ValueError(f"workspace root is not a directory: {workspace}")

    interpreter = Path(sys.executable).resolve()
    runtime_root = interpreter.parents[1]
    environment_root = Path(sys.prefix).resolve()
    command = [
        bubblewrap,
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--clearenv",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        "/lib64",
        "/lib64",
        "--ro-bind",
        str(runtime_root),
        str(runtime_root),
        "--ro-bind",
        str(environment_root),
        str(environment_root),
        "--ro-bind",
        str(workspace),
        "/workspace",
    ]
    for path in read_only_paths:
        resolved = path.resolve()
        command.extend(["--ro-bind", str(resolved), str(resolved)])
    command.extend(
        [
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--setenv",
            "HOME",
            "/tmp",
            "--setenv",
            "PYTHONIOENCODING",
            "utf-8",
            "--setenv",
            "PYTHONDONTWRITEBYTECODE",
            "1",
            "--setenv",
            "OPENBLAS_NUM_THREADS",
            "1",
            "--chdir",
            "/workspace",
            str(interpreter),
            "-I",
            *python_arguments,
        ]
    )
    return command
