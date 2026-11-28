"""Tests for the hai-model command."""

import builtins

import pytest
import yaml

from hai_sh import model_cli
from tests.fake_ollama import FakeOllama


@pytest.fixture
def fake():
    server = FakeOllama().start()
    yield server
    server.stop()


@pytest.fixture
def cfg(tmp_path, fake, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p = tmp_path / "config.yaml"
    p.write_text(
        "provider: ollama\n"
        "providers:\n"
        "  ollama:\n"
        f'    base_url: "{fake.url}"\n'
        '    model: "gemma4:e2b"  # my comment\n'
    )
    return p


@pytest.fixture(autouse=True)
def roomy_machine(monkeypatch):
    """Plenty of disk and memory unless a test says otherwise."""
    monkeypatch.setattr(model_cli.m, "disk_space", lambda p: (500 * 10**9, 1000 * 10**9))
    monkeypatch.setattr(model_cli.m, "total_ram", lambda: 32 * 10**9)


def run(cfg, *argv):
    return model_cli.main(["--config", str(cfg), *argv])


def answers(monkeypatch, *replies):
    it = iter(replies)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(it))
    monkeypatch.setattr(model_cli, "is_interactive", lambda: True)


def no_terminal(monkeypatch):
    monkeypatch.setattr(model_cli, "is_interactive", lambda: False)

    def boom(prompt=""):
        raise AssertionError("prompted without a terminal")

    monkeypatch.setattr(builtins, "input", boom)


class TestAsk:
    def test_enter_takes_the_default(self, monkeypatch):
        monkeypatch.setattr(builtins, "input", lambda p="": "")
        assert model_cli.ask("?", "yN") == "n"
        assert model_cli.ask("?", "yNo") == "n"

    def test_letters_and_words(self, monkeypatch):
        replies = iter(["y", "YES", "o", "no"])
        monkeypatch.setattr(builtins, "input", lambda p="": next(replies))
        assert [model_cli.ask("?", "yNo") for _ in range(4)] == ["y", "y", "o", "n"]

    def test_reasks_on_nonsense(self, monkeypatch, capsys):
        replies = iter(["maybe", "y"])
        monkeypatch.setattr(builtins, "input", lambda p="": next(replies))
        assert model_cli.ask("?", "yN") == "y"
        assert "Please answer" in capsys.readouterr().out

    def test_eof_is_no(self, monkeypatch):
        def eof(p=""):
            raise EOFError

        monkeypatch.setattr(builtins, "input", eof)
        assert model_cli.ask("?", "yN") == "n"


class TestStatus:
    def test_ready(self, cfg, fake, capsys):
        fake.installed["gemma4:e2b"] = 1
        assert run(cfg, "status") == 0
        out = capsys.readouterr().out
        assert "running (0.0.0-fake)" in out
        assert "gemma4:e2b  (installed)" in out
        assert "Licence: Apache 2.0" in out

    def test_model_missing(self, cfg, capsys):
        assert run(cfg, "status") == 1
        out = capsys.readouterr().out
        assert "NOT installed" in out
        assert f"hai-model --config {cfg} pull gemma4:e2b" in out  # same config file

    def test_ollama_down_prints_start_or_install_hint(self, cfg, capsys, monkeypatch):
        cfg.write_text("providers:\n  ollama:\n    base_url: http://127.0.0.1:9\n")
        monkeypatch.setattr(model_cli.m.shutil, "which", lambda name: None)
        assert run(cfg, "status") == 1
        out = capsys.readouterr().out
        assert "not reachable" in out
        assert (
            "curl -fsSL https://ollama.com/install.sh | sh" in out or "ollama.com/download" in out
        )

    def test_llama32_user_sees_the_switch_command(self, cfg, fake, capsys):
        cfg.write_text(f'providers:\n  ollama:\n    base_url: "{fake.url}"\n    model: llama3.2\n')
        fake.installed["llama3.2:latest"] = 1
        assert run(cfg, "status") == 0
        assert "hai-model use gemma4:e2b" in capsys.readouterr().out


class TestList:
    def test_lists_recommended_and_installed(self, cfg, fake, capsys):
        fake.installed["gemma4:e2b"] = 4587156505
        fake.installed["mistral:latest"] = 4000000000
        assert run(cfg, "list") == 0
        out = capsys.readouterr().out
        assert "qwen2.5-coder:3b" in out and "phi4-mini" in out
        assert "* gemma4:e2b" in out
        assert "mistral:latest" in out and "untested with hai" in out

    def test_commercial_policy_hides_qwen(self, cfg, capsys):
        cfg.write_text(cfg.read_text() + "models:\n  licence_policy: commercial\n")
        run(cfg, "list")
        out = capsys.readouterr().out
        recommended = out.split("Not shown")[0]
        assert "qwen2.5-coder:3b" not in recommended
        assert "Not shown under the commercial policy: qwen2.5-coder:3b" in out

    def test_nothing_installed(self, cfg, capsys):
        assert run(cfg, "list") == 0
        assert "Installed: none yet" in capsys.readouterr().out

    def test_ollama_down(self, cfg, capsys):
        cfg.write_text("providers:\n  ollama:\n    base_url: http://127.0.0.1:9\n")
        assert run(cfg, "list") == 1
        assert "Installed: unknown" in capsys.readouterr().out


class TestPull:
    def test_shows_facts_and_default_is_no(self, cfg, fake, monkeypatch, capsys):
        fake.pullable.add("gemma4:e2b")
        answers(monkeypatch, "")
        assert run(cfg, "pull", "gemma4:e2b") == 1
        out = capsys.readouterr().out
        assert "Download: 4.6 GB" in out and "Licence:  Apache 2.0" in out
        assert "Nothing downloaded" in out
        assert fake.pull_requests == []

    def test_yes_downloads(self, cfg, fake, monkeypatch, capsys):
        fake.pullable.add("phi4-mini")
        answers(monkeypatch, "y")
        assert run(cfg, "pull", "phi4-mini") == 0
        assert "phi4-mini:latest" in fake.installed
        assert "is installed" in capsys.readouterr().err

    def test_non_commercial_licence_is_shown_plainly(self, cfg, fake, monkeypatch, capsys):
        answers(monkeypatch, "n")
        run(cfg, "pull", "qwen2.5-coder:3b")
        assert "Qwen Research, non-commercial use only" in capsys.readouterr().out

    def test_no_terminal_never_prompts(self, cfg, fake, monkeypatch, capsys):
        fake.pullable.add("phi4-mini")
        no_terminal(monkeypatch)
        assert run(cfg, "pull", "phi4-mini") == 1
        assert f"hai-model --config {cfg} pull phi4-mini --yes" in capsys.readouterr().out
        assert fake.pull_requests == []

    def test_yes_flag_without_terminal(self, cfg, fake, monkeypatch, capsys):
        fake.pullable.add("phi4-mini")
        no_terminal(monkeypatch)
        assert run(cfg, "pull", "phi4-mini", "--yes") == 0
        assert "phi4-mini:latest" in fake.installed
        err = capsys.readouterr().err
        assert "100%" in err  # plain progress lines when not a terminal

    def test_already_installed(self, cfg, fake, capsys):
        fake.installed["phi4-mini:latest"] = 1
        assert run(cfg, "pull", "phi4-mini") == 0
        assert "already installed" in capsys.readouterr().out

    def test_uncatalogued_model_says_size_unknown(self, cfg, fake, monkeypatch, capsys):
        answers(monkeypatch, "n")
        run(cfg, "pull", "mistral")
        out = capsys.readouterr().out
        assert "unknown until the download starts" in out and "not tested with hai" in out

    def test_low_disk_stops_unless_forced(self, cfg, fake, monkeypatch, capsys):
        fake.pullable.add("gemma4:e2b")
        monkeypatch.setattr(model_cli.m, "disk_space", lambda p: (3 * 10**9, 100 * 10**9))
        no_terminal(monkeypatch)
        assert run(cfg, "pull", "gemma4:e2b", "--yes") == 1
        assert "Not enough disk space" in capsys.readouterr().out
        assert fake.pull_requests == []
        assert run(cfg, "pull", "gemma4:e2b", "--yes", "--force") == 0

    def test_failed_download(self, cfg, fake, monkeypatch, capsys):
        no_terminal(monkeypatch)
        assert run(cfg, "pull", "no-such-model", "--yes") == 1
        assert "Download failed" in capsys.readouterr().err

    def test_ollama_down(self, cfg, capsys):
        cfg.write_text("providers:\n  ollama:\n    base_url: http://127.0.0.1:9\n")
        assert run(cfg, "pull", "phi4-mini") == 1
        assert "Ollama" in capsys.readouterr().err


class TestUse:
    def test_switches_installed_model_and_keeps_comment(self, cfg, fake, capsys):
        fake.installed["phi4-mini:latest"] = 1
        assert run(cfg, "use", "phi4-mini") == 0
        assert "gemma4:e2b -> phi4-mini" in capsys.readouterr().out
        text = cfg.read_text()
        assert 'model: "phi4-mini"  # my comment' in text
        assert (cfg.parent / "config.yaml.bak").exists()

    def test_offers_download_and_leaves_config_on_no(self, cfg, fake, monkeypatch, capsys):
        before = cfg.read_text()
        answers(monkeypatch, "n")
        assert run(cfg, "use", "phi4-mini") == 1
        assert cfg.read_text() == before
        assert "--no-pull" in capsys.readouterr().out

    def test_downloads_then_switches(self, cfg, fake, monkeypatch):
        fake.pullable.add("phi4-mini")
        answers(monkeypatch, "y")
        assert run(cfg, "use", "phi4-mini") == 0
        assert yaml.safe_load(cfg.read_text())["providers"]["ollama"]["model"] == "phi4-mini"

    def test_no_pull_sets_it_anyway(self, cfg, capsys):
        cfg.write_text("providers:\n  ollama:\n    base_url: http://127.0.0.1:9\n    model: x\n")
        assert run(cfg, "use", "mistral", "--no-pull") == 0
        out = capsys.readouterr().out
        assert "untested with hai" in out
        assert yaml.safe_load(cfg.read_text())["providers"]["ollama"]["model"] == "mistral"

    def test_ollama_down_does_not_change_config(self, cfg, capsys):
        cfg.write_text("providers:\n  ollama:\n    base_url: http://127.0.0.1:9\n    model: x\n")
        assert run(cfg, "use", "phi4-mini") == 1
        assert "model: x" in cfg.read_text()

    def test_policy_note(self, cfg, fake, capsys):
        cfg.write_text(cfg.read_text() + "models:\n  licence_policy: commercial\n")
        fake.installed["qwen2.5-coder:3b"] = 1
        assert run(cfg, "use", "qwen2.5-coder:3b") == 0
        assert "not recommended under your licence policy" in capsys.readouterr().out


def test_no_command_prints_help(capsys):
    assert model_cli.main([]) == 0
    assert "hai-model" in capsys.readouterr().out


def test_entry_point_is_declared():
    from pathlib import Path

    text = Path(__file__).resolve().parents[2].joinpath("pyproject.toml").read_text()
    assert 'hai-model = "hai_sh.model_cli:main"' in text
    assert '"data/*.yaml"' in text


def test_missing_config_file_uses_defaults_not_the_home_config(tmp_path, fake, monkeypatch, capsys):
    """--config remote.yaml that doesn't exist must not fall back to ~/.hai/config.yaml."""
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".hai").mkdir()
    (tmp_path / ".hai" / "config.yaml").write_text(
        f'providers:\n  ollama:\n    base_url: "{fake.url}"\n    model: other\n'
    )
    run(tmp_path / "remote.yaml", "status")
    out = capsys.readouterr().out
    assert fake.url not in out
    assert "localhost:11434" in out


@pytest.mark.parametrize(
    "text", ["providers:\n  ollama:\n    base_url: [unclosed\n", "- not\n- a mapping\n"]
)
def test_broken_existing_config_stops_instead_of_using_defaults(tmp_path, fake, capsys, text):
    """A --config file that exists but can't be parsed must not mean localhost's Ollama."""
    cfg = tmp_path / "remote.yaml"
    cfg.write_text(text)
    fake.pullable.add("phi4-mini")
    with pytest.raises(SystemExit) as exc:
        run(cfg, "pull", "phi4-mini", "--yes")
    assert exc.value.code == 1
    assert "Cannot read config" in capsys.readouterr().err
    assert cfg.read_text() == text


class TestSixthReviewFixes:
    def test_ollama_down_hint_keeps_the_config_path(self, tmp_path, capsys):
        cfg = tmp_path / "team.yaml"
        cfg.write_text("providers:\n  ollama:\n    base_url: http://127.0.0.1:9\n    model: x\n")
        assert run(cfg, "use", "phi4-mini") == 1
        assert f"hai-model --config {cfg} use phi4-mini --no-pull" in capsys.readouterr().err

    def test_model_name_is_shell_quoted_in_hints(self):
        from hai_sh import model_flow

        hint = model_flow.missing_model_hint("x; rm -rf ~")
        assert "pull 'x; rm -rf ~'" in hint
        assert "pull gemma4:e2b" in model_flow.missing_model_hint("gemma4:e2b")


@pytest.mark.parametrize("cmd", [["use", "  ", "--no-pull"], ["pull", ""]])
def test_empty_model_name_is_refused(cfg, capsys, cmd):
    before = cfg.read_text()
    assert run(cfg, *cmd) == 2
    assert "Give a model name" in capsys.readouterr().err
    assert cfg.read_text() == before


class TestSeventhReviewFixes:
    @pytest.mark.parametrize("text", ["providers:\n  ollama: disabled\n", "providers: [a]\n"])
    def test_odd_ollama_section_stops_cleanly(self, tmp_path, capsys, text):
        cfg = tmp_path / "c.yaml"
        cfg.write_text(text)
        with pytest.raises(SystemExit) as exc:
            run(cfg, "status")
        assert exc.value.code == 1
        assert "Cannot read config" in capsys.readouterr().err

    def test_odd_details_and_counters_from_ollama(self, monkeypatch):
        import requests

        class Tags:
            status_code = 200

            def json(self):
                return {"models": [{"name": "a", "size": 1, "details": "unknown"}]}

            def raise_for_status(self):
                pass

        monkeypatch.setattr(requests, "get", lambda *a, **k: Tags())
        assert [x.name for x in model_cli.m.list_installed("http://x")] == ["a"]

        class Pull:
            status_code = 200

            def iter_lines(self):
                yield b'{"status": "pulling", "digest": "d", "total": "lots"}'
                yield b'{"status": "success"}'

            def close(self):
                pass

        monkeypatch.setattr(requests, "post", lambda *a, **k: Pull())
        model_cli.m.pull_model("http://x", "a")  # no exception
