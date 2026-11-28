"""
End-to-end tests of what `hai <query>` does when the model or Ollama is
missing, run through hai's real main() against a fake Ollama server.

Covers: --suggest-only (the Ctrl+X Ctrl+H binding), pipes, the interactive
offer (default No), another installed model, the cloud offer, Ollama not
installed or not running, --model, and upgrading from a v0.1.4 config.
"""

import builtins
import json
import os
import sys
from unittest.mock import Mock, patch

import pytest
import yaml

from hai_sh import model_cli, model_flow
from hai_sh.__main__ import main
from tests.fake_ollama import FakeOllama

QUESTION_ANSWER = {"explanation": "It is a fake answer.", "confidence": 90}


@pytest.fixture
def fake():
    server = FakeOllama().start()
    server.answer = dict(QUESTION_ANSWER)  # no command, so nothing is executed
    yield server
    server.stop()


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("HAI_CONFIG", raising=False)
    monkeypatch.delenv("HAI_APP_MODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(model_cli.m, "disk_space", lambda p: (500 * 10**9, 1000 * 10**9))
    monkeypatch.setattr(model_cli.m, "total_ram", lambda: 32 * 10**9)
    (tmp_path / ".hai").mkdir()
    return tmp_path


def write_config(home, base_url, model="gemma4:e2b", extra=""):
    path = home / ".hai" / "config.yaml"
    path.write_text(
        "provider: ollama\n"
        "providers:\n"
        "  ollama:\n"
        f'    base_url: "{base_url}"\n'
        f'    model: "{model}"\n' + extra
    )
    return path


def run_hai(*argv):
    with patch.object(sys, "argv", ["hai", *argv]):
        return main()


def terminal(monkeypatch, *replies, stderr_tty=True):
    """Pretend to be a terminal. Returns the list of prompts shown."""
    it = iter(replies)
    prompts = []

    def fake_input(prompt=""):
        prompts.append(prompt)
        try:
            return next(it)
        except StopIteration:
            raise AssertionError(f"unexpected prompt: {prompt}") from None

    monkeypatch.setattr(builtins, "input", fake_input)
    monkeypatch.setattr(model_cli, "is_interactive", lambda: True)
    monkeypatch.setattr(model_flow, "is_interactive", lambda: True)
    monkeypatch.setattr(model_flow, "stderr_is_tty", lambda: stderr_tty)
    return prompts


def no_terminal(monkeypatch):
    def boom(prompt=""):
        raise AssertionError(f"prompted without a terminal: {prompt}")

    monkeypatch.setattr(builtins, "input", boom)
    monkeypatch.setattr(model_cli, "is_interactive", lambda: False)
    monkeypatch.setattr(model_flow, "is_interactive", lambda: False)


# --------------------------------------------------------------------------
# --suggest-only and pipes never prompt
# --------------------------------------------------------------------------


class TestNoPrompt:
    def test_suggest_only_missing_model_prints_json_and_exits_0(
        self, home, fake, capfd, monkeypatch
    ):
        write_config(home, fake.url)
        fake.pullable.add("gemma4:e2b")
        no_terminal(monkeypatch)
        assert run_hai("--suggest-only", "list", "files") == 0
        out, err = capfd.readouterr()
        data = json.loads(out)
        assert data["command"] == ""
        assert "gemma4:e2b" in data["conversation"]
        assert "hai-model pull gemma4:e2b" in data["conversation"]
        assert "\n" not in data["conversation"] and "\\" not in out
        assert err == ""
        assert fake.pull_requests == []

    def test_suggest_only_success_writes_only_json(self, home, fake, capfd, monkeypatch):
        # The no-gum key binding reads stdout and stderr as one stream.
        write_config(home, fake.url)
        fake.installed["gemma4:e2b"] = 1
        no_terminal(monkeypatch)
        assert run_hai("--suggest-only", "what", "is", "this") == 0
        out, err = capfd.readouterr()
        assert json.loads(out)["conversation"] == "It is a fake answer."
        assert err == ""

    def test_pipe_missing_model_prints_command_and_exits_1(self, home, fake, capfd, monkeypatch):
        write_config(home, fake.url)
        no_terminal(monkeypatch)
        assert run_hai("list", "files") == 1
        err = capfd.readouterr().err
        assert "isn't installed in Ollama" in err
        assert "hai-model pull gemma4:e2b" in err and "4.6 GB" in err
        assert fake.pull_requests == []

    def test_suggest_only_ollama_not_running(self, home, capfd, monkeypatch):
        write_config(home, "http://127.0.0.1:9")
        no_terminal(monkeypatch)
        monkeypatch.setattr(model_cli.m.shutil, "which", lambda n: "/usr/bin/ollama")
        assert run_hai("--suggest-only", "list", "files") == 0
        out, err = capfd.readouterr()
        data = json.loads(out)
        assert data["command"] == ""
        assert "not running" in data["conversation"] and "ollama serve" in data["conversation"]
        assert err == ""

    def test_suggest_only_ollama_not_installed(self, home, capfd, monkeypatch):
        write_config(home, "http://127.0.0.1:9")
        no_terminal(monkeypatch)
        monkeypatch.setattr(model_cli.m.shutil, "which", lambda n: None)
        assert run_hai("--suggest-only", "list", "files") == 0
        data = json.loads(capfd.readouterr().out)
        assert "not installed" in data["conversation"]
        assert "ollama.com" in data["conversation"]

    def test_pipe_ollama_not_running(self, home, capfd, monkeypatch):
        write_config(home, "http://127.0.0.1:9")
        no_terminal(monkeypatch)
        monkeypatch.setattr(model_cli.m.shutil, "which", lambda n: "/usr/bin/ollama")
        assert run_hai("list", "files") == 1
        assert "ollama serve" in capfd.readouterr().err

    def test_remote_ollama_down_names_the_host(self, home, capfd, monkeypatch):
        write_config(home, "http://gpu-box.invalid:11434")
        no_terminal(monkeypatch)
        assert run_hai("--suggest-only", "x") == 0
        conv = json.loads(capfd.readouterr().out)["conversation"]
        assert "gpu-box.invalid" in conv and "another machine" in conv


def test_suggest_only_json_is_safe_for_the_shell_parsers():
    text = model_flow.suggest_only_json("line one\nline two with a \\ and ''' quotes")
    data = json.loads(text)
    assert "\n" not in data["conversation"]
    assert "\\" not in text and "'''" not in text


# --------------------------------------------------------------------------
# Interactive offer
# --------------------------------------------------------------------------


class TestInteractive:
    def test_enter_downloads_nothing(self, home, fake, capfd, monkeypatch):
        write_config(home, fake.url)
        fake.pullable.add("gemma4:e2b")
        terminal(monkeypatch, "")
        assert run_hai("what", "is", "this") == 1
        out = capfd.readouterr().out
        assert "Download: 4.6 GB" in out and "Licence:  Apache 2.0" in out
        assert "Nothing changed" in out
        assert fake.pull_requests == []

    def test_yes_downloads_then_answers_the_question(self, home, fake, capfd, monkeypatch):
        write_config(home, fake.url)
        fake.pullable.add("gemma4:e2b")
        terminal(monkeypatch, "y")
        assert run_hai("what", "is", "this") == 0
        out = capfd.readouterr().out
        assert fake.pull_requests == ["gemma4:e2b"]
        assert "It is a fake answer." in out
        assert fake.generate_requests == ["gemma4:e2b", "gemma4:e2b"]

    def test_decline_then_use_installed_alternative_once(self, home, fake, capfd, monkeypatch):
        cfg = write_config(home, fake.url)
        before = cfg.read_text()
        fake.installed["phi4-mini:latest"] = 1
        prompts = terminal(monkeypatch, "n", "y", "n")  # no download; use phi4-mini; not default
        assert run_hai("what", "is", "this") == 0
        out = capfd.readouterr().out
        assert any("phi4-mini is installed" in p for p in prompts)
        assert "It is a fake answer." in out
        assert fake.generate_requests[-1] == "phi4-mini:latest"
        assert cfg.read_text() == before

    def test_decline_then_make_alternative_the_default(self, home, fake, monkeypatch):
        cfg = write_config(home, fake.url)
        fake.installed["phi4-mini:latest"] = 1
        terminal(monkeypatch, "n", "y", "y")
        assert run_hai("what", "is", "this") == 0
        assert yaml.safe_load(cfg.read_text())["providers"]["ollama"]["model"] == "phi4-mini"

    def test_other_models_menu(self, home, fake, monkeypatch, capfd):
        write_config(home, fake.url)
        fake.installed["phi4-mini:latest"] = 1
        terminal(monkeypatch, "o", "n")  # pick another; don't make it the default
        picked = {}

        def fake_choose(options, header=""):
            picked["options"] = options
            return next(o for o in options if o.startswith("phi4-mini"))

        monkeypatch.setattr("hai_sh.gum.choose", fake_choose)
        assert run_hai("what", "is", "this") == 0
        assert picked["options"][0].startswith("phi4-mini")  # installed first
        assert all("gemma4:e2b " not in o for o in picked["options"])
        assert fake.generate_requests[-1] == "phi4-mini:latest"

    def test_commercial_policy_never_offers_qwen(self, home, fake, monkeypatch):
        write_config(home, fake.url, extra="models:\n  licence_policy: commercial\n")
        fake.installed["qwen2.5-coder:3b"] = 1
        terminal(monkeypatch, "n")  # decline; qwen must not be offered
        assert run_hai("what", "is", "this") == 1
        assert "qwen2.5-coder:3b" not in fake.generate_requests

    def test_cloud_offered_only_when_configured_and_default_no(
        self, home, fake, capfd, monkeypatch
    ):
        write_config(
            home, fake.url, extra="  openai:\n    api_key: sk-test\n    model: gpt-4o-mini\n"
        )
        prompts = terminal(monkeypatch, "n", "")  # no download; Enter on the cloud offer
        from hai_sh import providers

        real_get = providers.get_provider
        used = []
        monkeypatch.setattr(
            providers, "get_provider", lambda name, c: used.append(name) or real_get(name, c)
        )
        assert run_hai("what", "is", "this") == 1
        assert "openai" not in used
        assert prompts[-1].startswith("Use OpenAI for this question only? [y/N]")
        out = capfd.readouterr().out
        assert "You have OpenAI set up" in out and "servers" in out

    def test_cloud_yes_uses_it_for_this_question(self, home, fake, capfd, monkeypatch):
        write_config(
            home, fake.url, extra="  openai:\n    api_key: sk-test\n    model: gpt-4o-mini\n"
        )
        terminal(monkeypatch, "n", "y")
        cloud = Mock()
        cloud.generate.return_value = json.dumps(
            {"explanation": "From the cloud.", "confidence": 80}
        )
        real_get = __import__("hai_sh.providers", fromlist=["get_provider"]).get_provider

        def get_provider(name, cfg):
            return cloud if name == "openai" else real_get(name, cfg)

        monkeypatch.setattr("hai_sh.providers.get_provider", get_provider)
        assert run_hai("what", "is", "this") == 0
        assert "From the cloud." in capfd.readouterr().out
        cloud.generate.assert_called_once()

    def test_no_cloud_offer_without_a_key(self, home, fake, capfd, monkeypatch):
        write_config(home, fake.url)
        terminal(monkeypatch, "n")
        assert run_hai("what", "is", "this") == 1
        assert "set up" not in capfd.readouterr().out

    def test_ollama_not_installed_offers_configured_cloud(self, home, capfd, monkeypatch):
        write_config(home, "http://127.0.0.1:9", extra="  anthropic:\n    api_key: sk-ant-x\n")
        monkeypatch.setattr(model_cli.m.shutil, "which", lambda n: None)
        terminal(monkeypatch, "")
        assert run_hai("what", "is", "this") == 1
        out = capfd.readouterr().out
        assert (
            "curl -fsSL https://ollama.com/install.sh | sh" in out or "ollama.com/download" in out
        )
        assert "You have Anthropic set up" in out


# --------------------------------------------------------------------------
# --model and upgrading from v0.1.4
# --------------------------------------------------------------------------


def test_model_flag_is_one_shot(home, fake, monkeypatch, capfd):
    cfg = write_config(home, fake.url)
    before = cfg.read_text()
    fake.installed["phi4-mini:latest"] = 1
    no_terminal(monkeypatch)
    assert run_hai("--suggest-only", "--model", "phi4-mini", "what", "is", "this") == 0
    assert fake.generate_requests == ["phi4-mini:latest"]
    assert cfg.read_text() == before


# Exactly what v0.1.4's init.create_default_config() wrote.
V014_CONFIG = """# hai-sh configuration file
# See https://github.com/frankbria/hai-sh for documentation

# Default LLM provider to use
provider: "ollama"

# Provider-specific configurations
providers:
  openai:
    # api_key: "sk-..."  # Uncomment and add your API key
    model: "gpt-4o-mini"
    # base_url: null  # Optional: custom API endpoint

  anthropic:
    # api_key: "sk-ant-..."  # Uncomment and add your API key
    model: "claude-sonnet-4-5"

  ollama:
    base_url: "{url}"
    model: "llama3.2"  # Or: mistral, codellama, etc.

# Context settings
context:
  include_history: true
  history_length: 10
  include_env_vars: true
  include_git_state: true

# Output settings
output:
  show_conversation: true
  show_reasoning: true
  use_colors: true
"""


class TestUpgradeFromV014:
    @pytest.fixture
    def v014(self, home, fake):
        path = home / ".hai" / "config.yaml"
        path.write_text(V014_CONFIG.replace("{url}", fake.url))
        os.chmod(path, 0o600)
        fake.installed["llama3.2:latest"] = 1
        return path

    def test_model_kept_and_file_untouched(self, v014, fake, monkeypatch):
        before = (v014.read_bytes(), v014.stat().st_mtime_ns)
        terminal(monkeypatch)
        assert run_hai("what", "is", "this") == 0
        assert fake.generate_requests == ["llama3.2:latest"]
        assert (v014.read_bytes(), v014.stat().st_mtime_ns) == before
        assert not (v014.parent / "config.yaml.bak").exists()

    def test_notice_once_in_a_terminal(self, v014, monkeypatch, capfd):
        terminal(monkeypatch)
        run_hai("what", "is", "this")
        first = capfd.readouterr().err
        run_hai("what", "is", "this")
        second = capfd.readouterr().err
        assert "hai-model use gemma4:e2b" in first
        assert "hai-model use" not in second

    def test_no_notice_in_suggest_only(self, v014, monkeypatch, capfd):
        terminal(monkeypatch)
        assert run_hai("--suggest-only", "what", "is", "this") == 0
        out, err = capfd.readouterr()
        json.loads(out)
        assert "hai-model use" not in out + err
        assert not (v014.parent / ".notices").exists()

    def test_no_notice_in_a_pipe(self, v014, monkeypatch, capfd):
        no_terminal(monkeypatch)
        run_hai("what", "is", "this")
        assert "hai-model use" not in capfd.readouterr().err

    def test_no_notice_when_stderr_is_redirected(self, v014, monkeypatch, capfd):
        terminal(monkeypatch, stderr_tty=False)
        run_hai("what", "is", "this")
        assert "hai-model use" not in capfd.readouterr().err

    def test_old_config_inherits_the_new_sampling_settings(self, v014):
        from hai_sh.config import load_config

        ollama = load_config(config_path=v014, use_pydantic=False)["providers"]["ollama"]
        assert ollama["model"] == "llama3.2"
        assert ollama["format"] == "schema" and ollama["temperature"] == 0
        assert ollama["think"] is False

    def test_old_config_still_validates(self, v014):
        from hai_sh.config import load_config
        from hai_sh.schema import validate_config_dict

        raw = load_config(config_path=v014, use_pydantic=False)
        raw.pop("_warnings", None)
        config, _ = validate_config_dict(raw)
        assert config.providers.ollama.model == "llama3.2"
        assert config.models.licence_policy == "any"


def test_documented_undo_restores_v014_sampling(tmp_path):
    """CONFIGURATION.md's 'Upgrading from v0.1.4' settings really turn the new defaults off."""
    from hai_sh.config import load_config
    from hai_sh.providers.ollama import OllamaProvider

    path = tmp_path / "config.yaml"
    path.write_text(
        "providers:\n  ollama:\n    model: llama3.2\n"
        "    format: null\n    temperature: 0.7\n    think: null\n"
    )
    ollama = load_config(config_path=path, use_pydantic=False)["providers"]["ollama"]
    provider = OllamaProvider(ollama)
    assert (provider.format, provider.temperature, provider.think) == (None, 0.7, None)


class TestSetupWizard:
    def _choose(self, monkeypatch, pick):
        seen = {}

        def choose(options, header=""):
            seen["options"] = options
            return pick(options)

        monkeypatch.setattr("hai_sh.gum.choose", choose)
        return seen

    def test_lists_catalog_installed_first_and_skips_download_if_installed(
        self, home, fake, monkeypatch
    ):
        from hai_sh.__main__ import choose_setup_ollama_model

        fake.installed["phi4-mini:latest"] = 1
        fake.installed["mistral:latest"] = 1
        no_terminal(monkeypatch)
        seen = self._choose(monkeypatch, lambda opts: opts[0])
        assert choose_setup_ollama_model(fake.url) == "phi4-mini"
        opts = seen["options"]
        assert opts[0].startswith("phi4-mini (lighter)") and opts[0].endswith("installed")
        assert any(o.startswith("gemma4:e2b (recommended)") for o in opts)
        assert "mistral:latest (installed, untested with hai)" in opts
        assert opts[-1] == "Another model (type its name)"
        assert fake.pull_requests == []

    def test_picking_a_missing_model_asks_before_downloading(self, home, fake, monkeypatch):
        from hai_sh.__main__ import choose_setup_ollama_model

        fake.pullable.add("gemma4:e2b")
        terminal(monkeypatch, "")  # Enter on "Download it now?"
        self._choose(monkeypatch, lambda opts: next(o for o in opts if o.startswith("gemma4:e2b")))
        assert choose_setup_ollama_model(fake.url) == "gemma4:e2b"
        assert fake.pull_requests == []

        terminal(monkeypatch, "y")
        assert choose_setup_ollama_model(fake.url) == "gemma4:e2b"
        assert fake.pull_requests == ["gemma4:e2b"]

    def test_ollama_down_still_offers_the_menu(self, home, monkeypatch, capsys):
        from hai_sh.__main__ import choose_setup_ollama_model

        monkeypatch.setattr(model_cli.m.shutil, "which", lambda n: None)
        seen = self._choose(monkeypatch, lambda opts: next(o for o in opts if o.startswith("phi4-mini")))
        assert choose_setup_ollama_model("http://127.0.0.1:9") == "phi4-mini"
        assert all("installed" not in o for o in seen["options"])
        assert seen["options"][-1] == "Another model (type its name)"
        assert "hai-model pull phi4-mini" in capsys.readouterr().out

    def test_ollama_down_and_cancel_returns_none(self, home, monkeypatch):
        from hai_sh.__main__ import choose_setup_ollama_model

        monkeypatch.setattr(model_cli.m.shutil, "which", lambda n: None)
        self._choose(monkeypatch, lambda opts: None)
        assert choose_setup_ollama_model("http://127.0.0.1:9") is None

    def test_cancel_returns_none(self, home, fake, monkeypatch):
        from hai_sh.__main__ import choose_setup_ollama_model

        self._choose(monkeypatch, lambda opts: None)
        assert choose_setup_ollama_model(fake.url) is None

    def test_commercial_policy_hides_qwen(self, home, fake, monkeypatch):
        from hai_sh.__main__ import choose_setup_ollama_model

        (home / ".hai" / "config.yaml").write_text("models:\n  licence_policy: commercial\n")
        seen = self._choose(monkeypatch, lambda opts: None)
        choose_setup_ollama_model(fake.url)
        assert not any("qwen" in o for o in seen["options"])


class TestProviderAndModelFlags:
    def _config(self, home, fake):
        path = home / ".hai" / "config.yaml"
        path.write_text(
            "provider_priority: [ollama, openai]\n"
            "providers:\n"
            "  ollama:\n"
            f'    base_url: "{fake.url}"\n'
            '    model: "gemma4:e2b"\n'
            "  openai:\n"
            "    api_key: sk-test\n"
            "    model: gpt-4o-mini\n"
        )

    def test_provider_flag_goes_first_even_with_a_priority_list(
        self, home, fake, monkeypatch, capfd
    ):
        self._config(home, fake)
        fake.installed["gemma4:e2b"] = 1
        no_terminal(monkeypatch)
        from hai_sh import providers

        real_get = providers.get_provider
        cloud = Mock()
        cloud.check_availability.return_value = (True, None)
        cloud.generate.return_value = json.dumps({"explanation": "cloud", "confidence": 80})
        seen = {}

        def get_provider(name, cfg):
            if name == "openai":
                seen["model"] = cfg.get("model")
                return cloud
            return real_get(name, cfg)

        monkeypatch.setattr(providers, "get_provider", get_provider)
        assert run_hai("--suggest-only", "--provider", "openai", "--model", "gpt-4.1", "x") == 0
        assert json.loads(capfd.readouterr().out)["conversation"] == "cloud"
        assert seen["model"] == "gpt-4.1"
        assert fake.generate_requests == []  # Ollama was not used

    def test_model_flag_without_provider_goes_to_the_first_in_the_list(
        self, home, fake, monkeypatch
    ):
        self._config(home, fake)
        fake.installed["phi4-mini:latest"] = 1
        no_terminal(monkeypatch)
        assert run_hai("--suggest-only", "--model", "phi4-mini", "x") == 0
        assert fake.generate_requests == ["phi4-mini:latest"]


def test_setup_wizard_keeps_a_commercial_policy(home):
    from hai_sh.__main__ import _write_setup_config

    cfg = home / ".hai" / "config.yaml"
    cfg.write_text("models:\n  licence_policy: commercial\n")
    _write_setup_config({"provider": "ollama"})
    assert yaml.safe_load(cfg.read_text())["models"]["licence_policy"] == "commercial"


def test_setup_wizard_new_config_policy_is_any(home):
    from hai_sh.__main__ import _write_setup_config

    _write_setup_config({"provider": "ollama"})
    cfg = home / ".hai" / "config.yaml"
    assert yaml.safe_load(cfg.read_text())["models"]["licence_policy"] == "any"


class TestConfigFlagInHints:
    def test_suggest_only_hint_names_the_config_file(self, tmp_path, home, fake, capfd, monkeypatch):
        other = tmp_path / "remote config.yaml"
        other.write_text(
            "provider: ollama\nproviders:\n  ollama:\n"
            f'    base_url: "{fake.url}"\n    model: "gemma4:e2b"\n'
        )
        no_terminal(monkeypatch)
        assert run_hai("--config", str(other), "--suggest-only", "list", "files") == 0
        out, err = capfd.readouterr()
        data = json.loads(out)
        assert f"hai-model --config '{other}' pull gemma4:e2b" in data["conversation"]
        assert "\\" not in out and err == ""

    def test_pipe_hint_names_the_config_file(self, tmp_path, home, fake, capfd, monkeypatch):
        other = tmp_path / "remote.yaml"
        other.write_text(f'providers:\n  ollama:\n    base_url: "{fake.url}"\n')
        no_terminal(monkeypatch)
        assert run_hai("--config", str(other), "list", "files") == 1
        assert f"hai-model --config {other} pull gemma4:e2b" in capfd.readouterr().err

    def test_default_config_gives_the_plain_command(self, home):
        from hai_sh.init import get_config_path

        assert model_cli.hai_model_command("pull x") == "hai-model pull x"
        assert model_cli.hai_model_command("pull x", get_config_path()) == "hai-model pull x"

    def test_hai_model_with_config_repeats_it(self, tmp_path, home, fake, capsys, monkeypatch):
        other = tmp_path / "remote.yaml"
        other.write_text(f'providers:\n  ollama:\n    base_url: "{fake.url}"\n')
        no_terminal(monkeypatch)
        assert model_cli.main(["--config", str(other), "pull", "gemma4:e2b"]) == 1
        assert f"hai-model --config {other} pull gemma4:e2b --yes" in capsys.readouterr().out


def test_setup_config_is_private_from_the_start(home, monkeypatch):
    from hai_sh.__main__ import _write_setup_config
    from hai_sh.init import get_config_path

    old = os.umask(0o022)
    try:
        _write_setup_config({"provider": "openai", "openai_api_key": "sk-test"})
    finally:
        os.umask(old)
    path = get_config_path()
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert "sk-test" in path.read_text()
