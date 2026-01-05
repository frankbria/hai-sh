"""
Context collection for hai-sh.

This module handles collecting contextual information about the current
environment to provide to the LLM, including:
- Current working directory
- Git repository state
- Environment variables
- Shell history
"""

import os
import stat
import subprocess
from pathlib import Path
from typing import Any, Optional

# Cache for git availability check (avoids repeated subprocess calls)
_git_available: Optional[bool] = None


def _reset_git_cache() -> None:
    """Reset the git availability cache (for testing)."""
    global _git_available
    _git_available = None


def get_cwd_context() -> dict[str, Any]:
    """
    Collect context information about the current working directory.

    Returns:
        dict: Dictionary containing CWD information with keys:
            - cwd: Absolute path to current working directory
            - exists: Whether the directory exists
            - readable: Whether the directory is readable
            - writable: Whether the directory is writable
            - size: Number of items in directory (if accessible)
            - error: Error message if collection failed

    Example:
        >>> context = get_cwd_context()
        >>> print(context['cwd'])
        '/home/user/project'
        >>> print(context['readable'])
        True
    """
    context = {
        "cwd": None,
        "exists": False,
        "readable": False,
        "writable": False,
        "size": 0,
        "error": None,
    }

    try:
        # Get current working directory
        cwd = os.getcwd()
        context["cwd"] = cwd

        # Check if directory exists (should always be True for cwd)
        cwd_path = Path(cwd)
        context["exists"] = cwd_path.exists()

        if not context["exists"]:
            context["error"] = "Current directory does not exist"
            return context

        # Check readability
        try:
            # Try to list directory contents
            _ = os.listdir(cwd)
            context["readable"] = True

            # Count items in directory
            context["size"] = len(list(cwd_path.iterdir()))

        except PermissionError:
            context["readable"] = False
            context["error"] = "Permission denied reading directory"
        except OSError as e:
            context["readable"] = False
            context["error"] = f"Error reading directory: {e}"

        # Check writability
        try:
            # Check if we can write to the directory
            if os.access(cwd, os.W_OK):
                context["writable"] = True
            else:
                context["writable"] = False
        except OSError:
            context["writable"] = False

    except OSError as e:
        context["error"] = f"Error getting current directory: {e}"
    except Exception as e:
        context["error"] = f"Unexpected error: {e}"

    return context


def get_directory_info(path: str) -> dict[str, Any]:
    """
    Get detailed information about a specific directory.

    Args:
        path: Path to directory to inspect

    Returns:
        dict: Dictionary containing directory information with keys:
            - path: Absolute path to directory
            - exists: Whether the directory exists
            - is_dir: Whether the path is a directory
            - readable: Whether the directory is readable
            - writable: Whether the directory is writable
            - executable: Whether the directory is executable
            - size: Number of items in directory (if accessible)
            - permissions: Octal permissions string (e.g., '755')
            - error: Error message if collection failed

    Example:
        >>> info = get_directory_info('/tmp')
        >>> print(info['exists'])
        True
        >>> print(info['writable'])
        True
    """
    dir_path = Path(path).resolve()

    info = {
        "path": str(dir_path),
        "exists": False,
        "is_dir": False,
        "readable": False,
        "writable": False,
        "executable": False,
        "size": 0,
        "permissions": None,
        "error": None,
    }

    try:
        # Check if path exists
        info["exists"] = dir_path.exists()

        if not info["exists"]:
            info["error"] = "Directory does not exist"
            return info

        # Check if it's a directory
        info["is_dir"] = dir_path.is_dir()

        if not info["is_dir"]:
            info["error"] = "Path is not a directory"
            return info

        # Get permissions
        try:
            st = dir_path.stat()
            # Convert to octal string (e.g., '755')
            info["permissions"] = oct(st.st_mode)[-3:]
        except OSError as e:
            info["error"] = f"Error getting permissions: {e}"

        # Check readability
        try:
            _ = os.listdir(str(dir_path))
            info["readable"] = True
            info["size"] = len(list(dir_path.iterdir()))
        except PermissionError:
            info["readable"] = False
            if not info["error"]:
                info["error"] = "Permission denied reading directory"
        except OSError as e:
            info["readable"] = False
            if not info["error"]:
                info["error"] = f"Error reading directory: {e}"

        # Check writability
        try:
            info["writable"] = os.access(str(dir_path), os.W_OK)
        except OSError:
            info["writable"] = False

        # Check executability (for directories, this means ability to cd into it)
        try:
            info["executable"] = os.access(str(dir_path), os.X_OK)
        except OSError:
            info["executable"] = False

    except Exception as e:
        info["error"] = f"Unexpected error: {e}"

    return info


def format_cwd_context(context: dict[str, Any]) -> str:
    """
    Format CWD context as human-readable string.

    Args:
        context: Context dictionary from get_cwd_context()

    Returns:
        str: Formatted context string

    Example:
        >>> context = get_cwd_context()
        >>> print(format_cwd_context(context))
        Current Directory: /home/user/project
        Status: readable, writable
        Items: 15
    """
    lines = []

    if context.get("error"):
        lines.append(f"Error: {context['error']}")
        if context.get("cwd"):
            lines.append(f"Directory: {context['cwd']}")
        return "\n".join(lines)

    lines.append(f"Current Directory: {context.get('cwd', 'unknown')}")

    # Build status line
    status_parts = []
    if context.get("readable"):
        status_parts.append("readable")
    else:
        status_parts.append("not readable")

    if context.get("writable"):
        status_parts.append("writable")
    else:
        status_parts.append("read-only")

    lines.append(f"Status: {', '.join(status_parts)}")

    if context.get("readable") and context.get("size") is not None:
        lines.append(f"Items: {context['size']}")

    return "\n".join(lines)


def _is_git_available() -> tuple[bool, Optional[str]]:
    """
    Check if git is available (cached for definitive results only).

    Returns:
        tuple: (is_available, error_message)
            - is_available: True if git is installed and accessible
            - error_message: None if available, error description otherwise
    """
    global _git_available

    # Use cached result if available (only caches definitive answers)
    if _git_available is not None:
        if _git_available:
            return True, None
        else:
            return False, "Git is not installed or not in PATH"

    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        _git_available = result.returncode == 0
        if _git_available:
            return True, None
        else:
            return False, "Git is not installed or not in PATH"
    except FileNotFoundError:
        # Permanent error - cache it
        _git_available = False
        return False, "Git is not installed"
    except subprocess.TimeoutExpired:
        # Transient error - don't cache
        return False, "Git command timed out"


def get_git_context(directory: Optional[str] = None) -> dict[str, Any]:
    """
    Collect git repository information for a directory.

    Args:
        directory: Directory to check (default: current working directory)

    Returns:
        dict: Dictionary containing git information with keys:
            - is_git_repo: Whether directory is in a git repository
            - branch: Current branch name (if in git repo)
            - is_clean: Whether working directory is clean
            - has_staged: Whether there are staged changes
            - has_unstaged: Whether there are unstaged changes
            - has_untracked: Whether there are untracked files
            - commit_hash: Short commit hash (if available)
            - error: Error message if collection failed

    Example:
        >>> context = get_git_context()
        >>> if context['is_git_repo']:
        ...     print(f"Branch: {context['branch']}")
        ...     print(f"Clean: {context['is_clean']}")
    """
    context = {
        "is_git_repo": False,
        "branch": None,
        "is_clean": True,
        "has_staged": False,
        "has_unstaged": False,
        "has_untracked": False,
        "commit_hash": None,
        "error": None,
    }

    try:
        # Determine directory to check
        if directory is None:
            directory = os.getcwd()

        # Check if git is installed (cached check)
        is_available, error_msg = _is_git_available()
        if not is_available:
            context["error"] = error_msg
            return context

        # Check if directory is in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            # Not a git repository
            return context

        context["is_git_repo"] = True

        # Get current branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            context["branch"] = result.stdout.strip()

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            context["commit_hash"] = result.stdout.strip()

        # Check git status to determine if clean
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            status_lines = result.stdout.strip().split("\n")
            if status_lines == [""]:
                # Empty output means clean
                context["is_clean"] = True
            else:
                context["is_clean"] = False

                # Parse status to detect staged/unstaged/untracked
                for line in status_lines:
                    if not line:
                        continue

                    # First character is staged status, second is unstaged
                    staged = line[0]
                    unstaged = line[1] if len(line) > 1 else " "

                    if staged != " " and staged != "?":
                        context["has_staged"] = True
                    if unstaged != " ":
                        context["has_unstaged"] = True
                    if staged == "?" and unstaged == "?":
                        context["has_untracked"] = True

    except subprocess.TimeoutExpired:
        context["error"] = "Git command timed out"
    except OSError as e:
        context["error"] = f"Error running git command: {e}"
    except Exception as e:
        context["error"] = f"Unexpected error: {e}"

    return context


def format_git_context(context: dict[str, Any]) -> str:
    """
    Format git context as human-readable string.

    Args:
        context: Context dictionary from get_git_context()

    Returns:
        str: Formatted git context string

    Example:
        >>> context = get_git_context()
        >>> print(format_git_context(context))
        Git Repository: Yes
        Branch: main
        Status: clean
    """
    lines = []

    if context.get("error"):
        lines.append(f"Git Error: {context['error']}")
        return "\n".join(lines)

    if not context.get("is_git_repo"):
        lines.append("Git Repository: No")
        return "\n".join(lines)

    lines.append("Git Repository: Yes")

    if context.get("branch"):
        branch = context["branch"]
        if context.get("commit_hash"):
            branch = f"{branch} ({context['commit_hash']})"
        lines.append(f"Branch: {branch}")

    # Build status line
    if context.get("is_clean"):
        lines.append("Status: clean")
    else:
        status_parts = []
        if context.get("has_staged"):
            status_parts.append("staged changes")
        if context.get("has_unstaged"):
            status_parts.append("unstaged changes")
        if context.get("has_untracked"):
            status_parts.append("untracked files")

        if status_parts:
            lines.append(f"Status: {', '.join(status_parts)}")
        else:
            lines.append("Status: dirty")

    return "\n".join(lines)


def get_env_context(include_path: bool = True, max_path_length: int = 500) -> dict[str, Any]:
    """
    Collect relevant environment variables for LLM context.

    Collects USER, HOME, SHELL, and optionally PATH environment variables.
    Sanitizes PATH to prevent exposing too much information and handles
    missing variables gracefully.

    Args:
        include_path: Whether to include PATH variable (default: True)
        max_path_length: Maximum length for PATH string (default: 500)

    Returns:
        dict: Dictionary containing environment variables with keys:
            - user: Username from USER or LOGNAME env var
            - home: Home directory from HOME env var
            - shell: Shell from SHELL env var
            - path: PATH variable (if include_path=True, truncated if needed)
            - path_truncated: Whether PATH was truncated
            - missing: List of missing environment variables

    Example:
        >>> context = get_env_context()
        >>> print(context['user'])
        'frankbria'
        >>> print(context['shell'])
        '/bin/bash'
    """
    context = {
        "user": None,
        "home": None,
        "shell": None,
        "path": None,
        "path_truncated": False,
        "missing": [],
    }

    # Get USER (try USER first, then LOGNAME as fallback)
    context["user"] = os.environ.get("USER") or os.environ.get("LOGNAME")
    if not context["user"]:
        context["missing"].append("USER")

    # Get HOME
    context["home"] = os.environ.get("HOME")
    if not context["home"]:
        context["missing"].append("HOME")

    # Get SHELL
    context["shell"] = os.environ.get("SHELL")
    if not context["shell"]:
        context["missing"].append("SHELL")

    # Get PATH if requested
    if include_path:
        path = os.environ.get("PATH")
        if path:
            # Truncate PATH if too long
            if len(path) > max_path_length:
                context["path"] = path[:max_path_length] + "..."
                context["path_truncated"] = True
            else:
                context["path"] = path
                context["path_truncated"] = False
        else:
            context["missing"].append("PATH")

    return context


def is_sensitive_env_var(var_name: str) -> bool:
    """
    Check if an environment variable name looks sensitive (enhanced security).

    Identifies common patterns for sensitive variables like API keys,
    passwords, tokens, secrets, etc. Uses comprehensive pattern matching
    to catch edge cases and provider-specific naming conventions.

    Args:
        var_name: Environment variable name to check

    Returns:
        bool: True if variable appears to contain sensitive data

    Example:
        >>> is_sensitive_env_var("API_KEY")
        True
        >>> is_sensitive_env_var("OPENAI_SK")
        True
        >>> is_sensitive_env_var("HOME")
        False
    """
    var_name_upper = var_name.upper()

    # Exact matches (highly sensitive standalone names)
    exact_sensitive = {
        "PASSWORD", "SECRET", "TOKEN", "KEY",
        "PASSWD", "PWD", "API", "SK",
    }
    if var_name_upper in exact_sensitive:
        return True

    # Comprehensive patterns for sensitive variables
    sensitive_patterns = [
        # Generic credentials
        "KEY", "SECRET", "PASSWORD", "PASSWD", "PWD",
        "TOKEN", "AUTH", "CREDENTIAL", "PRIVATE",

        # API-specific
        "API_KEY", "APIKEY", "API_SECRET", "ACCESS_KEY",
        "SECRET_KEY", "CLIENT_SECRET", "CLIENT_ID",

        # OAuth/Session
        "SESSION", "COOKIE", "CSRF", "JWT",
        "BEARER", "ACCESS_TOKEN", "REFRESH_TOKEN",

        # Database
        "DB_PASSWORD", "DATABASE_URL", "CONNECTION_STRING",
        "MONGODB_URI", "POSTGRES_PASSWORD", "MYSQL_PASSWORD",
        "DB_PASS", "DATABASE_PASSWORD",

        # Cloud Providers
        "AWS_SECRET", "AWS_ACCESS_KEY_ID", "AWS_SESSION_TOKEN",
        "AZURE_", "GCP_", "GOOGLE_APPLICATION_CREDENTIALS",
        "DIGITALOCEAN_", "HEROKU_API_KEY",

        # Service-specific (common third-party services)
        "OPENAI", "ANTHROPIC", "SLACK_", "GITHUB_TOKEN",
        "STRIPE_", "TWILIO_", "SENDGRID_",
        "FIREBASE_", "SUPABASE_", "VERCEL_",

        # SSH and encryption
        "SSH_", "GPG_", "PGP_", "ENCRYPTION_",
        "PRIVATE_KEY", "PASSPHRASE",

        # Generic security markers
        "CREDENTIALS", "SECURE_", "_SK", "_SECRET",
    ]

    # Check if any sensitive pattern is in the variable name
    for pattern in sensitive_patterns:
        if pattern in var_name_upper:
            return True

    return False


def get_safe_env_vars(exclude_patterns: Optional[list[str]] = None) -> dict[str, str]:
    """
    Get non-sensitive environment variables safe to share with LLM.

    Filters out variables that appear to contain sensitive information
    like API keys, passwords, tokens, etc.

    Args:
        exclude_patterns: Additional patterns to exclude (case-insensitive)

    Returns:
        dict: Dictionary of safe environment variables

    Example:
        >>> env = get_safe_env_vars()
        >>> 'HOME' in env
        True
        >>> 'API_KEY' in env  # Would be filtered out
        False
    """
    safe_vars = {}
    exclude_patterns = exclude_patterns or []

    for var_name, var_value in os.environ.items():
        # Skip if sensitive
        if is_sensitive_env_var(var_name):
            continue

        # Skip if matches exclude patterns
        skip = False
        for pattern in exclude_patterns:
            if pattern.upper() in var_name.upper():
                skip = True
                break

        if skip:
            continue

        safe_vars[var_name] = var_value

    return safe_vars


def format_env_context(context: dict[str, Any]) -> str:
    """
    Format environment context as human-readable string.

    Args:
        context: Context dictionary from get_env_context()

    Returns:
        str: Formatted environment context string

    Example:
        >>> context = get_env_context()
        >>> print(format_env_context(context))
        User: frankbria
        Home: /home/frankbria
        Shell: /bin/bash
        PATH: /usr/local/bin:/usr/bin:... (truncated)
    """
    lines = []

    if context.get("user"):
        lines.append(f"User: {context['user']}")

    if context.get("home"):
        lines.append(f"Home: {context['home']}")

    if context.get("shell"):
        lines.append(f"Shell: {context['shell']}")

    if context.get("path"):
        path_line = f"PATH: {context['path']}"
        if context.get("path_truncated"):
            path_line += " (truncated)"
        lines.append(path_line)

    if context.get("missing"):
        lines.append(f"Missing: {', '.join(context['missing'])}")

    return "\n".join(lines)
