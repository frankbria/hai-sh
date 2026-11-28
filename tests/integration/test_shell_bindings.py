"""
Run the real Ctrl+X Ctrl+H binding functions from bash_integration.sh and
zsh_integration.sh against a fake Ollama, the way a user's shell does.

Without gum the bindings capture `hai --suggest-only` stdout and stderr
together and parse that as JSON, so anything extra hai prints breaks every
query. These tests catch that, and check the missing-model answer reaches the
user as text with an empty command line.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fake_ollama import FakeOllama

INTEGRATIONS = Path(__file__).resolve().parents[2] / "hai_sh" / "integrations"
SHELLS = ["bash", "zsh"]

pytestmark = pytest.mark.integration


def shell_script(shell: str, line: str) -> str:
    quoted = line.replace("'", "'\\''")
    if shell == "bash":
        return (
            f"source {INTEGRATIONS / 'bash_integration.sh'} 2>/dev/null\n"
            f"READLINE_LINE='{quoted}'; READLINE_POINT=${{#READLINE_LINE}}\n"
            "_hai_trigger; rc=$?\n"
            'printf "\\n<<RC=%s>>\\n<<LINE=%s>>\\n" "$rc" "$READLINE_LINE"\n'
        )
    # zsh: the widget needs ZLE only for zle/bindkey; stub them.
    return (
        "zle() { :; }; bindkey() { :; }\n"
        f"source {INTEGRATIONS / 'zsh_integration.sh'}\n"
        f"BUFFER='{quoted}'; CURSOR=${{#BUFFER}}\n"
        "_hai_trigger_widget; rc=$?\n"
        'printf "\\n<<RC=%s>>\\n<<LINE=%s>>\\n" "$rc" "$BUFFER"\n'
    )


@pytest.fixture
def fake():
    server = FakeOllama().start()
    yield server
    server.stop()


@pytest.fixture
def env(tmp_path, fake):
    """A HOME with a config pointing at the fake, and PATH with hai but no gum."""
    home = tmp_path / "home"
    (home / ".hai").mkdir(parents=True)
    (home / ".hai" / "config.yaml").write_text(
        "provider: ollama\n"
        "providers:\n"
        "  ollama:\n"
        f'    base_url: "{fake.url}"\n'
        '    model: "gemma4:e2b"\n'
    )
    bindir = tmp_path / "bin"
    bindir.mkdir()
    hai = bindir / "hai"
    repo = Path(__file__).resolve().parents[2]
    hai.write_text(f'#!/bin/sh\ncd "{repo}" && exec "{sys.executable}" -m hai_sh "$@"\n')
    hai.chmod(0o755)
    path_dirs = [str(bindir)] + [
        d for d in ("/usr/local/bin", "/usr/bin", "/bin") if os.path.isdir(d)
    ]
    e = {
        "HOME": str(home),
        "PATH": os.pathsep.join(path_dirs),
        "HAI_QUIET": "1",
        "HAI_TESTING": "1",
        "NO_COLOR": "1",
        "TERM": "dumb",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    return e


def run_binding(shell: str, line: str, env: dict):
    exe = shutil.which(shell)
    if exe is None:
        pytest.skip(f"{shell} is not installed")
    if any(shutil.which("gum", path=d) for d in env["PATH"].split(os.pathsep)):
        pytest.skip("gum is on PATH; this test covers the no-gum path")
    args = [exe, "--norc", "--noprofile"] if shell == "bash" else [exe, "-f"]
    proc = subprocess.run(
        args,
        input=shell_script(shell, line),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    out = proc.stdout
    rc = out.rsplit("<<RC=", 1)[1].split(">>", 1)[0]
    new_line = out.rsplit("<<LINE=", 1)[1].split(">>", 1)[0]
    return out, rc, new_line


@pytest.mark.parametrize("shell", SHELLS)
def test_command_lands_on_the_prompt(shell, fake, env):
    fake.installed["gemma4:e2b"] = 1
    out, rc, line = run_binding(shell, "@hai list the files", env)
    assert "Error parsing response" not in out, out
    assert rc == "0", out
    assert line == "\\ls", out  # the bindings escape aliases with a backslash
    assert "Lists the files." in out


@pytest.mark.parametrize("shell", SHELLS)
def test_missing_model_says_what_to_run(shell, fake, env):
    out, rc, line = run_binding(shell, "@hai list the files", env)
    assert "Error parsing response" not in out, out
    assert rc == "0", out
    assert line == "", out  # nothing put on the prompt to run
    assert "hai-model pull gemma4:e2b" in out
    assert fake.pull_requests == []


@pytest.mark.parametrize("shell", SHELLS)
def test_ollama_down_says_what_to_run(shell, env):
    cfg = Path(env["HOME"]) / ".hai" / "config.yaml"
    cfg.write_text("provider: ollama\nproviders:\n  ollama:\n    base_url: http://127.0.0.1:9\n")
    out, rc, line = run_binding(shell, "@hai list the files", env)
    assert "Error parsing response" not in out, out
    assert rc == "0", out
    assert line == ""
    assert "Ollama" in out
