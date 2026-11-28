"""Tests for hai_sh/models.py: catalog, licence policy, detection, pull, config edit."""

import os
import stat
from pathlib import Path

import pytest
import yaml

from hai_sh import models as m
from hai_sh.providers.ollama import DEFAULT_OLLAMA_MODEL
from tests.fake_ollama import FakeOllama


@pytest.fixture
def fake():
    server = FakeOllama().start()
    yield server
    server.stop()


# --------------------------------------------------------------------------
# Catalog
# --------------------------------------------------------------------------


class TestCatalog:
    def test_shipped_catalog_parses(self):
        catalog = m.load_catalog()
        assert catalog.schema_version == 1
        assert catalog.cases == 93
        assert len(catalog.models) >= 3

    def test_exactly_one_default_and_it_matches_the_code(self):
        catalog = m.load_catalog()
        defaults = [e for e in catalog.models if e.role == "default"]
        assert len(defaults) == 1
        assert defaults[0].name == DEFAULT_OLLAMA_MODEL

    def test_default_is_commercial_safe(self):
        # The licence carve-out must never leave hai without a default.
        assert m.load_catalog().default.commercial_use is True

    @pytest.mark.parametrize("role", m.ROLES)
    def test_every_role_has_a_commercial_entry(self, role):
        catalog = m.load_catalog()
        if catalog.by_role(role, "any"):
            assert catalog.by_role(role, "commercial"), role

    def test_default_clears_the_bar(self):
        assert m.load_catalog().default.clears_bar is True

    def test_entries_are_plausible(self):
        for e in m.load_catalog().models:
            assert e.download_bytes > 100_000_000, e.name
            assert 0 < e.task_accuracy <= 1
            assert e.accuracy_ci[0] <= e.task_accuracy <= e.accuracy_ci[1]
            assert 0 <= e.refused <= 7
            assert e.licence and e.licence_checked
            assert e.memory_bytes > 0

    def test_lighter_order_follows_policy(self):
        catalog = m.load_catalog()
        assert catalog.by_role("lighter", "any")[0].name == "qwen2.5-coder:3b"
        assert catalog.by_role("lighter", "commercial")[0].name == "phi4-mini"

    def test_recommended_puts_default_first(self):
        assert m.load_catalog().recommended()[0].role == "default"

    def test_get_is_tag_insensitive(self):
        catalog = m.load_catalog()
        assert catalog.get("phi4-mini:latest").name == "phi4-mini"
        assert catalog.get("nope") is None

    def test_memory_falls_back_to_download_size(self):
        e = m.load_catalog().default
        assert e.loaded_bytes is None
        assert e.memory_bytes == e.download_bytes

    def _write(self, tmp_path, data):
        p = tmp_path / "models.yaml"
        p.write_text(yaml.safe_dump(data))
        return p

    def test_rejects_two_defaults(self, tmp_path):
        data = yaml.safe_load(m.CATALOG_PATH.read_text())
        data["models"][1]["role"] = "default"
        with pytest.raises(m.CatalogError):
            m.load_catalog(self._write(tmp_path, data))

    def test_rejects_unknown_role(self, tmp_path):
        data = yaml.safe_load(m.CATALOG_PATH.read_text())
        data["models"][1]["role"] = "best"
        with pytest.raises(m.CatalogError):
            m.load_catalog(self._write(tmp_path, data))

    def test_rejects_missing_field(self, tmp_path):
        data = yaml.safe_load(m.CATALOG_PATH.read_text())
        del data["models"][0]["download_bytes"]
        with pytest.raises(m.CatalogError):
            m.load_catalog(self._write(tmp_path, data))

    def test_rejects_wrong_schema_version(self, tmp_path):
        with pytest.raises(m.CatalogError):
            m.load_catalog(self._write(tmp_path, {"schema_version": 2, "models": []}))

    def test_missing_file(self, tmp_path):
        with pytest.raises(m.CatalogError):
            m.load_catalog(tmp_path / "absent.yaml")


class TestLicencePolicy:
    def test_package_default_is_any(self):
        assert m.DEFAULT_LICENCE_POLICY == "any"

    def test_user_can_tighten(self):
        assert (
            m.effective_licence_policy({"models": {"licence_policy": "commercial"}}) == "commercial"
        )

    def test_default_and_unknown_values_mean_any(self):
        assert m.effective_licence_policy(None) == "any"
        assert m.effective_licence_policy({}) == "any"
        assert m.effective_licence_policy({"models": {"licence_policy": "whatever"}}) == "any"

    def test_package_commercial_wins_over_user_any(self, monkeypatch):
        monkeypatch.setattr(m, "DEFAULT_LICENCE_POLICY", "commercial")
        assert m.effective_licence_policy({"models": {"licence_policy": "any"}}) == "commercial"

    def test_commercial_hides_non_commercial(self):
        names = [e.name for e in m.load_catalog().recommended("commercial")]
        assert "qwen2.5-coder:3b" not in names
        assert DEFAULT_OLLAMA_MODEL in names


# --------------------------------------------------------------------------
# Names and detection
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "given, expected",
    [
        ("llama3.2", "llama3.2:latest"),
        ("llama3.2:latest", "llama3.2:latest"),
        ("gemma4:e2b", "gemma4:e2b"),
        ("library/phi4-mini", "library/phi4-mini:latest"),
        ("registry.example:5000/x/model", "registry.example:5000/x/model:latest"),
        ("hf.co/org/Model-GGUF", "hf.co/org/Model-GGUF"),
        ("  qwen2.5-coder:3b ", "qwen2.5-coder:3b"),
        ("", ""),
    ],
)
def test_normalise_name(given, expected):
    assert m.normalise_name(given) == expected


def test_same_model():
    assert m.same_model("llama3.2", "llama3.2:latest")
    assert not m.same_model("gemma4:e2b", "gemma4:e4b")


@pytest.mark.parametrize(
    "url, local",
    [
        ("http://localhost:11434", True),
        ("http://127.0.0.1:11434", True),
        ("http://[::1]:11434", True),
        ("http://gpu-box:11434", False),
        ("https://ollama.example.com", False),
        ("", False),
    ],
)
def test_is_local_url(url, local):
    assert m.is_local_url(url) is local


def test_detect_running_with_model(fake):
    fake.installed["gemma4:e2b"] = 5
    env = m.detect_environment(fake.url, "gemma4:e2b")
    assert env.running and env.version == "0.0.0-fake"
    assert env.model_installed
    assert env.local
    assert env.catalog_entry.name == "gemma4:e2b"


def test_detect_running_without_model(fake):
    fake.installed["llama3.2:latest"] = 5
    env = m.detect_environment(fake.url, "gemma4:e2b")
    assert env.running and not env.model_installed
    assert m.find_installed("llama3.2", env.installed).name == "llama3.2:latest"


def test_detect_not_running():
    env = m.detect_environment("http://127.0.0.1:9", "gemma4:e2b")
    assert not env.running
    assert env.installed is None and env.version is None


def test_detect_remote_skips_local_probes(monkeypatch):
    calls = []
    monkeypatch.setattr(m, "disk_space", lambda p: calls.append(p) or (1, 2))
    monkeypatch.setattr(m, "_get_json", lambda url, timeout=2: None)
    env = m.detect_environment("http://gpu-box:11434", "gemma4:e2b")
    assert not env.local and env.disk_free is None and calls == []


def test_models_dir_prefers_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_MODELS", str(tmp_path))
    assert m.ollama_models_dir() == tmp_path


def test_models_dir_home(tmp_path, monkeypatch):
    monkeypatch.delenv("OLLAMA_MODELS", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".ollama" / "models").mkdir(parents=True)
    assert m.ollama_models_dir() == tmp_path / ".ollama" / "models"


def test_disk_space_and_ram_are_numbers():
    free, total = m.disk_space(None)
    assert free and total and free <= total
    ram = m.total_ram()
    assert ram is None or ram > 0


def test_disk_space_unreadable_disk(monkeypatch):
    def fail(path):
        raise OSError(13, "Permission denied")

    monkeypatch.setattr(m.shutil, "disk_usage", fail)
    assert m.disk_space(Path("/definitely/not/here")) == (None, None)


def test_disk_space_missing_path_measures_its_parent_disk():
    assert m.disk_space(Path("/definitely/not/here")) == m.disk_space(Path("/"))


# --------------------------------------------------------------------------
# Pull checks and pulling
# --------------------------------------------------------------------------

GB = 1000**3


class TestCheckPull:
    def test_plenty_of_space(self):
        assert m.check_pull(5 * GB, 2 * GB, 200 * GB, 500 * GB, 32 * GB).ok

    def test_stops_when_less_than_10_percent_would_be_left(self):
        r = m.check_pull(5 * GB, None, 12 * GB, 100 * GB, None)
        assert not r.ok and "Not enough disk space" in r.messages[0]

    def test_stops_when_less_than_2_gb_would_be_left(self):
        r = m.check_pull(5 * GB, None, 6 * GB, 10 * GB, None)
        assert not r.ok

    def test_ten_percent_floor_is_capped_at_20_gb(self):
        # 2 TB disk, 100 GB free: 10% would be 200 GB, the cap makes it 20 GB.
        assert m.check_pull(5 * GB, None, 100 * GB, 2000 * GB, None).ok
        assert not m.check_pull(5 * GB, None, 24 * GB, 2000 * GB, None).ok

    def test_force_overrides(self):
        r = m.check_pull(5 * GB, None, 6 * GB, 10 * GB, None, force=True)
        assert r.ok and "--force" in r.messages[0]

    def test_memory_warning_does_not_stop(self):
        r = m.check_pull(1 * GB, 7 * GB, 200 * GB, 500 * GB, 8 * GB)
        assert r.ok and "memory" in r.messages[0]

    def test_unknowns_skip_checks(self):
        assert m.check_pull(None, None, None, None, None).ok


def test_pull_streams_progress(fake):
    fake.pullable.add("phi4-mini")
    seen = []
    m.pull_model(fake.url, "phi4-mini", on_progress=seen.append)
    assert fake.installed.get("phi4-mini:latest") == 1000
    assert seen[-1].status == "success"
    assert max(p.fraction or 0 for p in seen) == 1.0
    assert any(p.fraction == 0.5 for p in seen)


def test_pull_unknown_model(fake):
    with pytest.raises(m.PullError, match="does not exist"):
        m.pull_model(fake.url, "no-such-model")


def test_pull_error_midway(fake):
    fake.pullable.add("phi4-mini")
    fake.fail_pull_midway = True
    with pytest.raises(m.PullError, match="connection reset"):
        m.pull_model(fake.url, "phi4-mini")


def test_pull_cannot_connect():
    with pytest.raises(m.PullError, match="Cannot reach"):
        m.pull_model("http://127.0.0.1:9", "phi4-mini", timeout=1)


# --------------------------------------------------------------------------
# Config edit
# --------------------------------------------------------------------------

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
    base_url: "http://localhost:11434"
    model: "llama3.2"  # Or: mistral, codellama, etc.

# Context settings
context:
  include_history: true
"""


class TestSetConfigModel:
    def test_edits_only_the_ollama_model_line(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text(V014_CONFIG)
        old, new = m.set_config_model(p, "gemma4:e2b")
        assert (old, new) == ("llama3.2", "gemma4:e2b")
        after = p.read_text()
        assert after == V014_CONFIG.replace('model: "llama3.2"', 'model: "gemma4:e2b"')
        assert "# Or: mistral, codellama, etc." in after
        assert yaml.safe_load(after)["providers"]["openai"]["model"] == "gpt-4o-mini"

    def test_writes_backup_and_keeps_mode_600(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text(V014_CONFIG)
        m.set_config_model(p, "phi4-mini")
        assert (tmp_path / "config.yaml.bak").read_text() == V014_CONFIG
        for f in (p, tmp_path / "config.yaml.bak"):
            assert stat.S_IMODE(f.stat().st_mode) == 0o600

    def test_unquoted_value_and_no_comment(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("providers:\n  ollama:\n    model: llama3.2\n    base_url: http://x:1\n")
        old, _ = m.set_config_model(p, "gemma4:e2b")
        assert old == "llama3.2"
        assert (
            p.read_text()
            == 'providers:\n  ollama:\n    model: "gemma4:e2b"\n    base_url: http://x:1\n'
        )

    def test_ignores_nested_and_other_providers_model_keys(self, tmp_path):
        text = (
            "providers:\n"
            "  openai:\n    model: gpt-4o-mini\n"
            "  ollama:\n    options:\n      model: weird\n    model: llama3.2\n"
        )
        p = tmp_path / "config.yaml"
        p.write_text(text)
        m.set_config_model(p, "gemma4:e2b")
        data = yaml.safe_load(p.read_text())
        assert data["providers"]["openai"]["model"] == "gpt-4o-mini"
        assert data["providers"]["ollama"]["options"]["model"] == "weird"
        assert data["providers"]["ollama"]["model"] == "gemma4:e2b"

    def test_falls_back_to_rewrite_when_no_model_line(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text(
            "provider: ollama\nproviders:\n  ollama:\n    base_url: http://localhost:11434\n"
        )
        old, _ = m.set_config_model(p, "gemma4:e2b")
        assert old is None
        data = yaml.safe_load(p.read_text())
        assert data["providers"]["ollama"] == {
            "base_url": "http://localhost:11434",
            "model": "gemma4:e2b",
        }

    def test_creates_missing_file(self, tmp_path):
        p = tmp_path / "sub" / "config.yaml"
        m.set_config_model(p, "gemma4:e2b")
        assert yaml.safe_load(p.read_text())["providers"]["ollama"]["model"] == "gemma4:e2b"
        assert not (tmp_path / "sub" / "config.yaml.bak").exists()

    def test_flow_style_providers_falls_back(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("providers: {ollama: {model: llama3.2}}\n")
        m.set_config_model(p, "gemma4:e2b")
        assert yaml.safe_load(p.read_text())["providers"]["ollama"]["model"] == "gemma4:e2b"


# --------------------------------------------------------------------------
# Notices, cloud, hints, formatting
# --------------------------------------------------------------------------


def test_notice_marker(tmp_path):
    assert not m.notice_seen("k", tmp_path)
    m.mark_notice_seen("k", tmp_path)
    assert m.notice_seen("k", tmp_path)
    assert not m.notice_seen("other", tmp_path)


def test_old_default_notice_only_for_llama32():
    text = m.old_default_notice("llama3.2:latest")
    assert "gemma4:e2b" in text and "hai-model use gemma4:e2b" in text
    assert m.old_default_notice("gemma4:e2b") is None
    assert m.old_default_notice("mistral") is None


def test_configured_cloud_providers(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert m.configured_cloud_providers({"providers": {"openai": {"model": "x"}}}) == []
    got = m.configured_cloud_providers({"providers": {"openai": {"api_key": "sk-1", "model": "x"}}})
    assert got == [("openai", {"api_key": "sk-1", "model": "x"})]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-2")
    names = [n for n, _ in m.configured_cloud_providers({})]
    assert names == ["anthropic"]


def test_install_and_start_hints_are_printed_not_run():
    linux = "\n".join(m.ollama_install_hint("Linux"))
    assert "curl -fsSL https://ollama.com/install.sh | sh" in linux and "sudo" in linux
    mac = "\n".join(m.ollama_install_hint("Darwin"))
    assert "https://ollama.com/download" in mac
    assert "sudo systemctl start ollama" in "\n".join(m.ollama_start_hint("Linux"))
    assert "ollama serve" in "\n".join(m.ollama_start_hint("Darwin"))


@pytest.mark.parametrize(
    "n, text",
    [
        (None, "unknown"),
        (512, "512 B"),
        (4587156505, "4.6 GB"),
        (1929912626, "1.9 GB"),
        (2 * 10**12, "2.0 TB"),
    ],
)
def test_format_bytes(n, text):
    assert m.format_bytes(n) == text


def test_ollama_config_defaults():
    assert m.ollama_config({}) == {
        "base_url": "http://localhost:11434",
        "model": DEFAULT_OLLAMA_MODEL,
    }


class TestReviewFixes:
    def test_backup_and_config_are_never_world_readable(self, tmp_path):
        import os

        path = tmp_path / "config.yaml"
        path.write_text('providers:\n  ollama:\n    model: "a"\n    api_key: secret\n')
        path.chmod(0o644)
        old_umask = os.umask(0o022)
        try:
            m.set_config_model(path, "b")
        finally:
            os.umask(old_umask)
        for p in (path, tmp_path / "config.yaml.bak"):
            assert stat.S_IMODE(p.stat().st_mode) == 0o600, p

    def test_existing_world_readable_backup_is_narrowed(self, tmp_path):
        path = tmp_path / "config.yaml"
        path.write_text('providers:\n  ollama:\n    model: "a"\n')
        backup = tmp_path / "config.yaml.bak"
        backup.write_text("old")
        backup.chmod(0o644)
        m.set_config_model(path, "b")
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
        assert 'model: "a"' in backup.read_text()

    @pytest.mark.parametrize(
        "value",
        [
            "model: >-\n      gemma4:e2b\n",
            "model: |\n      gemma4:e2b\n",
            "model:\n      gemma4:e2b\n",
        ],
    )
    def test_multiline_model_value_is_rewritten_not_corrupted(self, tmp_path, value):
        path = tmp_path / "config.yaml"
        path.write_text(f"providers:\n  ollama:\n    base_url: http://h:1\n    {value}")
        old, new = m.set_config_model(path, "phi4-mini")
        data = yaml.safe_load(path.read_text())
        assert data["providers"]["ollama"] == {"base_url": "http://h:1", "model": "phi4-mini"}
        assert old.strip() == "gemma4:e2b"  # a literal block keeps its newline

    def test_connection_lost_mid_stream_is_a_pull_error(self, monkeypatch):
        import requests

        class Response:
            status_code = 200

            def iter_lines(self):
                yield b'{"status": "pulling aaa", "digest": "d", "total": 10, "completed": 1}'
                raise requests.exceptions.ConnectionError("reset by peer")

            def close(self):
                self.closed = True

        monkeypatch.setattr(requests, "post", lambda *a, **k: Response())
        with pytest.raises(m.PullError, match="connection to Ollama was lost"):
            m.pull_model("http://localhost:11434", "x")

    def test_read_timeout_mid_stream_is_a_pull_error(self, monkeypatch):
        import requests

        class Response:
            status_code = 200

            def iter_lines(self):
                raise requests.exceptions.ReadTimeout("stalled")
                yield  # pragma: no cover

            def close(self):
                pass

        monkeypatch.setattr(requests, "post", lambda *a, **k: Response())
        with pytest.raises(m.PullError):
            m.pull_model("http://localhost:11434", "x")


class TestSecondReviewFixes:
    def test_failed_write_leaves_the_old_config_whole(self, tmp_path, monkeypatch):
        path = tmp_path / "config.yaml"
        original = 'providers:\n  ollama:\n    model: "a"\n    api_key: secret\n'
        path.write_text(original)

        def full_disk(fd):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(m.os, "fsync", full_disk)
        with pytest.raises(OSError):
            m.set_config_model(path, "b")
        assert path.read_text() == original
        assert not [p for p in tmp_path.iterdir() if ".hai-tmp-" in p.name]

    def test_symlinked_config_keeps_its_link(self, tmp_path):
        real = tmp_path / "dotfiles" / "hai.yaml"
        real.parent.mkdir()
        real.write_text('providers:\n  ollama:\n    model: "a"\n')
        link = tmp_path / "config.yaml"
        link.symlink_to(real)
        m.set_config_model(link, "b")
        assert link.is_symlink()
        assert 'model: "b"' in real.read_text()
        assert stat.S_IMODE(real.stat().st_mode) == 0o600

    @pytest.mark.parametrize(
        "text",
        [
            # ollama defines the anchor, openai reuses it
            "providers:\n"
            "  ollama: &shared\n"
            "    model: gpt-4o-mini\n"
            "    timeout: 30\n"
            "  openai: *shared\n",
            # both reuse an anchor defined elsewhere
            "base: &shared\n"
            "  model: gpt-4o-mini\n"
            "providers:\n"
            "  ollama: *shared\n"
            "  openai: *shared\n",
        ],
    )
    def test_yaml_alias_shared_with_another_provider_is_not_changed(self, tmp_path, text):
        path = tmp_path / "config.yaml"
        path.write_text(text)
        old, _ = m.set_config_model(path, "phi4-mini")
        data = yaml.safe_load(path.read_text())
        assert old == "gpt-4o-mini"
        assert data["providers"]["ollama"]["model"] == "phi4-mini"
        assert data["providers"]["openai"]["model"] == "gpt-4o-mini"

    def test_disk_check_uses_the_fullest_candidate_disk(self, tmp_path, monkeypatch):
        home_models = tmp_path / "home" / ".ollama" / "models"
        service = tmp_path / "service"
        home_models.mkdir(parents=True)
        service.mkdir()
        free = {home_models: (500, 1000), service: (10, 1000)}
        monkeypatch.setattr(m, "disk_space", lambda p: free.get(p, (None, None)))
        assert m.tightest_disk([home_models, service]) == (service, 10, 1000)
        assert m.tightest_disk([]) == (None, None, None)

    def test_model_dirs_lists_every_existing_candidate(self, tmp_path, monkeypatch):
        env_dir = tmp_path / "custom"
        env_dir.mkdir()
        (tmp_path / ".ollama" / "models").mkdir(parents=True)
        monkeypatch.setenv("OLLAMA_MODELS", str(env_dir))
        monkeypatch.setenv("HOME", str(tmp_path))
        dirs = m.ollama_model_dirs()
        assert dirs[:2] == [env_dir, tmp_path / ".ollama" / "models"]

    def test_urllib3_libressl_warning_is_hidden(self):
        import subprocess
        import sys

        code = (
            "import hai_sh, warnings\n"
            "warnings.warn_explicit('urllib3 v2 only supports OpenSSL 1.1.1+, currently "
            "the ssl module is compiled with LibreSSL 2.8.3', UserWarning, "
            "'urllib3/__init__.py', 35, module='urllib3')\n"
        )
        import os

        env = {k: v for k, v in os.environ.items() if k != "PYTHONWARNINGS"}
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=env
        )
        assert proc.returncode == 0, proc.stderr
        assert proc.stderr == ""


class TestThirdReviewFixes:
    def test_backup_symlink_is_replaced_not_followed(self, tmp_path):
        other = tmp_path / "other.yaml"
        other.write_text("precious: true\n")
        path = tmp_path / "config.yaml"
        original = 'providers:\n  ollama:\n    model: "a"\n'
        path.write_text(original)
        backup = tmp_path / "config.yaml.bak"
        backup.symlink_to(other)
        m.set_config_model(path, "b")
        assert other.read_text() == "precious: true\n"
        assert not backup.is_symlink() and backup.read_text() == original

    def test_no_temp_file_means_no_change_and_a_clear_error(self, tmp_path, monkeypatch):
        path = tmp_path / "config.yaml"
        original = 'providers:\n  ollama:\n    model: "a"\n'
        path.write_text(original)
        real_open = os.open

        def no_new_files(p, flags, *a):
            if ".hai-tmp-" in str(p):
                raise PermissionError(13, "Permission denied")
            return real_open(p, flags, *a)

        monkeypatch.setattr(m.os, "open", no_new_files)
        with pytest.raises(m.ConfigWriteError, match="Nothing was changed"):
            m.set_config_model(path, "b")
        assert path.read_text() == original

    def test_disk_check_weighs_each_disks_own_reserve(self, tmp_path, monkeypatch):
        small, big = tmp_path / "small", tmp_path / "big"
        small.mkdir()
        big.mkdir()
        gb = 10**9
        # 12 GB free of 50 GB (keeps 5 GB) vs 15 GB free of 500 GB (keeps 20 GB)
        sizes = {small: (12 * gb, 50 * gb), big: (15 * gb, 500 * gb)}
        monkeypatch.setattr(m, "disk_space", lambda p: sizes.get(p, (None, None)))
        path, free, total = m.tightest_disk([small, big])
        assert path == big
        assert not m.check_pull(int(4.6 * gb), None, free, total, None).ok


class TestFourthReviewFixes:
    def test_config_linked_to_its_own_backup_is_refused(self, tmp_path):
        backup = tmp_path / "config.yaml.bak"
        original = 'providers:\n  ollama:\n    model: "a"\n'
        backup.write_text(original)
        path = tmp_path / "config.yaml"
        path.symlink_to(backup)
        with pytest.raises(m.ConfigWriteError, match="same file"):
            m.set_config_model(path, "b")
        assert backup.read_text() == original

    def test_edit_made_meanwhile_is_not_overwritten(self, tmp_path, monkeypatch):
        path = tmp_path / "config.yaml"
        path.write_text('providers:\n  ollama:\n    model: "a"\n')
        real_fsync = m.os.fsync

        def someone_saves(fd):
            real_fsync(fd)
            if not path.read_text().startswith("# edited"):
                path.write_text('# edited\nproviders:\n  ollama:\n    model: "x"\n')

        monkeypatch.setattr(m.os, "fsync", someone_saves)
        with pytest.raises(m.ConfigWriteError, match="changed while"):
            m.set_config_model(path, "b")
        assert path.read_text().startswith("# edited")
        assert not [p for p in tmp_path.iterdir() if ".hai-tmp-" in p.name]

    @pytest.mark.parametrize(
        "text",
        [
            "providers:\n  ollama:\n    model: [unclosed\n",
            "providers: [ollama]\n",
            "- just\n- a list\n",
        ],
    )
    def test_config_hai_cannot_read_is_left_alone(self, tmp_path, text):
        path = tmp_path / "config.yaml"
        path.write_text(text)
        with pytest.raises(m.ConfigWriteError, match="Nothing was changed"):
            m.set_config_model(path, "b")
        assert path.read_text() == text
        assert not (tmp_path / "config.yaml.bak").exists()


class TestFifthReviewFixes:
    @pytest.mark.parametrize("line", [b"null", b"[1, 2]", b'"pulling"', b"7"])
    def test_pull_event_that_is_not_an_object_is_a_pull_error(self, monkeypatch, line):
        import requests

        class Response:
            status_code = 200

            def iter_lines(self):
                yield line

            def close(self):
                pass

        monkeypatch.setattr(requests, "post", lambda *a, **k: Response())
        with pytest.raises(m.PullError, match="unexpected reply"):
            m.pull_model("http://localhost:11434", "x")

    def test_first_pull_measures_the_disk_ollama_will_create_its_folder_on(
        self, tmp_path, monkeypatch
    ):
        target = tmp_path / "not" / "yet" / "models"
        monkeypatch.setenv("OLLAMA_MODELS", str(target))
        seen = []
        real = m.shutil.disk_usage

        def usage(path):
            seen.append(path)
            return real(path)

        monkeypatch.setattr(m.shutil, "disk_usage", usage)
        path, free, total = m.tightest_disk([])
        assert seen == [str(tmp_path)]
        assert free is not None and total


class TestSixthReviewFixes:
    def test_uncreated_ollama_models_counts_next_to_an_existing_home_folder(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(m.Path, "home", lambda: tmp_path)
        (tmp_path / ".ollama" / "models").mkdir(parents=True)
        target = tmp_path / "big" / "models"
        monkeypatch.setenv("OLLAMA_MODELS", str(target))
        dirs = m.ollama_model_dirs()
        assert dirs[0] == target and tmp_path / ".ollama" / "models" in dirs

    def test_odd_size_in_tags_does_not_crash(self, monkeypatch):
        import requests

        class Response:
            status_code = 200

            def json(self):
                return {"models": [{"name": "a", "size": "4.6 GB"}, {"name": "b", "size": None}]}

            def raise_for_status(self):
                pass

        monkeypatch.setattr(requests, "get", lambda *a, **k: Response())
        models = m.list_installed("http://localhost:11434")
        assert [(x.name, x.size) for x in models] == [("a", 0), ("b", 0)]


class TestEighthReviewFixes:
    @pytest.mark.parametrize("value", [None, "", "  ", 5])
    def test_blank_or_odd_base_url_means_the_default(self, value):
        oc = m.ollama_config({"providers": {"ollama": {"base_url": value, "model": None}}})
        assert oc["base_url"] == "http://localhost:11434"
        assert oc["model"] == DEFAULT_OLLAMA_MODEL

    def test_tags_with_models_not_a_list_is_unreadable(self, monkeypatch):
        monkeypatch.setattr(m, "_get_json", lambda url, **k: {"models": 1})
        assert m.list_installed("http://x") is None
