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
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

from fixture import GIT_ENV, copy

IMAGE = "hai-eval-sandbox:1"

# Most bytes kept from a command's stdout / stderr. The rest is read and
# dropped, so a command that floods its output cannot exhaust host memory.
MAX_STDOUT = 1 << 20
MAX_STDERR = 64 << 10

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
        if backend == "local" and os.environ.get("HAI_EVAL_ALLOW_LOCAL") != "1":
            raise RuntimeError(
                "The local backend runs model-written commands on this machine "
                "with no isolation. Set HAI_EVAL_ALLOW_LOCAL=1 only on a throwaway "
                "machine or CI runner."
            )
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
        name = f"hai-eval-{uuid.uuid4().hex[:12]}"
        args = [
            "docker",
            "run",
            "--rm",
            "--name",
            name,
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

        def stop_container() -> None:
            # Killing the docker client leaves the container running; stop it.
            subprocess.run(
                ["docker", "kill", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

        out, err, code = run_capped(args, self.timeout + 10, on_timeout=stop_container)
        return Result(out, err, code)

    def _local(self, command: str, work: Path) -> Result:
        command = command.replace(str(self.pristine), str(work))
        # Only what the commands need, so nothing in the caller's environment
        # (API keys, tokens, cloud credentials) is visible to them.
        env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(work.parent / "home"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            **GIT_ENV,
        }
        (work.parent / "home").mkdir(exist_ok=True)
        out, err, code = run_capped(["bash", "-c", command], self.timeout, cwd=work, env=env)
        # make outputs look like the docker backend (paths under pristine)
        out = out.replace(str(work), str(self.pristine))
        return Result(out, err, code)


def _drain(stream, limit: int, sink: list) -> None:
    kept = 0
    while True:
        chunk = stream.read(65536)
        if not chunk:
            break
        if kept < limit:
            sink.append(chunk[: limit - kept])
            kept += len(sink[-1])
    stream.close()


def run_capped(args, timeout, cwd=None, env=None, on_timeout=None) -> tuple[str, str, int]:
    """subprocess.run with bounded output buffering.

    Keeps at most MAX_STDOUT / MAX_STDERR bytes of each stream. Raises
    subprocess.TimeoutExpired after killing the process (and calling
    ``on_timeout``, e.g. to stop a container) if it runs past ``timeout``.
    """
    p = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out: list[bytes] = []
    err: list[bytes] = []
    readers = [
        threading.Thread(target=_drain, args=(p.stdout, MAX_STDOUT, out), daemon=True),
        threading.Thread(target=_drain, args=(p.stderr, MAX_STDERR, err), daemon=True),
    ]
    for t in readers:
        t.start()
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if on_timeout:
            on_timeout()
        p.kill()
        p.wait()
        for t in readers:
            t.join(timeout=5)
        raise
    for t in readers:
        t.join()
    dec = lambda parts: b"".join(parts).decode("utf-8", errors="replace")  # noqa: E731
    return dec(out), dec(err), p.returncode
