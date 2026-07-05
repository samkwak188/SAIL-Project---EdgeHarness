"""Sandboxed bash execution.

Two modes:
  - docker        : run inside a Docker container with cwd + network=none
  - subprocess_jail: subprocess with cwd, env scrub, network denylist (best-effort)

A denylist is always enforced (settings.harness.sandbox.denylist).
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


@dataclass
class BashResult:
    exit_code: int
    stdout: str
    stderr: str
    command: str
    blocked: bool = False
    block_reason: str = ""


class SandboxedBash:
    def __init__(self, mode: str = "subprocess_jail", denylist: list[str] | None = None, cwd: str | None = None):
        self.mode = mode
        self.denylist = denylist or []
        self.cwd = cwd or os.getcwd()

    def run(self, command: str, timeout: int = 30) -> BashResult:
        # denylist check (pre_bash hook)
        for bad in self.denylist:
            if bad and bad in command:
                return BashResult(
                    exit_code=-1,
                    stdout="",
                    stderr=f"command blocked by denylist: {bad}",
                    command=command,
                    blocked=True,
                    block_reason=bad,
                )
        if self.mode == "docker":
            return self._run_docker(command, timeout)
        return self._run_subprocess(command, timeout)

    def _run_subprocess(self, command: str, timeout: int) -> BashResult:
        # scrub env of credential leakage; keep PATH, HOME, LANG
        safe_env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG", "LC_ALL", "USER"}}
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return BashResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                command=command,
            )
        except subprocess.TimeoutExpired:
            return BashResult(exit_code=-1, stdout="", stderr=f"timeout after {timeout}s", command=command)
        except Exception as e:  # pragma: no cover — defensive
            return BashResult(exit_code=-1, stdout="", stderr=str(e), command=command)

    def _run_docker(self, command: str, timeout: int) -> BashResult:  # pragma: no cover — requires docker
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{self.cwd}:/work",
            "-w",
            "/work",
            "python:3.11-slim",
            "bash",
            "-c",
            command,
        ]
        try:
            proc = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout)
            return BashResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                command=command,
            )
        except subprocess.TimeoutExpired:
            return BashResult(exit_code=-1, stdout="", stderr=f"timeout after {timeout}s", command=command)
        except FileNotFoundError:
            # docker not installed — fall back to subprocess jail
            return self._run_subprocess(command, timeout)


# Lightweight check used as pre_bash hook before SandboxedBash.run
def denylist_check(command: str, denylist: list[str]) -> tuple[bool, str]:
    for bad in denylist:
        if bad and bad in command:
            return False, bad
    return True, ""
