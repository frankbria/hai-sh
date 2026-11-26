"""
Build the deterministic sandbox project that every eval case runs against.

The same tree is used three ways:
  1. hai's real context collector reads it (cwd, git state, file listing),
     so the model sees what a user in that directory would see;
  2. the reference command for each case runs in a fresh copy of it;
  3. the model's command runs in another fresh copy, and the two results
     are compared (see score.py).

Everything is fixed: file contents, sizes, git authors/dates and mtimes
(old files are dated 2020-01-01, a few are touched "1 hour ago" so that
"modified today" questions have a definite answer).
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Eval User",
    "GIT_AUTHOR_EMAIL": "eval@example.invalid",
    "GIT_COMMITTER_NAME": "Eval User",
    "GIT_COMMITTER_EMAIL": "eval@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
}

OLD = time.mktime((2020, 1, 1, 12, 0, 0, 0, 0, -1))

APP_LOG_LEVELS = ["INFO"] * 20 + ["WARN"] * 6 + ["ERROR"] * 4


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _git(work: Path, *args: str, date: str | None = None) -> None:
    env = dict(os.environ, **GIT_ENV)
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(
        ["git", *args],
        cwd=work,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build(work: Path) -> Path:
    """Create the sandbox project at ``work`` (removed first if present)."""
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    rnd = random.Random(1234)

    _w(
        work / "README.md",
        "# Demo Project\n\nA small demo project used by the hai eval.\n"
        "Run scripts/build.sh to build it.\nSee docs/guide.md for details.\n",
    )
    _w(
        work / "notes.txt",
        "meeting notes\nTODO: update the guide\nthe build is slow\n"
        "TODO: fix the login bug\nthe docs are out of date\n"
        "the login page is slow\nTODO: add more coverage\nthe end\n",
    )
    lines = []
    for i, lvl in enumerate(rnd.sample(APP_LOG_LEVELS, len(APP_LOG_LEVELS))):
        lines.append(
            f"2026-11-20 10:{i:02d}:00 {lvl} worker-{i % 3} "
            f"{'request failed' if lvl == 'ERROR' else 'request ok'}"
        )
    _w(work / "app.log", "\n".join(lines) + "\n")
    ips = [
        "10.0.0.1",
        "10.0.0.2",
        "10.0.0.3",
        "192.168.1.5",
        "192.168.1.9",
        "172.16.0.4",
        "10.0.0.1",
        "10.0.0.2",
        "10.0.0.1",
    ]
    _w(
        work / "access.log",
        "".join(
            f'{ip} - - [20/Nov/2026:10:{i:02d}:00] "GET /page{i} HTTP/1.1" 200 512\n'
            for i, ip in enumerate(ips)
        ),
    )
    _w(
        work / "data.csv",
        "name,age,city\nalice,34,Phoenix\nbob,27,Denver\ncarol,45,Austin\n"
        "dave,19,Boston\nerin,52,Seattle\nfrank,31,Phoenix\ngrace,38,Denver\n"
        "heidi,23,Austin\n",
    )
    _w(
        work / "config.json",
        '{\n  "name": "foo",\n  "mode": "dev",\n  "backend": "foo-server",\n' '  "port": 8080\n}\n',
    )
    _w(
        work / "src/main.py",
        "import os\nimport sys\n\n# TODO: handle errors\n\ndef main():\n"
        "    print(os.getcwd())\n\n\nif __name__ == '__main__':\n    main()\n",
    )
    _w(
        work / "src/utils.py",
        "import json\n\n# TODO: add caching\n\ndef helper(x):\n    return x * 2\n",
    )
    _w(work / "src/old_module.py", "import os\n\ndef legacy():\n    return 1\n")
    _w(work / "src/__pycache__/main.cpython-312.pyc", "fake bytecode\n")
    _w(work / "src/__pycache__/utils.cpython-312.pyc", "fake bytecode\n")
    _w(
        work / "tests/test_main.py",
        "from src.utils import helper\n\ndef test_helper():\n" "    assert helper(2) == 4\n",
    )
    _w(work / "docs/guide.md", "# Guide\n\nHow to use the demo.\n")
    _w(work / "docs/api.md", "# API\n\nmain() prints the cwd.\n")
    _w(work / "scripts/build.sh", "#!/bin/bash\necho building\n")
    _w(work / "scripts/deploy.sh", "#!/bin/bash\necho deploying\n")
    os.chmod(work / "scripts/build.sh", 0o644)
    os.chmod(work / "scripts/deploy.sh", 0o755)
    _w(work / "tmp/cache1.tmp", "cache\n")
    _w(work / "tmp/cache2.tmp", "cache\n")
    _w(work / ".hidden_config", "secret_mode=false\n")
    _w(work / ".gitignore", "*.bin\ntmp/\n__pycache__/\n*.tar.gz\n")
    (work / "empty.txt").write_text("")
    (work / "photos").mkdir()
    for name, size in (("a.jpg", 2048), ("b.jpg", 4096), ("c.png", 1024)):
        (work / "photos" / name).write_bytes(rnd.randbytes(size))
    for name, size in (
        ("big.bin", 3 * 1024 * 1024),
        ("medium.bin", 1536 * 1024),
        ("small.bin", 600 * 1024),
    ):
        (work / name).write_bytes(rnd.randbytes(size))

    # archive.tar.gz containing two small files (not in the tree itself)
    stage = work.parent / "_archive_stage"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    (stage / "a.txt").write_text("alpha\n")
    (stage / "b.txt").write_text("beta\n")
    with tarfile.open(work / "archive.tar.gz", "w:gz") as tar:
        tar.add(stage / "a.txt", arcname="a.txt")
        tar.add(stage / "b.txt", arcname="b.txt")
    shutil.rmtree(stage)

    # git history: 3 commits on main, 1 on feature/login, then local edits
    _git(work, "init", "-q", "-b", "main")
    _git(work, "add", "README.md", ".gitignore", "notes.txt")
    _git(work, "commit", "-q", "-m", "Initial commit", date="2026-11-01T09:00:00")
    _git(work, "add", "src", "tests", "docs", "scripts")
    _git(work, "commit", "-q", "-m", "Add source and tests", date="2026-11-02T09:00:00")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "Add data and logs", date="2026-11-03T09:00:00")
    _git(work, "checkout", "-q", "-b", "feature/login")
    _w(work / "src/login.py", "def login(user):\n    return True\n")
    _git(work, "add", "src/login.py")
    _git(work, "commit", "-q", "-m", "Add login stub", date="2026-11-04T09:00:00")
    _git(work, "checkout", "-q", "main")
    with open(work / "README.md", "a") as fh:
        fh.write("Work in progress.\n")
    _w(work / "new_feature.py", "def feature():\n    pass\n")

    # mtimes: everything old, then a few files touched an hour ago
    for root, dirs, files in os.walk(work):
        if ".git" in Path(root).parts:
            continue
        for name in files + dirs:
            p = Path(root) / name
            if ".git" in p.parts:
                continue
            os.utime(p, (OLD, OLD), follow_symlinks=False)
    recent = time.time() - 3600
    for rel in ("src/main.py", "notes.txt", "app.log", "README.md", "new_feature.py"):
        os.utime(work / rel, (recent, recent))
    return work


def copy(pristine: Path, dest: Path) -> Path:
    """Fresh copy of the fixture (keeps mtimes and modes)."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(pristine, dest, symlinks=True)
    return dest


if __name__ == "__main__":
    import sys

    print(build(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/hai-eval/work")))
