"""
Execute a shell command against a fresh copy of the eval fixture.

Backends:
  docker (default) - `docker run --network none --read-only` with only the copy
                     mounted. The copy is mounted at the SAME absolute path as
                     the pristine fixture, so commands that use the cwd shown to
                     the model in hai's context still work.
  local            - plain subprocess in the copy, with occurrences of the
                     pristine path rewritten to the copy. Only for throwaway
                     machines/CI; never point it at a real workstation.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fixture import GIT_ENV, copy

IMAGE = "hai-eval-sandbox:1"

# Never executed, whatever the backend.
NEVER_RUN = re.compile(
    r"\bsudo\b|\bmkfs|\bdd\s.*of=/dev/|/dev/(sd|nvme|hd|vd)|\bshutdown\b|\breboot\b"
    r"|:\(\)\s*\{|\brm\s+(-[a-zA-Z-]*\s+)*(/|~|\$HOME)(\*|\s|$)|\bkill(all)?\b|\bpkill\b"
    r"|\bchmod\s+-R\s+\S+\s+/(\s|$)|\bcurl\b|\bwget\b|\bssh\b|\bgit\s+push\b"
)


@dataclass
class Result:
    stdout: str
    stderr: str
    code: int
    skipped: str | None = None


class Sandbox:
    def __init__(
        self,
        pristine: Path,
        backend: str = "docker",
        timeout: int = 20,
        scratch: Path | None = None,
    ):
        self.pristine = pristine.resolve()
        self.backend = backend
        self.timeout = timeout
        self.scratch = Path(scratch or tempfile.mkdtemp(prefix="hai-eval-run-"))
        self.scratch.mkdir(parents=True, exist_ok=True)
        self._n = 0

    @staticmethod
    def build_image(context_dir: Path) -> None:
        subprocess.run(
            ["docker", "build", "-q", "-t", IMAGE, str(context_dir)],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    def run(self, command: str, post: str | None = None) -> tuple[Result, Result | None]:
        """Run ``command`` (and then ``post``) in one fresh copy."""
        if NEVER_RUN.search(command):
            r = Result("", "", -1, skipped="blocked by NEVER_RUN filter")
            return r, (Result("", "", -1, skipped="not run") if post else None)
        self._n += 1
        work = copy(self.pristine, self.scratch / f"c{self._n}" / "work")
        try:
            main = self._exec(command, work)
            after = self._exec(post, work) if post else None
            return main, after
        finally:
            subprocess.run(["rm", "-rf", str(work.parent)], check=False)

    def _exec(self, command: str, work: Path) -> Result:
        try:
            if self.backend == "docker":
                return self._docker(command, work)
            return self._local(command, work)
        except subprocess.TimeoutExpired:
            return Result("", "timeout", 124)

    def _docker(self, command: str, work: Path) -> Result:
        uid, gid = os.getuid(), os.getgid()
        args = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/home/evaluser",
            "--memory",
            "512m",
            "--pids-limit",
            "256",
            "--cpus",
            "1",
            "--user",
            f"{uid}:{gid}",
            "-e",
            "HOME=/home/evaluser",
            "-v",
            f"{work}:{self.pristine}",
            "-w",
            str(self.pristine),
        ]
        for k, v in GIT_ENV.items():
            args += ["-e", f"{k}={v}"]
        args += [IMAGE, "bash", "-c", command]
        p = subprocess.run(args, capture_output=True, text=True, timeout=self.timeout + 10)
        return Result(p.stdout, p.stderr, p.returncode)

    def _local(self, command: str, work: Path) -> Result:
        command = command.replace(str(self.pristine), str(work))
        env = dict(os.environ, HOME=str(work.parent / "home"), **GIT_ENV)
        (work.parent / "home").mkdir(exist_ok=True)
        p = subprocess.run(
            ["bash", "-c", command],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        # make outputs look like the docker backend (paths under pristine)
        out = p.stdout.replace(str(work), str(self.pristine))
        return Result(out, p.stderr, p.returncode)
