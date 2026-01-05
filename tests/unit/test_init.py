"""
Tests for hai-sh directory initialization.
"""

import os
import stat
from pathlib import Path

import pytest

from hai_sh.init import (
    create_default_config,
    get_config_path,
    get_directory_info,
    get_hai_dir,
    init_hai_directory,
    verify_hai_directory,
)


@pytest.mark.unit
def test_get_hai_dir():
    """Test that get_hai_dir returns correct path."""
    hai_dir = get_hai_dir()

    assert hai_dir.name == ".hai"
    assert hai_dir.parent == Path.home()
    assert str(hai_dir) == str(Path.home() / ".hai")


@pytest.mark.unit
def test_get_config_path():
    """Test that get_config_path returns correct path."""
    config_path = get_config_path()

    assert config_path.name == "config.yaml"
    assert config_path.parent.name == ".hai"
    assert str(config_path) == str(Path.home() / ".hai" / "config.yaml")


@pytest.mark.unit
def test_create_default_config():
    """Test that default config content is valid YAML."""
    config = create_default_config()

    assert isinstance(config, str)
    assert len(config) > 0
    assert "provider:" in config
    assert "ollama" in config
    assert "openai" in config
    assert "context:" in config

    # Verify it's valid YAML by parsing it
    import yaml

    parsed = yaml.safe_load(config)
    assert isinstance(parsed, dict)
    assert "provider" in parsed
    assert "providers" in parsed
    assert "context" in parsed


@pytest.mark.unit
def test_init_hai_directory_creates_structure(tmp_path, monkeypatch):
    """Test that init_hai_directory creates all required components."""
    # Use tmp_path as home directory
    monkeypatch.setenv("HOME", str(tmp_path))

    success, error = init_hai_directory()

    assert success is True
    assert error is None

    # Check main directory exists
    hai_dir = tmp_path / ".hai"
    assert hai_dir.exists()
    assert hai_dir.is_dir()

    # Check subdirectories exist
    assert (hai_dir / "logs").exists()
    assert (hai_dir / "logs").is_dir()
    assert (hai_dir / "cache").exists()
    assert (hai_dir / "cache").is_dir()

    # Check config file exists
    config_path = hai_dir / "config.yaml"
    assert config_path.exists()
    assert config_path.is_file()
    assert len(config_path.read_text()) > 0


@pytest.mark.unit
def test_init_hai_directory_permissions(tmp_path, monkeypatch):
    """Test that directory permissions are set correctly (700)."""
    monkeypatch.setenv("HOME", str(tmp_path))

    success, error = init_hai_directory()
    assert success is True

    hai_dir = tmp_path / ".hai"

    # Check main directory permissions (should be 700)
    mode = hai_dir.stat().st_mode
    perms = stat.S_IMODE(mode)
    assert perms == 0o700, f"Expected 0o700, got {oct(perms)}"

    # Check subdirectory permissions
    for subdir in ["logs", "cache"]:
        subdir_path = hai_dir / subdir
        mode = subdir_path.stat().st_mode
        perms = stat.S_IMODE(mode)
        assert perms == 0o700, f"{subdir} expected 0o700, got {oct(perms)}"

    # Check config file permissions (should be 600)
    config_path = hai_dir / "config.yaml"
    mode = config_path.stat().st_mode
    perms = stat.S_IMODE(mode)
    assert perms == 0o600, f"Config expected 0o600, got {oct(perms)}"


@pytest.mark.unit
def test_init_hai_directory_idempotent(tmp_path, monkeypatch):
    """Test that init_hai_directory can be called multiple times safely."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # First initialization
    success1, error1 = init_hai_directory()
    assert success1 is True
    assert error1 is None

    # Second initialization (should not fail)
    success2, error2 = init_hai_directory()
    assert success2 is True
    assert error2 is None

    # Directory should still exist and be valid
    hai_dir = tmp_path / ".hai"
    assert hai_dir.exists()
    assert hai_dir.is_dir()


@pytest.mark.unit
def test_init_hai_directory_force_recreate_config(tmp_path, monkeypatch):
    """Test that force=True recreates config file."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Initial setup
    init_hai_directory()
    config_path = tmp_path / ".hai" / "config.yaml"

    # Modify config
    original_content = config_path.read_text()
    config_path.write_text("# Modified config\nprovider: test")
    modified_content = config_path.read_text()
    assert modified_content != original_content

    # Reinitialize with force=True
    success, error = init_hai_directory(force=True)
    assert success is True

    # Config should be restored to default
    new_content = config_path.read_text()
    assert new_content == original_content
    assert "# Modified config" not in new_content


@pytest.mark.unit
def test_init_hai_directory_file_exists_error(tmp_path, monkeypatch):
    """Test error handling when .hai exists as a file instead of directory."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Create .hai as a file instead of directory
    hai_file = tmp_path / ".hai"
    hai_file.write_text("I'm a file, not a directory")

    success, error = init_hai_directory()

    assert success is False
    assert error is not None
    assert "not a directory" in error.lower()


@pytest.mark.unit
def test_verify_hai_directory_valid(tmp_path, monkeypatch):
    """Test verify_hai_directory with valid structure."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Initialize directory
    init_hai_directory()

    # Verify
    is_valid, missing = verify_hai_directory()

    assert is_valid is True
    assert len(missing) == 0


@pytest.mark.unit
def test_verify_hai_directory_missing_components(tmp_path, monkeypatch):
    """Test verify_hai_directory detects missing components."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Initialize but then remove some components
    init_hai_directory()

    hai_dir = tmp_path / ".hai"
    (hai_dir / "logs").rmdir()
    (hai_dir / "config.yaml").unlink()

    # Verify
    is_valid, missing = verify_hai_directory()

    assert is_valid is False
    assert len(missing) == 2
    assert any("logs" in str(m) for m in missing)
    assert any("config.yaml" in str(m) for m in missing)


@pytest.mark.unit
def test_verify_hai_directory_not_initialized(tmp_path, monkeypatch):
    """Test verify_hai_directory when directory doesn't exist."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Don't initialize, just verify
    is_valid, missing = verify_hai_directory()

    assert is_valid is False
    assert len(missing) > 0
    assert any(".hai" in str(m) for m in missing)


@pytest.mark.unit
def test_get_directory_info_not_initialized(tmp_path, monkeypatch):
    """Test get_directory_info when directory doesn't exist."""
    monkeypatch.setenv("HOME", str(tmp_path))

    info = get_directory_info()

    assert info["exists"] is False
    assert info["config_exists"] is False
    assert "hai_dir" in info
    assert "subdirs" in info


@pytest.mark.unit
def test_get_directory_info_initialized(tmp_path, monkeypatch):
    """Test get_directory_info after initialization."""
    monkeypatch.setenv("HOME", str(tmp_path))

    init_hai_directory()
    info = get_directory_info()

    assert info["exists"] is True
    assert info["config_exists"] is True
    assert info["permissions"] == "0o700"

    # Check subdirectories
    assert "logs" in info["subdirs"]
    assert "cache" in info["subdirs"]
    assert info["subdirs"]["logs"]["exists"] is True
    assert info["subdirs"]["cache"]["exists"] is True


@pytest.mark.unit
def test_init_preserves_existing_config_content(tmp_path, monkeypatch):
    """Test that init doesn't overwrite existing config without force."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Initial setup
    init_hai_directory()
    config_path = tmp_path / ".hai" / "config.yaml"

    # Modify config
    custom_content = "# My custom config\nprovider: custom\n"
    config_path.write_text(custom_content)

    # Reinitialize without force
    success, error = init_hai_directory(force=False)
    assert success is True

    # Config should be preserved
    assert config_path.read_text() == custom_content


@pytest.mark.unit
def test_default_config_yaml_structure():
    """Test that default config has expected YAML structure."""
    import yaml

    config_text = create_default_config()
    config = yaml.safe_load(config_text)

    # Test top-level keys
    assert "provider" in config
    assert "providers" in config
    assert "context" in config
    assert "output" in config

    # Test providers structure
    assert "openai" in config["providers"]
    assert "anthropic" in config["providers"]
    assert "ollama" in config["providers"]

    # Test context settings
    assert "include_history" in config["context"]
    assert "include_git_state" in config["context"]

    # Test output settings
    assert "show_conversation" in config["output"]
    assert "use_colors" in config["output"]
