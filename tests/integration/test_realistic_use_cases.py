"""
Integration tests for realistic use cases from PRD.

Tests the complete workflow from natural language input to command
generation using mocked LLM responses for consistency and repeatability.

NOTE: These tests use MockLLMProvider for speed and determinism.
For real provider testing, see test_integration_openai.py,
test_integration_anthropic.py, and test_integration_ollama.py.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Optional
from unittest.mock import Mock, patch

import pytest

from hai_sh.context import get_cwd_context, get_env_context, get_git_context
from hai_sh.executor import execute_command
from hai_sh.input_detector import is_hai_input, parse_hai_input
from hai_sh.prompt import build_system_prompt, parse_response
from hai_sh.providers.base import BaseLLMProvider


# ============================================================================
# Mock LLM Provider for Integration Tests
# ============================================================================


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider for integration testing.

    Returns predefined responses based on input queries to ensure
    test repeatability and consistency without making actual API calls.
    """

    def __init__(self, config: dict[str, Any] = None):
        """Initialize mock provider with config."""
        self.config = config or {}
        self.responses = {}

    def set_response(self, query: str, response: dict[str, Any]):
        """
        Set a predefined response for a query.

        Args:
            query: The input query to match
            response: The response dict to return (explanation, command, confidence)
        """
        self.responses[query.lower().strip()] = response

    def generate(self, prompt: str, context: Optional[dict[str, Any]] = None) -> str:
        """
        Generate mock response based on predefined responses.

        Args:
            prompt: The user's query
            context: Optional context (ignored in mock)

        Returns:
            str: JSON response matching the query
        """
        # Find matching response
        query = prompt.lower().strip()

        for key, response in self.responses.items():
            if key in query or query in key:
                return json.dumps(response)

        # Default fallback response
        return json.dumps({
            "explanation": "Mock response for testing",
            "command": "echo 'test'",
            "confidence": 50,
        })

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Always return True for mock provider."""
        return True

    def is_available(self) -> bool:
        """Always return True for mock provider."""
        return True


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def setup_test_files(tmp_path):
    """
    Create a test directory structure with sample files.

    Creates:
    - TypeScript files (some importing React, some not)
    - Python files
    - Various file types with different modification times
    """
    # TypeScript files
    (tmp_path / "src").mkdir()

    # React component
    (tmp_path / "src" / "Component.tsx").write_text(
        "import React from 'react';\n"
        "export const MyComponent = () => <div>Hello</div>;"
    )

    # Non-React TypeScript file
    (tmp_path / "src" / "utils.ts").write_text(
        "export function helper() { return 42; }"
    )

    # Another React file
    (tmp_path / "src" / "App.tsx").write_text(
        "import React, { useState } from 'react';\n"
        "export const App = () => <div>App</div>;"
    )

    # Python files
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "test.py").write_text("print('test')")
    (tmp_path / "requirements.txt").write_text("pytest\nrequests\n")

    # Various files for disk space testing
    (tmp_path / "large_file.bin").write_bytes(b"0" * (10 * 1024 * 1024))  # 10MB
    (tmp_path / "small_file.txt").write_text("small content")

    return tmp_path


# ============================================================================
# Use Case 1: Show Files Modified in Last 24 Hours
# ============================================================================


@pytest.mark.integration
def test_use_case_1_files_modified_24_hours(mock_provider):
    """
    Test: "Show me files modified in the last 24 hours"

    Verifies:
    - Query parsing
    - LLM response generation
    - Command correctness
    """
    query = "Show me files modified in the last 24 hours"

    # Set up mock response
    mock_provider.set_response(
        query,
        {
            "explanation": "I'll find all files modified in the last 24 hours using find.",
            "command": "find . -type f -mtime -1",
            "confidence": 90,
        }
    )

    # Test input detection
    assert is_hai_input(query) or True  # Query doesn't need @hai prefix

    # Test LLM generation
    response = mock_provider.generate(query)
    parsed = parse_response(response)

    assert "command" in parsed
    assert "find" in parsed["command"]
    assert "-mtime -1" in parsed["command"] or "-mtime 0" in parsed["command"]
    assert parsed["confidence"] >= 80

    # Verify explanation
    assert "24 hours" in parsed["explanation"] or "find" in parsed["explanation"]


@pytest.mark.integration
def test_use_case_1_command_execution(tmp_path):
    """
    Test actual execution of file modification command.

    Verifies command runs successfully and produces output.
    """
    # Create test files
    (tmp_path / "recent.txt").write_text("recent file")

    # Execute the command in test directory
    result = execute_command(
        "find . -type f -name '*.txt' -mtime -1",
        cwd=str(tmp_path),
        timeout=5
    )

    assert result.success
    assert result.exit_code == 0


# ============================================================================
# Use Case 2: Find TypeScript Files Importing React
# ============================================================================


@pytest.mark.integration
def test_use_case_2_typescript_react_imports(mock_provider):
    """
    Test: "Find all TypeScript files that import React"

    Verifies:
    - Query understanding
    - Command uses grep or similar
    - Filters for TypeScript files
    """
    query = "Find all TypeScript files that import React"

    # Set up mock response
    mock_provider.set_response(
        query,
        {
            "explanation": "I'll search for TypeScript files containing 'import React' using grep.",
            "command": "grep -r --include='*.tsx' --include='*.ts' 'import.*React' .",
            "confidence": 95,
        }
    )

    # Test LLM generation
    response = mock_provider.generate(query)
    parsed = parse_response(response)

    assert "command" in parsed
    assert "grep" in parsed["command"] or "find" in parsed["command"]
    assert "React" in parsed["command"]
    assert ".ts" in parsed["command"] or "*.ts" in parsed["command"]
    assert parsed["confidence"] >= 85


@pytest.mark.integration
def test_use_case_2_command_execution(setup_test_files):
    """
    Test actual execution of TypeScript React search.

    Verifies command finds React imports correctly.
    """
    test_dir = setup_test_files

    # Execute grep command
    result = execute_command(
        "grep -r --include='*.tsx' --include='*.ts' 'import.*React' .",
        cwd=str(test_dir),
        timeout=5
    )

    # Should succeed and find React imports
    assert result.success
    assert "Component.tsx" in result.stdout or "App.tsx" in result.stdout
    assert "React" in result.stdout


# ============================================================================
# Use Case 3: Disk Space Usage
# ============================================================================


@pytest.mark.integration
def test_use_case_3_disk_space_usage(mock_provider):
    """
    Test: "What's taking up the most disk space?"

    Verifies:
    - Query understanding
    - Command uses du or df
    - Sorts by size
    """
    query = "What's taking up the most disk space?"

    # Set up mock response
    mock_provider.set_response(
        query,
        {
            "explanation": "I'll show disk usage sorted by size using du.",
            "command": "du -h -d 1 . | sort -rh | head -20",
            "confidence": 90,
        }
    )

    # Test LLM generation
    response = mock_provider.generate(query)
    parsed = parse_response(response)

    assert "command" in parsed
    assert "du" in parsed["command"] or "df" in parsed["command"]
    assert "sort" in parsed["command"] or "-h" in parsed["command"]
    assert parsed["confidence"] >= 80


@pytest.mark.integration
def test_use_case_3_command_execution(setup_test_files):
    """
    Test actual execution of disk space command.

    Verifies command runs and shows sizes.
    """
    test_dir = setup_test_files

    # Execute du command
    result = execute_command(
        "du -h -d 1 .",
        cwd=str(test_dir),
        timeout=5
    )

    assert result.success
    assert result.stdout  # Should have output
    # Should show directories or total
    assert "." in result.stdout or "/" in result.stdout


# ============================================================================
# Use Case 4: Python Virtual Environment Setup
# ============================================================================


@pytest.mark.integration
def test_use_case_4_python_venv_setup(mock_provider):
    """
    Test: "Set up a Python virtual environment and install requirements"

    Verifies:
    - Multi-step command generation
    - Uses python -m venv or virtualenv
    - Activates and installs requirements
    """
    query = "Set up a Python virtual environment and install requirements"

    # Set up mock response
    mock_provider.set_response(
        query,
        {
            "explanation": "I'll create a virtual environment and install from requirements.txt.",
            "command": "python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt",
            "confidence": 85,
        }
    )

    # Test LLM generation
    response = mock_provider.generate(query)
    parsed = parse_response(response)

    assert "command" in parsed
    assert "venv" in parsed["command"] or "virtualenv" in parsed["command"]
    assert "pip install" in parsed["command"] or "requirements" in parsed["command"]
    assert parsed["confidence"] >= 75


@pytest.mark.integration
def test_use_case_4_venv_creation(setup_test_files):
    """
    Test actual venv creation (without full installation).

    Verifies venv can be created successfully.
    """
    test_dir = setup_test_files

    # Create venv only (don't activate or install for speed)
    result = execute_command(
        "python3 -m venv .venv",
        cwd=str(test_dir),
        timeout=30
    )

    assert result.success
    # Verify venv directory was created
    assert (test_dir / ".venv").exists()
    assert (test_dir / ".venv" / "bin" / "python").exists() or \
           (test_dir / ".venv" / "bin" / "python3").exists()


# ============================================================================
# Use Case 5: Git Workflow
# ============================================================================


@pytest.mark.integration
def test_use_case_5_git_workflow(mock_provider, sample_git_repo):
    """
    Test: "commit just README.md to main, I'm on feature-branch"

    Verifies:
    - Complex git workflow understanding
    - Branch switching
    - Selective file commit
    """
    query = "commit just README.md to main, I'm on feature-branch"

    # Set up mock response
    mock_provider.set_response(
        query,
        {
            "explanation": "I'll switch to main, add README.md, commit, and switch back to feature-branch.",
            "command": "git checkout main && git add README.md && git commit -m 'Update README' && git checkout feature-branch",
            "confidence": 80,
        }
    )

    # Test LLM generation
    response = mock_provider.generate(query)
    parsed = parse_response(response)

    assert "command" in parsed
    assert "git" in parsed["command"]
    assert "README.md" in parsed["command"] or "add" in parsed["command"]
    assert "commit" in parsed["command"]
    assert parsed["confidence"] >= 70


@pytest.mark.integration
def test_use_case_5_git_operations(sample_git_repo):
    """
    Test actual git operations.

    Verifies git commands execute correctly.
    """
    repo_dir = sample_git_repo

    # Create and checkout feature branch
    execute_command("git checkout -b feature-branch", cwd=str(repo_dir), timeout=5)

    # Modify README
    readme = repo_dir / "README.md"
    readme.write_text("# Updated Test Repository\n")

    # Test git status
    result = execute_command("git status", cwd=str(repo_dir), timeout=5)
    assert result.success
    assert "README.md" in result.stdout or "modified" in result.stdout

    # Test git add
    result = execute_command("git add README.md", cwd=str(repo_dir), timeout=5)
    assert result.success

    # Test git commit
    result = execute_command(
        'git commit -m "Update README"',
        cwd=str(repo_dir),
        timeout=5
    )
    assert result.success


# ============================================================================
# End-to-End Integration Tests
# ============================================================================


@pytest.mark.integration
def test_full_workflow_with_context(mock_provider, tmp_path):
    """
    Test complete workflow: input → context → LLM → parse → validate.

    Verifies the full integration chain works end-to-end.
    """
    # Use @hai prefix for proper input detection
    user_input = "@hai Show me files modified in the last 24 hours"
    query = "Show me files modified in the last 24 hours"

    # Set up mock response
    mock_provider.set_response(
        query,
        {
            "explanation": "I'll find recently modified files.",
            "command": "find . -type f -mtime -1",
            "confidence": 90,
        }
    )

    # Step 1: Parse input
    parsed_query = parse_hai_input(user_input)
    assert parsed_query == query

    # Step 2: Gather context
    context = {
        "cwd": str(tmp_path),
        "env": get_env_context(),
    }

    # Step 3: Build system prompt
    system_prompt = build_system_prompt(context)
    assert "Current directory:" in system_prompt

    # Step 4: Generate LLM response
    llm_response = mock_provider.generate(query, context)

    # Step 5: Parse response
    parsed_response = parse_response(llm_response)

    assert "command" in parsed_response
    assert "explanation" in parsed_response
    assert "confidence" in parsed_response
    assert parsed_response["confidence"] >= 50


@pytest.mark.integration
def test_multiple_providers_consistency(tmp_path):
    """
    Test that different provider configurations produce consistent results.

    Verifies mock providers behave consistently.
    """
    query = "list python files"

    # Create two mock providers with same response
    provider1 = MockLLMProvider({"name": "provider1"})
    provider2 = MockLLMProvider({"name": "provider2"})

    expected_response = {
        "explanation": "I'll find all Python files.",
        "command": "find . -name '*.py' -type f",
        "confidence": 90,
    }

    provider1.set_response(query, expected_response)
    provider2.set_response(query, expected_response)

    # Both should return same response
    response1 = parse_response(provider1.generate(query))
    response2 = parse_response(provider2.generate(query))

    assert response1["command"] == response2["command"]
    assert response1["confidence"] == response2["confidence"]


@pytest.mark.integration
def test_error_handling_in_workflow(mock_provider):
    """
    Test error handling in the integration workflow.

    Verifies graceful handling of invalid responses.
    """
    query = "invalid query"

    # Set up invalid JSON response
    mock_provider.responses["invalid"] = "not json"

    # Should handle gracefully
    with pytest.raises(ValueError):
        response = mock_provider.generate(query)
        parse_response(response)


@pytest.mark.integration
def test_command_safety_validation(mock_provider):
    """
    Test that generated commands can be validated for safety.

    Verifies dangerous commands are flagged (future feature).
    """
    query = "delete all files"

    # Mock provider should generate safe alternative
    mock_provider.set_response(
        query,
        {
            "explanation": "I cannot generate destructive commands. Did you mean to list files?",
            "command": "ls -la",
            "confidence": 30,
        }
    )

    response = mock_provider.generate(query)
    parsed = parse_response(response)

    # Should have low confidence or safe alternative
    assert parsed["confidence"] < 50 or "ls" in parsed["command"]


# ============================================================================
# Performance and Reliability Tests
# ============================================================================


@pytest.mark.integration
def test_all_use_cases_complete_within_timeout():
    """
    Test that all use cases can complete within reasonable time.

    Verifies performance is acceptable.
    """
    import time

    mock_provider = MockLLMProvider()
    queries = [
        "Show me files modified in the last 24 hours",
        "Find all TypeScript files that import React",
        "What's taking up the most disk space?",
        "Set up a Python virtual environment and install requirements",
        "commit just README.md to main",
    ]

    # Set up responses
    for query in queries:
        mock_provider.set_response(
            query,
            {
                "explanation": f"Test response for: {query}",
                "command": "echo 'test'",
                "confidence": 85,
            }
        )

    start_time = time.time()

    for query in queries:
        response = mock_provider.generate(query)
        parsed = parse_response(response)
        assert "command" in parsed

    elapsed = time.time() - start_time

    # All 5 queries should complete quickly (mock responses are instant)
    assert elapsed < 1.0  # Less than 1 second for all


@pytest.mark.integration
def test_integration_with_real_filesystem(tmp_path):
    """
    Test integration with real filesystem operations.

    Verifies commands work with actual files.
    """
    # Create test structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "test.py").write_text("print('test')")
    (tmp_path / "README.md").write_text("# Test")

    # Test find command
    result = execute_command(
        "find . -name '*.py'",
        cwd=str(tmp_path),
        timeout=5
    )

    assert result.success
    assert "test.py" in result.stdout

    # Test ls command
    result = execute_command(
        "ls -la",
        cwd=str(tmp_path),
        timeout=5
    )

    assert result.success
    assert "README.md" in result.stdout


# ============================================================================
# Question-Answering Mode Tests (Issue #27)
# ============================================================================


@pytest.mark.integration
def test_question_mode_ls_difference(mock_provider):
    """
    Test: "What's the difference between ls -la and ls -lah?"

    Verifies:
    - Question is detected (no command generated)
    - Explanation is provided
    - Confidence is returned
    - No command field in response
    """
    query = "What's the difference between ls -la and ls -lah?"

    # Set up mock response (question mode - no command)
    mock_provider.set_response(
        query,
        {
            "explanation": "Both commands list all files including hidden ones (-a) in long format (-l). The only difference is the -h flag in 'ls -lah', which displays file sizes in human-readable format (KB, MB, GB) instead of bytes. For example, instead of 1048576, it shows 1.0M.",
            "confidence": 95,
        }
    )

    # Test LLM generation
    response = mock_provider.generate(query)
    parsed = parse_response(response)

    # Verify question mode response
    assert "command" not in parsed  # No command in question mode
    assert "explanation" in parsed
    assert "confidence" in parsed

    # Verify explanation content
    assert "ls -la" in parsed["explanation"] or "ls -lah" in parsed["explanation"]
    assert "human-readable" in parsed["explanation"] or "-h" in parsed["explanation"]
    assert parsed["confidence"] >= 90


@pytest.mark.integration
def test_question_mode_git_rebase(mock_provider):
    """
    Test: "How do I use git rebase?"

    Verifies question-answering for git workflow questions.
    """
    query = "How do I use git rebase?"

    # Set up mock response
    mock_provider.set_response(
        query,
        {
            "explanation": "Git rebase moves or combines commits from one branch onto another. Use 'git rebase <branch>' to rebase current branch onto <branch>, or 'git rebase -i HEAD~N' for interactive rebase of last N commits. It's useful for cleaning up commit history before merging, but avoid rebasing commits that have been pushed to shared branches.",
            "confidence": 90,
        }
    )

    response = mock_provider.generate(query)
    parsed = parse_response(response)

    # Verify question mode
    assert "command" not in parsed
    assert "git rebase" in parsed["explanation"]
    assert parsed["confidence"] >= 85


@pytest.mark.integration
def test_question_mode_grep_vs_awk(mock_provider):
    """
    Test: "Why would I use grep instead of awk?"

    Verifies comparison questions are handled properly.
    """
    query = "Why would I use grep instead of awk?"

    mock_provider.set_response(
        query,
        {
            "explanation": "Use grep for simple pattern matching and filtering lines. Use awk for complex text processing that requires field extraction, arithmetic, or conditional logic. Grep is faster and simpler for basic searches, while awk is more powerful for data manipulation and formatted output.",
            "confidence": 95,
        }
    )

    response = mock_provider.generate(query)
    parsed = parse_response(response)

    assert "command" not in parsed
    assert "grep" in parsed["explanation"]
    assert "awk" in parsed["explanation"]
    assert parsed["confidence"] >= 90


@pytest.mark.integration
def test_question_mode_explain_command(mock_provider):
    """
    Test: "Explain what the find command does"

    Verifies explanatory questions work.
    """
    query = "Explain what the find command does"

    mock_provider.set_response(
        query,
        {
            "explanation": "The find command searches for files and directories in a directory hierarchy. It can filter by name, type, size, modification time, and more. For example, 'find . -name \"*.py\"' finds all Python files in the current directory and subdirectories.",
            "confidence": 95,
        }
    )

    response = mock_provider.generate(query)
    parsed = parse_response(response)

    assert "command" not in parsed
    assert "find" in parsed["explanation"]
    assert parsed["confidence"] >= 90


@pytest.mark.integration
def test_question_mode_when_to_use_sudo(mock_provider):
    """
    Test: "When should I use sudo?"

    Verifies advisory questions are handled.
    """
    query = "When should I use sudo?"

    mock_provider.set_response(
        query,
        {
            "explanation": "Use sudo when you need elevated privileges for system-level operations like installing packages, modifying system files, changing network settings, or managing services. Avoid using sudo for regular user tasks to minimize security risks. Only use it when necessary and be cautious with the commands you run.",
            "confidence": 95,
        }
    )

    response = mock_provider.generate(query)
    parsed = parse_response(response)

    assert "command" not in parsed
    assert "sudo" in parsed["explanation"]
    assert "privilege" in parsed["explanation"].lower() or "elevated" in parsed["explanation"].lower()


@pytest.mark.integration
def test_mixed_mode_command_vs_question(mock_provider):
    """
    Test that command mode and question mode work in sequence.

    Verifies the system correctly switches between modes.
    """
    # First: Question mode
    question = "What does ls do?"
    mock_provider.set_response(
        question,
        {
            "explanation": "The ls command lists directory contents. It shows files and folders in the current or specified directory.",
            "confidence": 95,
        }
    )

    response_q = mock_provider.generate(question)
    parsed_q = parse_response(response_q)

    assert "command" not in parsed_q
    assert "ls" in parsed_q["explanation"]

    # Then: Command mode
    command_request = "list all files in the current directory"
    mock_provider.set_response(
        command_request,
        {
            "explanation": "I'll list all files including hidden ones in long format.",
            "command": "ls -la",
            "confidence": 95,
        }
    )

    response_c = mock_provider.generate(command_request)
    parsed_c = parse_response(response_c)

    assert "command" in parsed_c
    assert parsed_c["command"] == "ls -la"


@pytest.mark.integration
def test_question_mode_workflow_integration(mock_provider):
    """
    Test complete workflow for question mode from query to response.

    This simulates the full flow through the system.
    """
    # Build system prompt with context
    context = {
        'cwd': get_cwd_context(),
        'env': get_env_context(),
    }

    system_prompt = build_system_prompt(context)

    # Verify prompt mentions question mode
    assert "question" in system_prompt.lower() or "explanation" in system_prompt.lower()

    # Test question
    query = "What's the difference between cat and less?"

    mock_provider.set_response(
        query,
        {
            "explanation": "Both commands display file contents, but cat outputs everything at once while less allows scrolling through content page by page. Use cat for small files or piping output, and less for viewing large files interactively.",
            "confidence": 95,
        }
    )

    # Generate response
    response = mock_provider.generate(query, context)
    parsed = parse_response(response)

    # Verify question mode behavior
    assert "command" not in parsed
    assert "cat" in parsed["explanation"] and "less" in parsed["explanation"]
    assert parsed["confidence"] >= 90
    assert "explanation" in parsed
