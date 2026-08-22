from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

from steadlith import __version__


def _run_version(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*command, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _installed_console_script() -> Path:
    executable = "steadlith.exe" if os.name == "nt" else "steadlith"
    candidates = [Path(sys.executable).parent / executable]
    scripts = sysconfig.get_path("scripts")
    if scripts:
        candidates.append(Path(scripts) / executable)
    user_scheme = sysconfig.get_preferred_scheme("user")
    user_scripts = sysconfig.get_path("scripts", scheme=user_scheme)
    if user_scripts:
        candidates.append(Path(user_scripts) / executable)
    discovered = shutil.which("steadlith")
    if discovered:
        candidates.append(Path(discovered))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise AssertionError("the installed steadlith console script was not found")


def test_python_module_entrypoint_reports_installed_version() -> None:
    result = _run_version([sys.executable, "-m", "steadlith"])

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"steadlith {__version__}"
    assert result.stderr == ""


def test_console_script_entrypoint_reports_installed_version() -> None:
    result = _run_version([str(_installed_console_script())])

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"steadlith {__version__}"
    assert result.stderr == ""
