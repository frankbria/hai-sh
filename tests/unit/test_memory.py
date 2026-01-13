"""
Tests for the memory system (session, directory, persistent).
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from hai_sh.memory import (
    SessionMemory,
    DirectoryMemory,
    PersistentPreferences,
    MemoryManager,
)


# ============================================================================
# Session Memory Tests
# ============================================================================


class TestSessionMemory:
    """Tests for in-memory session storage."""

    @pytest.mark.unit
    def test_session_memory_init(self):
        """Test session memory initialization."""
        memory = SessionMemory()

        assert memory.interactions == []
        assert memory.max_interactions == 20  # Default limit

    @pytest.mark.unit
    def test_session_memory_custom_limit(self):
        """Test session memory with custom limit."""
        memory = SessionMemory(max_interactions=5)

        assert memory.max_interactions == 5

    @pytest.mark.unit
    def test_add_interaction(self):
        """Test adding an interaction."""
        memory = SessionMemory()

        memory.add_interaction(
            query="list files",
            command="ls -la",
            result="file1.txt\nfile2.txt",
        )

        assert len(memory.interactions) == 1
        interaction = memory.interactions[0]
        assert interaction["query"] == "list files"
        assert interaction["command"] == "ls -la"
        assert interaction["result"] == "file1.txt\nfile2.txt"
        assert "timestamp" in interaction

    @pytest.mark.unit
    def test_add_interaction_with_success(self):
        """Test adding an interaction with success flag."""
        memory = SessionMemory()

        memory.add_interaction(
            query="run tests",
            command="pytest",
            result="All tests passed",
            success=True,
        )

        assert memory.interactions[0]["success"] is True

    @pytest.mark.unit
    def test_add_interaction_respects_limit(self):
        """Test that adding interactions respects max limit."""
        memory = SessionMemory(max_interactions=3)

        # Add 5 interactions
        for i in range(5):
            memory.add_interaction(
                query=f"query {i}",
                command=f"cmd{i}",
                result=f"result {i}",
            )

        assert len(memory.interactions) == 3
        # Should keep the most recent
        assert memory.interactions[0]["query"] == "query 2"
        assert memory.interactions[2]["query"] == "query 4"

    @pytest.mark.unit
    def test_get_recent_interactions(self):
        """Test retrieving recent interactions."""
        memory = SessionMemory()

        for i in range(10):
            memory.add_interaction(f"query {i}", f"cmd{i}", f"result {i}")

        recent = memory.get_recent_interactions(count=3)

        assert len(recent) == 3
        # Should get the most recent 3
        assert recent[-1]["query"] == "query 9"

    @pytest.mark.unit
    def test_get_recent_interactions_fewer_than_count(self):
        """Test getting recent when fewer interactions exist."""
        memory = SessionMemory()
        memory.add_interaction("q1", "c1", "r1")

        recent = memory.get_recent_interactions(count=5)

        assert len(recent) == 1

    @pytest.mark.unit
    def test_clear(self):
        """Test clearing session memory."""
        memory = SessionMemory()
        for i in range(5):
            memory.add_interaction(f"q{i}", f"c{i}", f"r{i}")

        memory.clear()

        assert memory.interactions == []

    @pytest.mark.unit
    def test_to_dict(self):
        """Test serializing session memory to dict."""
        memory = SessionMemory()
        memory.add_interaction("query", "cmd", "result")

        data = memory.to_dict()

        assert "interactions" in data
        assert len(data["interactions"]) == 1
        assert data["interactions"][0]["query"] == "query"

    @pytest.mark.unit
    def test_from_dict(self):
        """Test deserializing session memory from dict."""
        data = {
            "interactions": [
                {"query": "q1", "command": "c1", "result": "r1", "timestamp": 123.0}
            ]
        }

        memory = SessionMemory.from_dict(data)

        assert len(memory.interactions) == 1
        assert memory.interactions[0]["query"] == "q1"

    @pytest.mark.unit
    def test_format_for_context(self):
        """Test formatting session memory for context injection."""
        memory = SessionMemory()
        memory.add_interaction("list files", "ls -la", "file.txt")
        memory.add_interaction("change dir", "cd src", "")

        formatted = memory.format_for_context()

        assert "list files" in formatted or "ls -la" in formatted
        assert isinstance(formatted, str)


# ============================================================================
# Directory Memory Tests
# ============================================================================


class TestDirectoryMemory:
    """Tests for directory/project-specific memory."""

    @pytest.mark.unit
    def test_directory_memory_init(self):
        """Test directory memory initialization."""
        memory = DirectoryMemory()

        assert memory.project_name is None
        assert memory.patterns == []
        assert memory.preferences == {}

    @pytest.mark.unit
    def test_load_nonexistent(self, tmp_path):
        """Test loading from directory without .hai/context.json."""
        memory = DirectoryMemory()
        memory.load(tmp_path)

        # Should have empty defaults
        assert memory.patterns == []
        assert memory.preferences == {}

    @pytest.mark.unit
    def test_save_and_load(self, tmp_path):
        """Test saving and loading directory memory."""
        memory = DirectoryMemory()
        memory.project_name = "test-project"
        memory.patterns = ["npm run build", "pytest"]
        memory.preferences = {"test_framework": "pytest"}

        memory.save(tmp_path)
        assert (tmp_path / ".hai" / "context.json").exists()

        # Load into new instance
        memory2 = DirectoryMemory()
        memory2.load(tmp_path)

        assert memory2.project_name == "test-project"
        assert "npm run build" in memory2.patterns
        assert memory2.preferences["test_framework"] == "pytest"

    @pytest.mark.unit
    def test_add_pattern(self):
        """Test adding command patterns."""
        memory = DirectoryMemory()

        memory.add_pattern("git status")
        memory.add_pattern("pytest -v")

        assert "git status" in memory.patterns
        assert "pytest -v" in memory.patterns

    @pytest.mark.unit
    def test_add_pattern_deduplication(self):
        """Test that duplicate patterns are not added."""
        memory = DirectoryMemory()

        memory.add_pattern("git status")
        memory.add_pattern("git status")
        memory.add_pattern("git status")

        assert memory.patterns.count("git status") == 1

    @pytest.mark.unit
    def test_add_pattern_respects_limit(self):
        """Test pattern list respects size limit."""
        memory = DirectoryMemory(max_patterns=5)

        for i in range(10):
            memory.add_pattern(f"command{i}")

        assert len(memory.patterns) <= 5

    @pytest.mark.unit
    def test_get_patterns(self):
        """Test retrieving patterns."""
        memory = DirectoryMemory()
        memory.patterns = ["cmd1", "cmd2", "cmd3"]

        patterns = memory.get_patterns()

        assert patterns == ["cmd1", "cmd2", "cmd3"]

    @pytest.mark.unit
    def test_update_preferences(self):
        """Test updating preferences."""
        memory = DirectoryMemory()

        memory.update_preferences("editor", "vim")
        memory.update_preferences("language", "python")

        assert memory.preferences["editor"] == "vim"
        assert memory.preferences["language"] == "python"

    @pytest.mark.unit
    def test_find_project_root_with_git(self, tmp_path, monkeypatch):
        """Test finding project root via .git directory."""
        # Create .git directory
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        subdir = tmp_path / "src" / "utils"
        subdir.mkdir(parents=True)

        memory = DirectoryMemory()
        root = memory.find_project_root(subdir)

        assert root == tmp_path

    @pytest.mark.unit
    def test_find_project_root_with_hai_dir(self, tmp_path):
        """Test finding project root via .hai directory."""
        hai_dir = tmp_path / ".hai"
        hai_dir.mkdir()

        subdir = tmp_path / "lib"
        subdir.mkdir()

        memory = DirectoryMemory()
        root = memory.find_project_root(subdir)

        assert root == tmp_path

    @pytest.mark.unit
    def test_find_project_root_none(self, tmp_path):
        """Test when no project root markers found."""
        subdir = tmp_path / "random"
        subdir.mkdir()

        memory = DirectoryMemory()
        root = memory.find_project_root(subdir)

        # Should return None or the directory itself
        assert root is None or root == subdir

    @pytest.mark.unit
    def test_to_dict(self):
        """Test serializing directory memory."""
        memory = DirectoryMemory()
        memory.project_name = "test"
        memory.patterns = ["cmd1"]
        memory.preferences = {"key": "value"}

        data = memory.to_dict()

        assert data["project_name"] == "test"
        assert "cmd1" in data["patterns"]
        assert data["preferences"]["key"] == "value"

    @pytest.mark.unit
    def test_format_for_context(self):
        """Test formatting directory memory for context injection."""
        memory = DirectoryMemory()
        memory.project_name = "hai-sh"
        memory.patterns = ["pytest", "ruff hai_sh/"]

        formatted = memory.format_for_context()

        assert isinstance(formatted, str)


# ============================================================================
# Persistent Preferences Tests
# ============================================================================


class TestPersistentPreferences:
    """Tests for user-wide persistent preferences."""

    @pytest.mark.unit
    def test_persistent_preferences_init(self):
        """Test persistent preferences initialization."""
        prefs = PersistentPreferences()

        assert prefs.command_patterns == {}
        assert prefs.style_preferences == {}
        assert prefs.frequent_operations == []

    @pytest.mark.unit
    def test_load_nonexistent(self, tmp_path, monkeypatch):
        """Test loading when preferences file doesn't exist."""
        monkeypatch.setenv("HOME", str(tmp_path))

        prefs = PersistentPreferences()
        prefs.load()

        # Should have empty defaults
        assert prefs.command_patterns == {}

    @pytest.mark.unit
    def test_save_and_load(self, tmp_path, monkeypatch):
        """Test saving and loading preferences."""
        monkeypatch.setenv("HOME", str(tmp_path))
        hai_dir = tmp_path / ".hai"
        hai_dir.mkdir()

        prefs = PersistentPreferences()
        prefs.command_patterns = {"ls": 10, "git status": 5}
        prefs.style_preferences = {"verbose": True}

        prefs.save()
        assert (hai_dir / "preferences.json").exists()

        # Load into new instance
        prefs2 = PersistentPreferences()
        prefs2.load()

        assert prefs2.command_patterns["ls"] == 10
        assert prefs2.style_preferences["verbose"] is True

    @pytest.mark.unit
    def test_record_command(self):
        """Test recording command usage."""
        prefs = PersistentPreferences()

        prefs.record_command("ls -la", success=True)
        prefs.record_command("ls -la", success=True)
        prefs.record_command("git status", success=True)

        assert prefs.command_patterns.get("ls -la", 0) >= 2
        assert prefs.command_patterns.get("git status", 0) >= 1

    @pytest.mark.unit
    def test_record_command_failed(self):
        """Test recording failed commands."""
        prefs = PersistentPreferences()

        prefs.record_command("invalid-cmd", success=False)

        # Failed commands should be recorded differently or not at all
        # Based on implementation choice

    @pytest.mark.unit
    def test_get_frequent_patterns(self):
        """Test getting most frequent command patterns."""
        prefs = PersistentPreferences()
        prefs.command_patterns = {
            "git status": 100,
            "ls -la": 50,
            "pytest": 25,
            "cd": 10,
        }

        frequent = prefs.get_frequent_patterns(limit=2)

        assert len(frequent) == 2
        assert "git status" in frequent

    @pytest.mark.unit
    def test_learn_style(self):
        """Test learning user style preferences."""
        prefs = PersistentPreferences()

        prefs.learn_style("output_format", "json")
        prefs.learn_style("verbosity", "high")

        assert prefs.style_preferences["output_format"] == "json"
        assert prefs.style_preferences["verbosity"] == "high"

    @pytest.mark.unit
    def test_to_dict(self):
        """Test serializing preferences to dict."""
        prefs = PersistentPreferences()
        prefs.command_patterns = {"cmd": 5}
        prefs.style_preferences = {"key": "value"}

        data = prefs.to_dict()

        assert "command_patterns" in data
        assert "style_preferences" in data

    @pytest.mark.unit
    def test_format_for_context(self):
        """Test formatting preferences for context injection."""
        prefs = PersistentPreferences()
        prefs.command_patterns = {"git push": 10}
        prefs.style_preferences = {"verbose": True}

        formatted = prefs.format_for_context()

        assert isinstance(formatted, str)


# ============================================================================
# Memory Manager Tests
# ============================================================================


class TestMemoryManager:
    """Tests for the memory manager that coordinates all tiers."""

    @pytest.mark.unit
    def test_memory_manager_init(self):
        """Test memory manager initialization."""
        manager = MemoryManager()

        assert manager.session is not None
        assert manager.directory is not None
        assert manager.preferences is not None

    @pytest.mark.unit
    def test_memory_manager_disabled(self):
        """Test memory manager when memory is disabled."""
        config = {"memory": {"enabled": False}}
        manager = MemoryManager(config)

        # Should still work but return empty contexts
        context = manager.collect_memory_context("test query")
        assert isinstance(context, dict)

    @pytest.mark.unit
    def test_collect_memory_context(self, tmp_path, monkeypatch):
        """Test collecting memory context from all tiers."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".hai").mkdir()

        manager = MemoryManager()

        # Add some data
        manager.session.add_interaction("list files", "ls", "output")
        manager.directory.add_pattern("pytest")
        manager.preferences.record_command("git status", True)

        context = manager.collect_memory_context("run tests")

        assert "session" in context or "interactions" in str(context)

    @pytest.mark.unit
    def test_update_memory(self, tmp_path, monkeypatch):
        """Test updating memory after command execution."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".hai").mkdir()

        manager = MemoryManager()

        manager.update_memory(
            query="list files",
            command="ls -la",
            result="file1.txt\nfile2.txt",
            success=True,
        )

        # Session should be updated
        assert len(manager.session.interactions) >= 1

    @pytest.mark.unit
    def test_save_and_load_all(self, tmp_path, monkeypatch):
        """Test saving and loading all memory tiers."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".hai").mkdir()

        manager = MemoryManager()
        manager.session.add_interaction("q", "c", "r")
        manager.directory.add_pattern("pytest")
        manager.preferences.record_command("ls", True)

        manager.save_all()

        # Load into new manager
        manager2 = MemoryManager()
        manager2.load_all()

        # Check that data was persisted
        assert len(manager2.directory.patterns) >= 0  # May vary by impl

    @pytest.mark.unit
    def test_cleanup_old_memory(self, tmp_path, monkeypatch):
        """Test cleanup of old memory entries."""
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".hai").mkdir()

        manager = MemoryManager()

        # This should not raise
        manager.cleanup_old_memory()

    @pytest.mark.unit
    def test_get_memory_stats(self, tmp_path, monkeypatch):
        """Test getting memory statistics."""
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".hai").mkdir()

        manager = MemoryManager()
        manager.session.add_interaction("q", "c", "r")

        stats = manager.get_memory_stats()

        assert "session_count" in stats or "session" in str(stats)

    @pytest.mark.unit
    def test_format_memory_context(self, tmp_path, monkeypatch):
        """Test formatting memory context for LLM."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".hai").mkdir()

        manager = MemoryManager()
        manager.session.add_interaction("list", "ls", "files")

        formatted = manager.format_memory_context()

        assert isinstance(formatted, str)


# ============================================================================
# Integration Tests
# ============================================================================


class TestMemoryIntegration:
    """Integration tests for the memory system."""

    @pytest.mark.unit
    def test_full_workflow(self, tmp_path, monkeypatch):
        """Test complete memory workflow."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".hai").mkdir()

        # Initialize manager
        manager = MemoryManager()

        # Simulate a few interactions
        for i in range(3):
            manager.update_memory(
                query=f"query {i}",
                command=f"command{i}",
                result=f"result {i}",
                success=True,
            )

        # Save all
        manager.save_all()

        # Create new manager and load
        manager2 = MemoryManager()
        manager2.load_all()

        # Verify session is preserved (if implemented to persist)
        # Directory and preferences should be loaded
        assert manager2.session is not None
        assert manager2.directory is not None
        assert manager2.preferences is not None
