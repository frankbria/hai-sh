"""
Memory system for hai-sh.

This module provides a three-tier memory system for maintaining context:
- SessionMemory: In-memory storage for current terminal session
- DirectoryMemory: Project-specific context stored in .hai/context.json
- PersistentPreferences: User-wide patterns stored in ~/.hai/preferences.json
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Optional


class SessionMemory:
    """
    In-memory session storage for tracking conversation within a terminal session.

    Stores recent interactions (query, command, result) to provide context
    about what the user has been doing in the current session.

    Attributes:
        interactions: List of interaction dictionaries
        max_interactions: Maximum number of interactions to store
    """

    def __init__(self, max_interactions: int = 20):
        """
        Initialize session memory.

        Args:
            max_interactions: Maximum interactions to store (default: 20)
        """
        self.interactions: list[dict[str, Any]] = []
        self.max_interactions = max_interactions

    def add_interaction(
        self,
        query: str,
        command: str,
        result: str,
        success: bool = True,
    ) -> None:
        """
        Add an interaction to session history.

        Args:
            query: User's natural language query
            command: Generated bash command
            result: Command execution result
            success: Whether the command succeeded
        """
        interaction = {
            "query": query,
            "command": command,
            "result": result,
            "success": success,
            "timestamp": time.time(),
        }

        self.interactions.append(interaction)

        # Enforce size limit
        if len(self.interactions) > self.max_interactions:
            self.interactions = self.interactions[-self.max_interactions:]

    def get_recent_interactions(self, count: int = 5) -> list[dict[str, Any]]:
        """
        Retrieve recent interactions.

        Args:
            count: Number of recent interactions to retrieve

        Returns:
            list: List of recent interaction dictionaries
        """
        if count <= 0:
            return []
        return self.interactions[-count:]

    def clear(self) -> None:
        """Clear all session memory."""
        self.interactions = []

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize session memory to dictionary.

        Returns:
            dict: Serialized session data
        """
        return {
            "interactions": self.interactions,
            "max_interactions": self.max_interactions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], max_interactions: int = 20) -> "SessionMemory":
        """
        Deserialize session memory from dictionary.

        Args:
            data: Dictionary containing session data
            max_interactions: Maximum interactions to store (default: 20)

        Returns:
            SessionMemory: New instance with loaded data
        """
        stored_max = data.get("max_interactions", max_interactions)
        memory = cls(max_interactions=stored_max)
        interactions = data.get("interactions", [])
        # Cap loaded history to the limit
        if len(interactions) > memory.max_interactions:
            interactions = interactions[-memory.max_interactions:]
        memory.interactions = interactions
        return memory

    def format_for_context(self) -> str:
        """
        Format session memory for LLM context injection.

        Returns:
            str: Human-readable session context
        """
        if not self.interactions:
            return ""

        lines = ["Recent session activity:"]

        # Show last few interactions
        for interaction in self.interactions[-5:]:
            query = interaction.get("query", "")
            command = interaction.get("command", "")
            # Truncate long commands
            if len(command) > 50:
                command = command[:47] + "..."
            lines.append(f"  - \"{query}\" → {command}")

        return "\n".join(lines)


class DirectoryMemory:
    """
    Project-specific memory stored in .hai/context.json.

    Stores patterns and preferences specific to a project directory,
    allowing hai to learn project-specific workflows.

    Attributes:
        project_name: Name of the project
        patterns: List of common command patterns for this project
        preferences: Project-specific settings
    """

    def __init__(self, max_patterns: int = 100):
        """
        Initialize directory memory.

        Args:
            max_patterns: Maximum command patterns to store
        """
        self.project_name: Optional[str] = None
        self.patterns: list[str] = []
        self.preferences: dict[str, Any] = {}
        self.last_updated: Optional[float] = None
        self.max_patterns = max_patterns

    def load(self, directory: Path) -> None:
        """
        Load directory memory from .hai/context.json.

        Args:
            directory: Directory to load from
        """
        context_file = directory / ".hai" / "context.json"

        if not context_file.exists():
            return

        try:
            with open(context_file, "r") as f:
                data = json.load(f)

            # Guard against non-dict JSON roots
            if not isinstance(data, dict):
                return

            self.project_name = data.get("project_name")
            # Validate/normalize field types
            patterns = data.get("patterns", [])
            self.patterns = patterns if isinstance(patterns, list) else []
            prefs = data.get("preferences", {})
            self.preferences = prefs if isinstance(prefs, dict) else {}
            self.last_updated = data.get("last_updated")

        except (json.JSONDecodeError, OSError):
            # Invalid or unreadable file, use defaults
            pass

    def save(self, directory: Path) -> None:
        """
        Save directory memory to .hai/context.json.

        Args:
            directory: Directory to save to
        """
        hai_dir = directory / ".hai"
        try:
            hai_dir.mkdir(exist_ok=True)
        except OSError:
            # Can't create directory (permissions or .hai is a file), skip saving
            return

        context_file = hai_dir / "context.json"

        self.last_updated = time.time()

        data = {
            "project_name": self.project_name,
            "patterns": self.patterns,
            "preferences": self.preferences,
            "last_updated": self.last_updated,
        }

        try:
            with open(context_file, "w") as f:
                json.dump(data, f, indent=2)
        except OSError:
            # Can't write, ignore
            pass

    def add_pattern(self, command: str) -> None:
        """
        Add a command pattern to the project memory.

        Args:
            command: Command pattern to add
        """
        # Avoid duplicates
        if command not in self.patterns:
            self.patterns.append(command)

        # Enforce size limit (remove oldest)
        # Handle max_patterns=0 edge case: -0 slice returns full list
        if len(self.patterns) > self.max_patterns:
            self.patterns = self.patterns[-self.max_patterns:] if self.max_patterns > 0 else []

    def get_patterns(self) -> list[str]:
        """
        Get all stored command patterns.

        Returns:
            list: List of command patterns
        """
        return list(self.patterns)

    def update_preferences(self, key: str, value: Any) -> None:
        """
        Update a project preference.

        Args:
            key: Preference key
            value: Preference value
        """
        self.preferences[key] = value

    def find_project_root(self, start_dir: Path) -> Optional[Path]:
        """
        Find the project root by looking for .git or .hai directory.

        Args:
            start_dir: Directory to start searching from

        Returns:
            Path: Project root directory, or None if not found
        """
        current = start_dir.resolve()

        # Limit search depth
        for _ in range(20):
            if (current / ".git").exists() or (current / ".hai").exists():
                return current

            parent = current.parent
            if parent == current:
                # Reached filesystem root
                break
            current = parent

        return None

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize directory memory to dictionary.

        Returns:
            dict: Serialized directory data
        """
        return {
            "project_name": self.project_name,
            "patterns": self.patterns,
            "preferences": self.preferences,
            "last_updated": self.last_updated,
        }

    def format_for_context(self) -> str:
        """
        Format directory memory for LLM context injection.

        Returns:
            str: Human-readable directory context
        """
        if not self.project_name and not self.patterns:
            return ""

        lines = []

        if self.project_name:
            lines.append(f"Project: {self.project_name}")

        if self.patterns:
            lines.append("Common commands:")
            for pattern in self.patterns[-5:]:  # Show last 5
                if len(pattern) > 50:
                    pattern = pattern[:47] + "..."
                lines.append(f"  - {pattern}")

        return "\n".join(lines)


class PersistentPreferences:
    """
    User-wide persistent preferences stored in ~/.hai/preferences.json.

    Tracks command usage patterns and user preferences across all projects.

    Attributes:
        command_patterns: Dictionary of commands to usage counts
        style_preferences: User style settings
        frequent_operations: List of most frequent operations
    """

    def __init__(self, max_patterns: int = 500):
        """
        Initialize persistent preferences.

        Args:
            max_patterns: Maximum unique commands to track
        """
        self.command_patterns: dict[str, int] = {}
        self.style_preferences: dict[str, Any] = {}
        self.frequent_operations: list[str] = []
        self.max_patterns = max_patterns

    def _get_preferences_path(self) -> Path:
        """Get path to preferences file."""
        return Path.home() / ".hai" / "preferences.json"

    def load(self) -> None:
        """Load preferences from ~/.hai/preferences.json."""
        prefs_file = self._get_preferences_path()

        if not prefs_file.exists():
            return

        try:
            with open(prefs_file, "r") as f:
                data = json.load(f)

            self.command_patterns = data.get("command_patterns", {})
            self.style_preferences = data.get("style_preferences", {})
            self.frequent_operations = data.get("frequent_operations", [])

        except (json.JSONDecodeError, OSError):
            # Invalid or unreadable, use defaults
            pass

    def save(self) -> None:
        """Save preferences to ~/.hai/preferences.json."""
        prefs_file = self._get_preferences_path()

        # Ensure .hai directory exists
        prefs_file.parent.mkdir(exist_ok=True)

        data = {
            "command_patterns": self.command_patterns,
            "style_preferences": self.style_preferences,
            "frequent_operations": self.frequent_operations,
        }

        try:
            with open(prefs_file, "w") as f:
                json.dump(data, f, indent=2)
        except OSError:
            # Can't write, ignore
            pass

    def record_command(self, command: str, success: bool = True) -> None:
        """
        Record a command execution.

        Args:
            command: Command that was executed
            success: Whether the command succeeded
        """
        if not success:
            # Optionally track failed commands differently
            return

        # Update count
        self.command_patterns[command] = self.command_patterns.get(command, 0) + 1

        # Enforce size limit (remove least used)
        if len(self.command_patterns) > self.max_patterns:
            # Sort by count and keep top max_patterns
            sorted_patterns = sorted(
                self.command_patterns.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            self.command_patterns = dict(sorted_patterns[:self.max_patterns])

        # Update frequent operations list
        self._update_frequent_operations()

    def _update_frequent_operations(self) -> None:
        """Update the frequent operations list."""
        sorted_patterns = sorted(
            self.command_patterns.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        self.frequent_operations = [cmd for cmd, _ in sorted_patterns[:10]]

    def get_frequent_patterns(self, limit: int = 5) -> list[str]:
        """
        Get the most frequently used command patterns.

        Args:
            limit: Maximum patterns to return

        Returns:
            list: Most frequent commands
        """
        sorted_patterns = sorted(
            self.command_patterns.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [cmd for cmd, _ in sorted_patterns[:limit]]

    def learn_style(self, key: str, value: Any) -> None:
        """
        Learn a user style preference.

        Args:
            key: Style preference key
            value: Style preference value
        """
        self.style_preferences[key] = value

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize preferences to dictionary.

        Returns:
            dict: Serialized preferences data
        """
        return {
            "command_patterns": self.command_patterns,
            "style_preferences": self.style_preferences,
            "frequent_operations": self.frequent_operations,
        }

    def format_for_context(self) -> str:
        """
        Format preferences for LLM context injection.

        Returns:
            str: Human-readable preferences context
        """
        if not self.command_patterns and not self.style_preferences:
            return ""

        lines = []

        if self.command_patterns:
            frequent = self.get_frequent_patterns(limit=3)
            if frequent:
                lines.append("Frequently used commands:")
                for cmd in frequent:
                    if len(cmd) > 50:
                        cmd = cmd[:47] + "..."
                    lines.append(f"  - {cmd}")

        return "\n".join(lines)


class MemoryManager:
    """
    Coordinates all memory tiers (session, directory, persistent).

    Provides a unified interface for collecting context, updating memory,
    and managing memory lifecycle.

    Attributes:
        session: SessionMemory instance
        directory: DirectoryMemory instance
        preferences: PersistentPreferences instance
        enabled: Whether memory system is enabled
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize memory manager.

        Args:
            config: Optional configuration dictionary
        """
        config = config or {}
        memory_config = config.get("memory", {})

        self.enabled = memory_config.get("enabled", True)

        # Initialize memory tiers
        session_size = memory_config.get("session_size", 20)
        self.session = SessionMemory(max_interactions=session_size)

        dir_pattern_limit = memory_config.get("directory_pattern_limit", 100)
        self.directory = DirectoryMemory(max_patterns=dir_pattern_limit)

        pref_pattern_limit = memory_config.get("preferences_pattern_limit", 500)
        self.preferences = PersistentPreferences(max_patterns=pref_pattern_limit)

        # Working directory for directory memory
        self._working_dir: Optional[Path] = None

    def load_all(self) -> None:
        """Load all memory tiers from disk."""
        if not self.enabled:
            return

        # Load preferences
        self.preferences.load()

        # Load directory memory from current directory
        try:
            cwd = Path.cwd()
            project_root = self.directory.find_project_root(cwd)
            if project_root:
                self._working_dir = project_root
                self.directory.load(project_root)
            else:
                self._working_dir = cwd
        except OSError:
            pass

    def save_all(self) -> None:
        """Save all memory tiers to disk."""
        if not self.enabled:
            return

        # Save preferences
        self.preferences.save()

        # Save directory memory
        if self._working_dir:
            self.directory.save(self._working_dir)

    def collect_memory_context(self) -> dict[str, Any]:
        """
        Collect relevant memory context.

        Returns:
            dict: Memory context from all tiers
        """
        if not self.enabled:
            return {}

        context = {}

        # Session context
        if self.session.interactions:
            context["session"] = self.session.to_dict()

        # Directory context
        if self.directory.patterns or self.directory.preferences:
            context["directory"] = self.directory.to_dict()

        # Preferences context
        if self.preferences.command_patterns:
            context["preferences"] = self.preferences.to_dict()

        return context

    def update_memory(
        self,
        query: str,
        command: str,
        result: str,
        success: bool = True,
    ) -> None:
        """
        Update all memory tiers after command execution.

        Args:
            query: User's natural language query
            command: Generated command
            result: Command execution result
            success: Whether command succeeded
        """
        if not self.enabled:
            return

        # Update session
        self.session.add_interaction(query, command, result, success)

        # Update directory patterns (only successful commands)
        if success:
            self.directory.add_pattern(command)

        # Update preferences
        self.preferences.record_command(command, success)

    def cleanup_old_memory(self) -> None:
        """Cleanup old memory entries to manage storage size."""
        if not self.enabled:
            return

        # Session is automatically limited by max_interactions
        # Directory patterns limited by max_patterns
        # Preferences limited by max_patterns

        # Additional cleanup could be done here based on timestamps
        pass

    def get_memory_stats(self) -> dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            dict: Memory statistics
        """
        return {
            "session_count": len(self.session.interactions),
            "directory_patterns": len(self.directory.patterns),
            "preference_patterns": len(self.preferences.command_patterns),
            "enabled": self.enabled,
        }

    def format_memory_context(self) -> str:
        """
        Format all memory context for LLM injection.

        Returns:
            str: Combined formatted memory context
        """
        if not self.enabled:
            return ""

        parts = []

        # Session context
        session_ctx = self.session.format_for_context()
        if session_ctx:
            parts.append(session_ctx)

        # Directory context
        dir_ctx = self.directory.format_for_context()
        if dir_ctx:
            parts.append(dir_ctx)

        # Preferences context
        pref_ctx = self.preferences.format_for_context()
        if pref_ctx:
            parts.append(pref_ctx)

        return "\n\n".join(parts)
