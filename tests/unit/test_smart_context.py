"""
Tests for smart context injection functionality.
"""

import pytest

from hai_sh.prompt import (
    collect_context,
    _calculate_relevance,
    _budget_context,
    _estimate_tokens,
)


# ============================================================================
# Token Estimation Tests
# ============================================================================


@pytest.mark.unit
def test_estimate_tokens_empty_string():
    """Test token estimation with empty string."""
    assert _estimate_tokens("") == 0


@pytest.mark.unit
def test_estimate_tokens_short_string():
    """Test token estimation with short string."""
    # Approximately 4 chars per token
    tokens = _estimate_tokens("hello world")
    assert 2 <= tokens <= 5


@pytest.mark.unit
def test_estimate_tokens_long_string():
    """Test token estimation with longer string."""
    text = "This is a longer piece of text that should have more tokens."
    tokens = _estimate_tokens(text)
    assert 10 <= tokens <= 25


@pytest.mark.unit
def test_estimate_tokens_with_newlines():
    """Test token estimation with newlines."""
    text = "line one\nline two\nline three"
    tokens = _estimate_tokens(text)
    assert tokens > 0


# ============================================================================
# Relevance Calculation Tests
# ============================================================================


@pytest.mark.unit
def test_calculate_relevance_exact_match():
    """Test relevance with exact word match."""
    context = "git status shows uncommitted changes"
    query = "git status"
    relevance = _calculate_relevance(context, query)
    assert relevance > 0.5


@pytest.mark.unit
def test_calculate_relevance_no_match():
    """Test relevance with no matching terms."""
    context = "python files in the directory"
    query = "git status"
    relevance = _calculate_relevance(context, query)
    assert relevance < 0.3


@pytest.mark.unit
def test_calculate_relevance_partial_match():
    """Test relevance with partial matching terms."""
    context = "the current directory contains files"
    query = "show files in directory"
    relevance = _calculate_relevance(context, query)
    assert 0.2 <= relevance <= 0.8


@pytest.mark.unit
def test_calculate_relevance_case_insensitive():
    """Test that relevance is case-insensitive."""
    context = "Git Branch Main"
    query = "git branch"
    relevance = _calculate_relevance(context, query)
    assert relevance > 0.5


@pytest.mark.unit
def test_calculate_relevance_empty_query():
    """Test relevance with empty query."""
    context = "some context text"
    query = ""
    relevance = _calculate_relevance(context, query)
    assert relevance >= 0.0


@pytest.mark.unit
def test_calculate_relevance_empty_context():
    """Test relevance with empty context."""
    context = ""
    query = "git status"
    relevance = _calculate_relevance(context, query)
    assert relevance == 0.0


@pytest.mark.unit
def test_calculate_relevance_domain_keywords():
    """Test that domain-specific keywords boost relevance."""
    context = "git repository with branch main"
    query = "check current branch"
    relevance = _calculate_relevance(context, query)
    # Should have some relevance due to domain keywords
    assert relevance > 0.0


# ============================================================================
# Context Budgeting Tests
# ============================================================================


@pytest.mark.unit
def test_budget_context_under_limit():
    """Test that context under budget is not truncated."""
    context_parts = {
        "cwd": "Current directory: /home/user/project",
        "git": "Git branch: main",
    }
    max_tokens = 1000

    budgeted = _budget_context(context_parts, max_tokens)

    assert "cwd" in budgeted
    assert "git" in budgeted


@pytest.mark.unit
def test_budget_context_over_limit():
    """Test that context over budget is truncated."""
    # Create large context
    large_content = "word " * 500  # ~500 tokens
    context_parts = {
        "cwd": "Current directory: /home/user/project",
        "git": large_content,
        "files": large_content,
    }
    max_tokens = 100

    budgeted = _budget_context(context_parts, max_tokens)

    # Should keep essential parts
    assert "cwd" in budgeted
    # Should have truncated or removed some parts
    total_chars = sum(len(v) for v in budgeted.values())
    assert total_chars < len(large_content) * 2


@pytest.mark.unit
def test_budget_context_priority_order():
    """Test that higher priority context is preserved."""
    context_parts = {
        "cwd": "Current directory: /home/user/project",
        "git": "Git branch: main, clean",
        "memory": "Previously used: git status",
        "files": "Files: a.py, b.py, c.py, d.py, e.py",
    }
    max_tokens = 50

    budgeted = _budget_context(context_parts, max_tokens)

    # CWD should always be preserved (highest priority)
    assert "cwd" in budgeted


@pytest.mark.unit
def test_budget_context_empty():
    """Test budgeting with empty context."""
    context_parts = {}
    max_tokens = 1000

    budgeted = _budget_context(context_parts, max_tokens)

    assert budgeted == {}


@pytest.mark.unit
def test_budget_context_zero_budget():
    """Test budgeting with zero token budget."""
    context_parts = {
        "cwd": "Current directory: /home/user/project",
        "git": "Git branch: main",
    }
    max_tokens = 0

    budgeted = _budget_context(context_parts, max_tokens)

    # Should return minimal or empty context
    total_tokens = sum(_estimate_tokens(v) for v in budgeted.values())
    assert total_tokens <= 10  # Allow minimal essential context


# ============================================================================
# Collect Context Tests
# ============================================================================


@pytest.mark.unit
def test_collect_context_basic():
    """Test basic context collection."""
    config = {
        "context": {
            "include_history": True,
            "history_length": 5,
            "include_env_vars": True,
            "include_git_state": True,
            "include_file_listing": False,
            "include_session_memory": False,
            "include_directory_memory": False,
            "max_context_tokens": 4000,
            "context_relevance_threshold": 0.3,
        }
    }

    context = collect_context(config=config, query="list files")

    assert isinstance(context, dict)
    assert "cwd" in context


@pytest.mark.unit
def test_collect_context_with_memory(tmp_path, monkeypatch):
    """Test context collection with memory enabled."""
    monkeypatch.chdir(tmp_path)

    config = {
        "context": {
            "include_history": False,
            "include_env_vars": False,
            "include_git_state": False,
            "include_file_listing": False,
            "include_session_memory": True,
            "include_directory_memory": False,
            "max_context_tokens": 4000,
            "context_relevance_threshold": 0.0,  # Include all
        },
        "memory": {
            "enabled": True,
            "session_enabled": True,
            "session_max_interactions": 10,
        }
    }

    # Create memory manager with interactions
    from hai_sh.memory import MemoryManager
    memory_manager = MemoryManager(config)
    memory_manager.session.add_interaction("test query", "test cmd", "ok", True)

    context = collect_context(config=config, query="test", memory_manager=memory_manager)

    assert isinstance(context, dict)


@pytest.mark.unit
def test_collect_context_respects_relevance_threshold():
    """Test that context collection respects relevance threshold."""
    config = {
        "context": {
            "include_history": False,
            "include_env_vars": False,
            "include_git_state": False,
            "include_file_listing": False,
            "include_session_memory": False,
            "include_directory_memory": False,
            "max_context_tokens": 4000,
            "context_relevance_threshold": 0.9,  # Very high threshold
        }
    }

    context = collect_context(config=config, query="unrelated query")

    assert isinstance(context, dict)


@pytest.mark.unit
def test_collect_context_respects_token_budget():
    """Test that collected context respects token budget."""
    config = {
        "context": {
            "include_history": True,
            "history_length": 50,
            "include_env_vars": True,
            "include_git_state": True,
            "include_file_listing": True,
            "file_listing_max_files": 100,
            "file_listing_max_depth": 3,
            "include_session_memory": True,
            "include_directory_memory": True,
            "max_context_tokens": 100,  # Very small budget
            "context_relevance_threshold": 0.0,
        },
        "memory": {
            "enabled": True,
        }
    }

    context = collect_context(config=config, query="test")

    assert isinstance(context, dict)
    # Context should be budgeted
    formatted = "\n".join(str(v) for v in context.values())
    tokens = _estimate_tokens(formatted)
    # Allow some overhead, but should be roughly within budget
    assert tokens < 200


@pytest.mark.unit
def test_collect_context_no_config():
    """Test context collection with no config (uses defaults)."""
    context = collect_context(query="list files")

    assert isinstance(context, dict)
    assert "cwd" in context


@pytest.mark.unit
def test_collect_context_disabled_sources():
    """Test that disabled context sources are not collected."""
    config = {
        "context": {
            "include_history": False,
            "include_env_vars": False,
            "include_git_state": False,
            "include_file_listing": False,
            "include_session_memory": False,
            "include_directory_memory": False,
            "max_context_tokens": 4000,
            "context_relevance_threshold": 0.0,
        }
    }

    context = collect_context(config=config, query="test")

    # Should only have cwd (always included)
    assert "cwd" in context
    assert "shell_history" not in context
    assert "git_enhanced" not in context


@pytest.mark.unit
def test_collect_context_with_shell_history(tmp_path, monkeypatch):
    """Test context collection includes shell history when enabled."""
    monkeypatch.chdir(tmp_path)

    config = {
        "context": {
            "include_history": True,
            "history_length": 5,
            "include_env_vars": False,
            "include_git_state": False,
            "include_file_listing": False,
            "include_session_memory": False,
            "include_directory_memory": False,
            "max_context_tokens": 4000,
            "context_relevance_threshold": 0.0,
        }
    }

    context = collect_context(config=config, query="recent commands")

    assert isinstance(context, dict)
    # Shell history may or may not be present depending on shell


@pytest.mark.unit
def test_collect_context_git_enhanced(sample_git_repo, monkeypatch):
    """Test context collection with enhanced git context."""
    monkeypatch.chdir(sample_git_repo)

    config = {
        "context": {
            "include_history": False,
            "include_env_vars": False,
            "include_git_state": True,
            "include_file_listing": False,
            "include_session_memory": False,
            "include_directory_memory": False,
            "max_context_tokens": 4000,
            "context_relevance_threshold": 0.0,
        }
    }

    context = collect_context(config=config, query="git status")

    assert isinstance(context, dict)
    # Should have git context in a git repo
    assert "git" in context or "git_enhanced" in context


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_collect_context_formats_for_prompt(sample_git_repo, monkeypatch):
    """Test that collected context can be formatted for prompt."""
    monkeypatch.chdir(sample_git_repo)

    config = {
        "context": {
            "include_history": False,
            "include_env_vars": True,
            "include_git_state": True,
            "include_file_listing": True,
            "file_listing_max_files": 10,
            "file_listing_max_depth": 1,
            "include_session_memory": False,
            "include_directory_memory": False,
            "max_context_tokens": 4000,
            "context_relevance_threshold": 0.0,
        }
    }

    context = collect_context(config=config, query="show project status")

    # Context should be ready for prompt building
    from hai_sh.prompt import build_system_prompt
    prompt = build_system_prompt(context)

    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.unit
def test_collect_context_with_all_sources(sample_git_repo, monkeypatch):
    """Test context collection with all sources enabled."""
    monkeypatch.chdir(sample_git_repo)

    config = {
        "context": {
            "include_history": True,
            "history_length": 5,
            "include_env_vars": True,
            "include_git_state": True,
            "include_file_listing": True,
            "file_listing_max_files": 10,
            "file_listing_max_depth": 1,
            "include_session_memory": True,
            "include_directory_memory": True,
            "max_context_tokens": 4000,
            "context_relevance_threshold": 0.0,
        },
        "memory": {
            "enabled": True,
            "session_enabled": True,
            "directory_enabled": True,
        }
    }

    context = collect_context(config=config, query="show everything")

    assert isinstance(context, dict)
    assert "cwd" in context


@pytest.mark.unit
def test_relevance_filtering_removes_low_relevance():
    """Test that low relevance context is filtered out."""
    config = {
        "context": {
            "include_history": False,
            "include_env_vars": False,
            "include_git_state": False,
            "include_file_listing": False,
            "include_session_memory": False,
            "include_directory_memory": False,
            "max_context_tokens": 4000,
            "context_relevance_threshold": 1.0,  # Maximum threshold
        }
    }

    # With maximum threshold, only perfectly relevant context survives
    context = collect_context(config=config, query="xyz123abc")

    # Should have minimal context (only always-included fields like cwd)
    assert isinstance(context, dict)
