# Implementation Plan: Add File Listing Context to hai-sh

## Issue
#41 - feat(context): Add file listing context collection

## Overview
Add file listing context collection to hai-sh, enabling Claude Code to see available files in the current directory. This improves context awareness for shell commands.

## Implementation Steps

### 1. Add File Listing Configuration
**File**: `hai_sh/config.py`

Update `DEFAULT_CONFIG` dictionary to add file listing settings in `context` section:

```python
"context": {
    "include_history": True,
    "history_length": 10,
    "include_env_vars": True,
    "include_git_state": True,
    "include_file_listing": True,      # NEW
    "file_listing_max_files": 20,      # NEW
    "file_listing_max_depth": 1,       # NEW (0 = current dir only, 1 = one level deep)
    "file_listing_show_hidden": False, # NEW
}
```

### 2. Implement Core File Listing Functions
**File**: `hai_sh/context.py`

Add the following function:

```python
def get_file_listing_context(
    directory: Optional[str] = None,
    max_files: int = 20,
    max_depth: int = 1,
    show_hidden: bool = False,
    query: Optional[str] = None
) -> dict[str, Any]:
    """
    Collect file listing with efficient directory traversal.

    Returns:
        - directory: Absolute path to directory
        - files: List of file dicts with keys: name, type (file/dir), size, modified
        - total_count: Total number of items found
        - truncated: Boolean indicating if list was truncated
        - depth: Depth level scanned
        - error: Error message if collection failed
    """
    # Implementation using os.scandir() for efficiency
    # Sort: directories first, then by name (case-insensitive)
    # Filter hidden files based on show_hidden
    # Limit results to max_files
    # Handle permission errors gracefully
    # Track performance
    # If query provided, implement relevance filtering
```

**Add formatting function:**

```python
def format_file_listing_context(context: dict[str, Any]) -> str:
    """
    Format file listing as human-readable output.

    Example:
    ```
    Files in directory (showing 20 of 150):
      dir1/
      dir2/
      file1.txt (1.2 KB)
      file2.py (3.4 KB)
      ...
    (truncated, showing 20 of 150 files)
    ```
    """
```

**Add helper functions:**

```python
def _format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format (B, KB, MB, GB)."""

def _filter_files_by_relevance(
    files: list[dict[str, Any]],
    query: str,
    max_files: int
) -> list[dict[str, Any]]:
    """Score files based on query relevance (case-insensitive substring matching)."""
```

### 3. Update Module Exports
**File**: `hai_sh/__init__.py`

Add new functions to imports and `__all__`:

```python
from hai_sh.context import (
    # ... existing imports ...
    get_file_listing_context,
    format_file_listing_context,
)

__all__ = [
    # ... existing exports ...
    "get_file_listing_context",
    "format_file_listing_context",
]
```

### 4. Integrate File Listing into Main Flow
**File**: `hai_sh/__main__.py`

Update context gathering section to include file listing:

```python
# Gather context
context = {
    'cwd': get_cwd_context(),
    'git': get_git_context(),
    'env': get_env_context()
}

# Add file listing if enabled
if config.get('context', {}).get('include_file_listing', True):
    file_listing_config = config.get('context', {})
    context['files'] = get_file_listing_context(
        max_files=file_listing_config.get('file_listing_max_files', 20),
        max_depth=file_listing_config.get('file_listing_max_depth', 1),
        show_hidden=file_listing_config.get('file_listing_show_hidden', False),
        query=user_query  # Pass user query for relevance filtering
    )
```

### 5. Update Prompt Formatting
**File**: `hai_sh/prompt.py`

Update `_format_context()` function to include file listings:

```python
def _format_context(context: dict[str, Any]) -> str:
    parts = []

    # ... existing context formatting ...

    # File listing context (NEW)
    if "files" in context:
        from hai_sh.context import format_file_listing_context
        file_listing = format_file_listing_context(context["files"])
        if file_listing:
            parts.append(file_listing)

    return "\\n".join(parts) if parts else "No specific context provided."
```

### 6. Implement Comprehensive Unit Tests
**File**: `tests/unit/test_context.py`

Add test cases covering:
- Basic functionality (basic listing, empty directory, default directory)
- File filtering (max_files, hidden files, truncation flag)
- Relevance filtering (with query, case-insensitive, exact match prioritization)
- Sorting (directories first, alphabetical)
- Error handling (nonexistent directory, permission errors, OS errors)
- Performance (typical directory, large directory)
- Formatting (normal, with truncation, with error, empty)
- Integration (end-to-end, main flow integration)

Target: **90%+ coverage** of new code

## Configuration Options

| Option | Type | Default | Description |
|---------|------|---------|-------------|
| `include_file_listing` | bool | `True` | Enable/disable file listing context |
| `file_listing_max_files` | int | `20` | Maximum files to include in listing |
| `file_listing_max_depth` | int | `1` | Directory depth to scan (0=current only) |
| `file_listing_show_hidden` | bool | `False` | Include hidden files (starting with `.`) |

## Performance Notes
- Use `os.scandir()` instead of `os.listdir()` + `os.stat()` (avoids extra syscalls)
- Cache stat information from DirEntry objects
- Implement early termination when `max_files` is reached
- Use generator expressions for memory efficiency with large directories

## Success Criteria
- ✅ File listing configuration added
- ✅ Core functions implemented with proper error handling
- ✅ Module exports updated
- ✅ Integrated into main context flow
- ✅ Prompt formatting updated
- ✅ Comprehensive unit tests with 90%+ coverage
- ✅ Performance benchmarks meet expectations
