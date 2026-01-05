"""
Directory initialization and management for hai-sh.

This module handles creation and setup of the ~/.hai/ directory structure
for storing configuration files, logs, and cache data.
"""

import os
import stat
from pathlib import Path
from typing import Optional

# Default directory structure
HAI_DIR_NAME = ".hai"
DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_SUBDIRS = ["logs", "cache"]


def get_hai_dir() -> Path:
    """
    Get the path to the hai configuration directory.

    Returns:
        Path: Path to ~/.hai/ directory

    Example:
        >>> hai_dir = get_hai_dir()
        >>> print(hai_dir)
        /home/user/.hai
    """
    home = Path.home()
    return home / HAI_DIR_NAME


def get_config_path() -> Path:
    """
    Get the path to the hai configuration file.

    Returns:
        Path: Path to ~/.hai/config.yaml

    Example:
        >>> config_path = get_config_path()
        >>> print(config_path)
        /home/user/.hai/config.yaml
    """
    return get_hai_dir() / DEFAULT_CONFIG_FILE


def create_default_config() -> str:
    """
    Generate default configuration content.

    Returns:
        str: Default YAML configuration content

    Example:
        >>> config = create_default_config()
        >>> print(config)
        # hai-sh configuration file
        ...
    """
    return """# hai-sh configuration file
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
    model: "llama3.2"

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


def init_hai_directory(force: bool = False) -> tuple[bool, Optional[str]]:
    """
    Initialize the ~/.hai/ directory structure.

    Creates the main directory, subdirectories, and default config file
    if they don't exist. Sets proper permissions (700) for security.

    Args:
        force: If True, recreate config file even if it exists

    Returns:
        tuple: (success: bool, error_message: Optional[str])
            - success: True if initialization succeeded
            - error_message: Error description if failed, None otherwise

    Example:
        >>> success, error = init_hai_directory()
        >>> if success:
        ...     print("Initialization successful")
        ... else:
        ...     print(f"Error: {error}")

    Note:
        Directory permissions are set to 700 (rwx------) for security.
        Config file permissions are set to 600 (rw-------).
    """
    try:
        hai_dir = get_hai_dir()

        # Create main directory
        if not hai_dir.exists():
            hai_dir.mkdir(mode=0o700, parents=True)
            # Explicitly set permissions in case umask interferes
            hai_dir.chmod(stat.S_IRWXU)  # 700: rwx------
        elif not hai_dir.is_dir():
            return False, f"{hai_dir} exists but is not a directory"

        # Create subdirectories
        for subdir in DEFAULT_SUBDIRS:
            subdir_path = hai_dir / subdir
            if not subdir_path.exists():
                subdir_path.mkdir(mode=0o700, parents=True)
                subdir_path.chmod(stat.S_IRWXU)

        # Create default config file if it doesn't exist (or force is True)
        config_path = get_config_path()
        if not config_path.exists() or force:
            config_content = create_default_config()
            config_path.write_text(config_content)
            # Set config file permissions to 600 (rw-------)
            config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

        return True, None

    except PermissionError as e:
        return False, f"Permission denied: {e}"
    except OSError as e:
        return False, f"OS error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def verify_hai_directory() -> tuple[bool, list[str]]:
    """
    Verify that the ~/.hai/ directory structure is properly set up.

    Checks for existence of main directory, subdirectories, and config file.

    Returns:
        tuple: (is_valid: bool, missing_items: list[str])
            - is_valid: True if all components exist
            - missing_items: List of missing components (empty if all exist)

    Example:
        >>> is_valid, missing = verify_hai_directory()
        >>> if is_valid:
        ...     print("Directory structure is valid")
        ... else:
        ...     print(f"Missing: {', '.join(missing)}")
    """
    missing = []
    hai_dir = get_hai_dir()

    # Check main directory
    if not hai_dir.exists():
        missing.append(str(hai_dir))
        return False, missing

    if not hai_dir.is_dir():
        missing.append(f"{hai_dir} (not a directory)")
        return False, missing

    # Check subdirectories
    for subdir in DEFAULT_SUBDIRS:
        subdir_path = hai_dir / subdir
        if not subdir_path.exists():
            missing.append(str(subdir_path))
        elif not subdir_path.is_dir():
            missing.append(f"{subdir_path} (not a directory)")

    # Check config file
    config_path = get_config_path()
    if not config_path.exists():
        missing.append(str(config_path))
    elif not config_path.is_file():
        missing.append(f"{config_path} (not a file)")

    is_valid = len(missing) == 0
    return is_valid, missing


def get_directory_info() -> dict[str, any]:
    """
    Get information about the hai directory structure.

    Returns:
        dict: Dictionary containing directory information:
            - hai_dir: Path to main directory
            - exists: Whether directory exists
            - config_path: Path to config file
            - config_exists: Whether config exists
            - subdirs: Dictionary of subdirectory paths and existence
            - permissions: Octal permissions of main directory (if exists)

    Example:
        >>> info = get_directory_info()
        >>> print(f"Config exists: {info['config_exists']}")
    """
    hai_dir = get_hai_dir()
    config_path = get_config_path()

    info = {
        "hai_dir": hai_dir,
        "exists": hai_dir.exists(),
        "config_path": config_path,
        "config_exists": config_path.exists(),
        "subdirs": {},
    }

    # Add subdirectory info
    for subdir in DEFAULT_SUBDIRS:
        subdir_path = hai_dir / subdir
        info["subdirs"][subdir] = {
            "path": subdir_path,
            "exists": subdir_path.exists(),
        }

    # Add permissions if directory exists
    if info["exists"]:
        try:
            mode = hai_dir.stat().st_mode
            info["permissions"] = oct(stat.S_IMODE(mode))
        except OSError:
            info["permissions"] = None

    return info
