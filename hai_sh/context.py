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


def _format_file_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format (B, KB, MB, GB).

    Args:
        size_bytes: File size in bytes

    Returns:
        str: Human-readable file size

    Example:
        >>> _format_file_size(1024)
        '1.0 KB'
        >>> _format_file_size(1536)
        '1.5 KB'
        >>> _format_file_size(1048576)
        '1.0 MB'
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _filter_files_by_relevance(
    files: list[dict[str, Any]],
    query: str,
    max_files: int
) -> list[dict[str, Any]]:
    """
    Score files based on query relevance (case-insensitive substring matching).

    Args:
        files: List of file dictionaries
        query: User query for relevance scoring
        max_files: Maximum number of files to return

    Returns:
        list: Filtered and sorted list of files by relevance

    Example:
        >>> files = [{'name': 'test.py', 'type': 'file'}, {'name': 'data.txt', 'type': 'file'}]
        >>> _filter_files_by_relevance(files, 'test', 10)
        [{'name': 'test.py', 'type': 'file'}]
    """
    if not query:
        return files[:max_files]

    query_lower = query.lower()
    scored_files = []

    for file_info in files:
        name_lower = file_info['name'].lower()
        score = 0

        # Exact match gets highest score
        if name_lower == query_lower:
            score = 1000
        # Name starts with query
        elif name_lower.startswith(query_lower):
            score = 500
        # Query is substring of name
        elif query_lower in name_lower:
            score = 100
        # Check individual query words
        else:
            query_words = query_lower.split()
            for word in query_words:
                if word in name_lower:
                    score += 10

        if score > 0:
            scored_files.append((score, file_info))

    # Sort by score descending, then by name
    scored_files.sort(key=lambda x: (-x[0], x[1]['name'].lower()))

    # Return top max_files
    return [file_info for _, file_info in scored_files[:max_files]]


def get_file_listing_context(
    directory: Optional[str] = None,
    max_files: int = 20,
    max_depth: int = 1,
    show_hidden: bool = False,
    query: Optional[str] = None
) -> dict[str, Any]:
    """
    Collect file listing with efficient directory traversal.

    Args:
        directory: Absolute path to directory (default: current working directory)
        max_files: Maximum files to include in listing
        max_depth: Directory depth to scan (0=current only, 1=one level deep)
        show_hidden: Include hidden files (starting with '.')
        query: Optional query for relevance filtering

    Returns:
        dict: Dictionary containing file listing with keys:
            - directory: Absolute path to directory
            - files: List of file dicts with keys: name, type (file/dir), size, modified
            - total_count: Total number of items found
            - truncated: Boolean indicating if list was truncated
            - depth: Depth level scanned
            - error: Error message if collection failed

    Example:
        >>> context = get_file_listing_context()
        >>> print(context['directory'])
        '/home/user/project'
        >>> print(context['files'][0])
        {'name': 'README.md', 'type': 'file', 'size': 1024, 'modified': 1234567890}
    """
    context = {
        "directory": None,
        "files": [],
        "total_count": 0,
        "truncated": False,
        "depth": max_depth,
        "error": None,
    }

    try:
        # Determine directory to scan
        if directory is None:
            directory = os.getcwd()

        directory = os.path.abspath(directory)
        context["directory"] = directory

        # Check if directory exists
        dir_path = Path(directory)
        if not dir_path.exists():
            context["error"] = "Directory does not exist"
            return context

        if not dir_path.is_dir():
            context["error"] = "Path is not a directory"
            return context

        # Collect files using os.scandir for efficiency
        all_files = []

        def scan_directory(path: Path, current_depth: int):
            """Recursively scan directory up to max_depth."""
            if current_depth > max_depth:
                return

            try:
                with os.scandir(path) as entries:
                    for entry in entries:
                        # Skip hidden files unless show_hidden is True
                        if not show_hidden and entry.name.startswith('.'):
                            continue

                        try:
                            # Get file info
                            stat_info = entry.stat(follow_symlinks=False)

                            file_info = {
                                "name": entry.name if current_depth == 0 else str(Path(entry.path).relative_to(dir_path)),
                                "type": "dir" if entry.is_dir(follow_symlinks=False) else "file",
                                "size": stat_info.st_size,
                                "modified": stat_info.st_mtime,
                            }

                            all_files.append(file_info)

                            # Recurse into subdirectories if within depth limit
                            if entry.is_dir(follow_symlinks=False) and current_depth < max_depth:
                                scan_directory(Path(entry.path), current_depth + 1)

                        except (PermissionError, OSError):
                            # Skip files we can't access
                            continue

            except PermissionError:
                if current_depth == 0:
                    context["error"] = "Permission denied reading directory"
            except OSError as e:
                if current_depth == 0:
                    context["error"] = f"Error reading directory: {e}"

        # Scan the directory
        scan_directory(dir_path, 0)

        # Sort: directories first, then by name (case-insensitive)
        all_files.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))

        # Track total count before filtering
        context["total_count"] = len(all_files)

        # Filter by relevance if query provided
        if query:
            filtered_files = _filter_files_by_relevance(all_files, query, max_files)
        else:
            filtered_files = all_files[:max_files]

        context["files"] = filtered_files
        if query:
            context["truncated"] = len(_filter_files_by_relevance(all_files, query, len(all_files))) > max_files
        else:
            context["truncated"] = len(all_files) > max_files

    except OSError as e:
        context["error"] = f"Error accessing directory: {e}"
    except Exception as e:
        context["error"] = f"Unexpected error: {e}"

    return context


def format_file_listing_context(context: dict[str, Any]) -> str:
    """
    Format file listing as human-readable output.

    Args:
        context: Context dictionary from get_file_listing_context()

    Returns:
        str: Formatted file listing string

    Example:
        >>> context = get_file_listing_context()
        >>> print(format_file_listing_context(context))
        Files in /home/user/project (showing 20 of 150):
          dir1/
          dir2/
          file1.txt (1.2 KB)
          file2.py (3.4 KB)
        (truncated, showing 20 of 150 files)
    """
    lines = []

    if context.get("error"):
        lines.append(f"Error listing files: {context['error']}")
        if context.get("directory"):
            lines.append(f"Directory: {context['directory']}")
        return "\n".join(lines)

    directory = context.get("directory", "unknown")
    files = context.get("files", [])
    total_count = context.get("total_count", 0)
    truncated = context.get("truncated", False)

    # Header
    if truncated:
        lines.append(f"Files in {directory} (showing {len(files)} of {total_count}):")
    else:
        lines.append(f"Files in {directory} ({total_count} items):")

    # List files
    if not files:
        lines.append("  (empty)")
    else:
        for file_info in files:
            name = file_info['name']
            file_type = file_info['type']

            if file_type == 'dir':
                # Add trailing slash for directories
                lines.append(f"  {name}/")
            else:
                size = file_info.get('size')
                if isinstance(size, int):
                    size_str = _format_file_size(size)
                    lines.append(f"  {name} ({size_str})")
                else:
                    lines.append(f"  {name}")

    # Footer if truncated
    if truncated:
        lines.append(f"(truncated, showing {len(files)} of {total_count} files)")

    return "\n".join(lines)


# ============================================================================
# Shell History Collection
# ============================================================================


def _detect_shell_type() -> str:
    """
    Detect the current shell type from SHELL environment variable.

    Returns:
        str: Shell type ('bash', 'zsh', 'fish', or 'unknown')

    Example:
        >>> os.environ['SHELL'] = '/bin/bash'
        >>> _detect_shell_type()
        'bash'
    """
    shell_path = os.environ.get("SHELL", "")
    shell_name = Path(shell_path).name.lower() if shell_path else ""

    if "bash" in shell_name:
        return "bash"
    elif "zsh" in shell_name:
        return "zsh"
    elif "fish" in shell_name:
        return "fish"
    else:
        return "unknown"


def _get_history_file_path(shell_type: str) -> Optional[Path]:
    """
    Get the history file path for the given shell type.

    Args:
        shell_type: The shell type ('bash', 'zsh', 'fish', or 'unknown')

    Returns:
        Path: Path to history file if it exists, None otherwise

    Example:
        >>> _get_history_file_path('bash')
        PosixPath('/home/user/.bash_history')
    """
    home = os.environ.get("HOME", "")
    if not home:
        return None

    home_path = Path(home)

    history_paths = {
        "bash": home_path / ".bash_history",
        "zsh": home_path / ".zsh_history",
        "fish": home_path / ".local" / "share" / "fish" / "fish_history",
    }

    history_file = history_paths.get(shell_type)

    if history_file and history_file.exists():
        return history_file

    return None


def _is_sensitive_command(command: str) -> bool:
    """
    Check if a command appears to contain sensitive information.

    Filters out commands that contain passwords, API keys, tokens, etc.

    Args:
        command: Shell command to check

    Returns:
        bool: True if command contains sensitive information

    Example:
        >>> _is_sensitive_command('export API_KEY=secret')
        True
        >>> _is_sensitive_command('ls -la')
        False
    """
    command_upper = command.upper()

    # Patterns indicating sensitive data
    sensitive_patterns = [
        # Credentials
        "PASSWORD", "PASSWD", "PWD=",
        "SECRET", "TOKEN", "CREDENTIAL",
        # API keys
        "API_KEY", "APIKEY", "API_SECRET",
        "ACCESS_KEY", "SECRET_KEY",
        # Auth headers
        "AUTHORIZATION:", "BEARER ",
        # Database
        "-P", "-PPASSWORD",  # MySQL password flag
        "MYSQL_PWD",
        # SSH
        "SSH-ADD", "SSH -I",
        # Cloud
        "AWS_SECRET", "OPENAI_API", "ANTHROPIC_API",
        # Env exports of sensitive vars
        "PRIVATE_KEY",
    ]

    for pattern in sensitive_patterns:
        if pattern in command_upper:
            return True

    # Check for password flags in common commands
    # e.g., mysql -u root -ppassword
    if "-P" in command and ("MYSQL" in command_upper or "PSQL" in command_upper):
        return True

    return False


def _parse_bash_history(lines: list[str]) -> list[str]:
    """
    Parse bash history format (simple line-based).

    Args:
        lines: Lines from .bash_history file

    Returns:
        list: Parsed commands
    """
    commands = []
    for line in lines:
        line = line.strip()
        if line:
            commands.append(line)
    return commands


def _parse_zsh_history(lines: list[str]) -> list[str]:
    """
    Parse zsh extended history format.

    Zsh format: `: timestamp:duration;command`

    Args:
        lines: Lines from .zsh_history file

    Returns:
        list: Parsed commands
    """
    commands = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for extended history format
        if line.startswith(": ") and ";" in line:
            # Extract command after the semicolon
            semicolon_idx = line.find(";")
            if semicolon_idx != -1:
                command = line[semicolon_idx + 1:].strip()
                if command:
                    commands.append(command)
        else:
            # Simple format, just add the line
            commands.append(line)

    return commands


def _parse_fish_history(content: str) -> list[str]:
    """
    Parse fish shell history format (YAML-like).

    Fish format:
        - cmd: command here
          when: timestamp

    Args:
        content: Content of fish_history file

    Returns:
        list: Parsed commands
    """
    commands = []
    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if line.startswith("- cmd:"):
            # Extract command after "- cmd:"
            command = line[6:].strip()
            if command:
                commands.append(command)

    return commands


def get_shell_history(length: int = 10) -> dict[str, Any]:
    """
    Collect shell history from the current shell's history file.

    Detects the shell type, reads the appropriate history file,
    and filters out sensitive commands.

    Args:
        length: Maximum number of recent commands to include (default: 10)

    Returns:
        dict: Dictionary containing shell history with keys:
            - commands: List of recent commands (filtered for sensitive data)
            - shell_type: Type of shell ('bash', 'zsh', 'fish', 'unknown')
            - total_count: Total number of commands in history
            - filtered_count: Number of commands filtered out for sensitivity
            - error: Error message if collection failed

    Example:
        >>> context = get_shell_history(length=5)
        >>> print(context['shell_type'])
        'bash'
        >>> print(context['commands'])
        ['ls -la', 'git status', 'cd projects']
    """
    context = {
        "commands": [],
        "shell_type": "unknown",
        "total_count": 0,
        "filtered_count": 0,
        "error": None,
    }

    try:
        # Detect shell type
        shell_type = _detect_shell_type()
        context["shell_type"] = shell_type

        # Get history file path
        history_path = _get_history_file_path(shell_type)

        if history_path is None:
            context["error"] = f"History file not found for {shell_type} shell"
            return context

        # Read history file
        try:
            with open(history_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except PermissionError:
            context["error"] = "Permission denied reading history file"
            return context
        except OSError as e:
            context["error"] = f"Error reading history file: {e}"
            return context

        # Parse based on shell type
        if shell_type == "fish":
            all_commands = _parse_fish_history(content)
        elif shell_type == "zsh":
            lines = content.split("\n")
            all_commands = _parse_zsh_history(lines)
        else:
            # Default to bash parsing
            lines = content.split("\n")
            all_commands = _parse_bash_history(lines)

        context["total_count"] = len(all_commands)

        # Filter sensitive commands and get last N
        filtered_commands = []
        filtered_count = 0

        for command in all_commands:
            if _is_sensitive_command(command):
                filtered_count += 1
            else:
                filtered_commands.append(command)

        context["filtered_count"] = filtered_count

        # Get last N commands (most recent)
        context["commands"] = filtered_commands[-length:] if length > 0 else []

    except Exception as e:
        context["error"] = f"Unexpected error: {e}"

    return context


def format_shell_history(context: dict[str, Any]) -> str:
    """
    Format shell history context as human-readable string.

    Args:
        context: Context dictionary from get_shell_history()

    Returns:
        str: Formatted shell history string

    Example:
        >>> context = get_shell_history()
        >>> print(format_shell_history(context))
        Recent Commands (bash):
          1. ls -la
          2. git status
          3. cd projects
    """
    lines = []

    if context.get("error"):
        lines.append(f"Shell History Error: {context['error']}")
        return "\n".join(lines)

    commands = context.get("commands", [])
    shell_type = context.get("shell_type", "unknown")
    filtered_count = context.get("filtered_count", 0)

    if not commands:
        return ""  # Empty history, don't add noise

    # Header
    lines.append(f"Recent Commands ({shell_type}):")

    # Limit display to reasonable number
    display_commands = commands[-10:]  # Show at most 10

    for i, cmd in enumerate(display_commands, 1):
        # Truncate very long commands
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        lines.append(f"  {i}. {cmd}")

    # Footer with filtering info if applicable
    if filtered_count > 0:
        lines.append(f"  ({filtered_count} sensitive command(s) filtered)")

    return "\n".join(lines)


# ============================================================================
# Enhanced Git Context Collection
# ============================================================================


def _get_dirty_files(directory: str) -> dict[str, list[str]]:
    """
    Get lists of staged, unstaged, and untracked files.

    Args:
        directory: Directory to check

    Returns:
        dict: Dictionary with 'staged', 'unstaged', 'untracked' lists
    """
    dirty_files = {
        "staged": [],
        "unstaged": [],
        "untracked": [],
    }

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return dirty_files

        # Split on newlines, preserving leading spaces (important for porcelain format)
        # Only strip the trailing newline, not leading whitespace
        for line in result.stdout.rstrip("\n").split("\n"):
            if not line or len(line) < 3:
                continue

            staged_status = line[0]
            unstaged_status = line[1]
            filename = line[3:].strip()

            # Handle renamed files (old -> new format)
            if " -> " in filename:
                filename = filename.split(" -> ")[-1]

            # Staged changes (not untracked)
            if staged_status != " " and staged_status != "?":
                dirty_files["staged"].append(filename)

            # Unstaged changes
            if unstaged_status != " " and unstaged_status != "?":
                dirty_files["unstaged"].append(filename)

            # Untracked files
            if staged_status == "?" and unstaged_status == "?":
                dirty_files["untracked"].append(filename)

    except (subprocess.TimeoutExpired, OSError):
        pass

    return dirty_files


def _get_ahead_behind_count(directory: str) -> tuple[int, int, Optional[str]]:
    """
    Get ahead/behind count relative to remote tracking branch.

    Args:
        directory: Git repository directory

    Returns:
        tuple: (ahead_count, behind_count, remote_branch)
    """
    ahead = 0
    behind = 0
    remote_branch = None

    try:
        # Get the upstream tracking branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            # No upstream tracking branch
            return ahead, behind, None

        remote_branch = result.stdout.strip()

        # Get ahead/behind counts
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"HEAD...{remote_branch}"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                ahead = int(parts[0])
                behind = int(parts[1])

    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass

    return ahead, behind, remote_branch


def _get_stash_count(directory: str) -> int:
    """
    Get the number of stashes.

    Args:
        directory: Git repository directory

    Returns:
        int: Number of stashes
    """
    try:
        result = subprocess.run(
            ["git", "stash", "list"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            return len(result.stdout.strip().split("\n"))

    except (subprocess.TimeoutExpired, OSError):
        pass

    return 0


def _get_recent_commits(directory: str, max_commits: int = 5) -> list[dict[str, str]]:
    """
    Get recent commit history.

    Args:
        directory: Git repository directory
        max_commits: Maximum number of commits to return

    Returns:
        list: List of dicts with 'hash' and 'message' keys
    """
    commits = []

    try:
        result = subprocess.run(
            ["git", "log", f"-{max_commits}", "--oneline", "--no-decorate"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split(" ", 1)
                if len(parts) >= 2:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                    })
                elif len(parts) == 1:
                    commits.append({
                        "hash": parts[0],
                        "message": "",
                    })

    except (subprocess.TimeoutExpired, OSError):
        pass

    return commits


def get_git_context_enhanced(
    directory: Optional[str] = None,
    max_commits: int = 5
) -> dict[str, Any]:
    """
    Collect enhanced git repository information.

    Extends the basic git context with additional details:
    - List of dirty files by status (staged, unstaged, untracked)
    - Ahead/behind counts relative to remote
    - Stash count
    - Recent commit history
    - Remote tracking branch info

    Args:
        directory: Directory to check (default: current working directory)
        max_commits: Maximum number of recent commits to include

    Returns:
        dict: Enhanced git context with keys:
            - is_git_repo: Whether directory is in a git repository
            - branch: Current branch name
            - commit_hash: Short commit hash
            - is_clean: Whether working directory is clean
            - has_staged: Whether there are staged changes
            - has_unstaged: Whether there are unstaged changes
            - has_untracked: Whether there are untracked files
            - dirty_files: Dict with 'staged', 'unstaged', 'untracked' file lists
            - ahead_count: Commits ahead of remote
            - behind_count: Commits behind remote
            - stash_count: Number of stashes
            - recent_commits: List of recent commits (hash, message)
            - remote_branch: Remote tracking branch name
            - error: Error message if collection failed

    Example:
        >>> context = get_git_context_enhanced()
        >>> print(context['dirty_files'])
        {'staged': ['file.py'], 'unstaged': [], 'untracked': ['new.txt']}
    """
    # Start with basic git context
    basic_context = get_git_context(directory)

    # Initialize enhanced fields
    context = {
        **basic_context,
        "dirty_files": {"staged": [], "unstaged": [], "untracked": []},
        "ahead_count": 0,
        "behind_count": 0,
        "stash_count": 0,
        "recent_commits": [],
        "remote_branch": None,
    }

    # If not a git repo or there's an error, return early
    if not context["is_git_repo"] or context.get("error"):
        return context

    # Determine directory
    if directory is None:
        directory = os.getcwd()

    # Get detailed dirty files
    context["dirty_files"] = _get_dirty_files(directory)

    # Get ahead/behind counts
    ahead, behind, remote = _get_ahead_behind_count(directory)
    context["ahead_count"] = ahead
    context["behind_count"] = behind
    context["remote_branch"] = remote

    # Get stash count
    context["stash_count"] = _get_stash_count(directory)

    # Get recent commits
    context["recent_commits"] = _get_recent_commits(directory, max_commits)

    return context


def format_git_context_enhanced(context: dict[str, Any]) -> str:
    """
    Format enhanced git context as human-readable string.

    Args:
        context: Context dictionary from get_git_context_enhanced()

    Returns:
        str: Formatted enhanced git context string

    Example:
        >>> context = get_git_context_enhanced()
        >>> print(format_git_context_enhanced(context))
        Git Repository: Yes
        Branch: main (abc1234)
        Status: clean
        Recent Commits:
          - abc1234: Add feature X
    """
    lines = []

    if context.get("error"):
        lines.append(f"Git Error: {context['error']}")
        return "\n".join(lines)

    if not context.get("is_git_repo"):
        lines.append("Git Repository: No")
        return "\n".join(lines)

    lines.append("Git Repository: Yes")

    # Branch and commit
    branch = context.get("branch", "unknown")
    if context.get("commit_hash"):
        branch = f"{branch} ({context['commit_hash']})"
    lines.append(f"Branch: {branch}")

    # Remote tracking
    if context.get("remote_branch"):
        ahead = context.get("ahead_count", 0)
        behind = context.get("behind_count", 0)
        if ahead or behind:
            tracking_info = f"↑{ahead} ↓{behind}"
            lines.append(f"Tracking: {context['remote_branch']} [{tracking_info}]")

    # Status
    if context.get("is_clean"):
        lines.append("Status: clean")
    else:
        status_parts = []
        dirty_files = context.get("dirty_files", {})

        staged = dirty_files.get("staged", [])
        if staged:
            status_parts.append(f"{len(staged)} staged")

        unstaged = dirty_files.get("unstaged", [])
        if unstaged:
            status_parts.append(f"{len(unstaged)} unstaged")

        untracked = dirty_files.get("untracked", [])
        if untracked:
            status_parts.append(f"{len(untracked)} untracked")

        if status_parts:
            lines.append(f"Status: {', '.join(status_parts)}")
        else:
            lines.append("Status: dirty")

    # Stash count
    stash_count = context.get("stash_count", 0)
    if stash_count > 0:
        lines.append(f"Stashes: {stash_count}")

    # Recent commits (show up to 3)
    recent_commits = context.get("recent_commits", [])
    if recent_commits:
        lines.append("Recent Commits:")
        for commit in recent_commits[:3]:
            hash_val = commit.get("hash", "?")
            msg = commit.get("message", "")
            # Truncate long messages
            if len(msg) > 50:
                msg = msg[:47] + "..."
            lines.append(f"  - {hash_val}: {msg}")

    return "\n".join(lines)
