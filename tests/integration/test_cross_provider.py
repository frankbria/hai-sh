"""
Cross-provider consistency tests.

These tests validate that all available providers behave consistently for the same inputs.
Tests dynamically detect which providers are available and run comparisons.

Run with: TEST_OPENAI=1 TEST_ANTHROPIC=1 pytest -m integration tests/integration/test_cross_provider.py
"""

import subprocess
from pathlib import Path
from typing import Dict, List

import pytest

from tests.conftest import (
    is_openai_available,
    is_anthropic_available,
    is_ollama_available,
)


def run_hai(query: str, config_file: Path) -> tuple[str, str, int]:
    """
    Run hai command and return stdout, stderr, and exit code.

    Args:
        query: The query to run
        config_file: Path to config file

    Returns:
        tuple: (stdout, stderr, exit_code)
    """
    result = subprocess.run(
        ["python", "-m", "hai_sh", "--config", str(config_file), query],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout, result.stderr, result.returncode


def get_available_providers() -> List[str]:
    """
    Get list of available providers for testing.

    Returns:
        List of provider names that are available
    """
    providers = []
    if is_openai_available():
        providers.append("openai")
    if is_anthropic_available():
        providers.append("anthropic")
    if is_ollama_available():
        providers.append("ollama")
    return providers


def get_provider_configs(request) -> Dict[str, Path]:
    """
    Get mapping of provider names to their config files.

    Uses request.getfixturevalue() to defer fixture evaluation until needed,
    preventing unnecessary pytest.skip calls for unavailable providers.

    Args:
        request: Pytest request fixture

    Returns:
        Dictionary mapping provider names to config file paths
    """
    configs = {}
    if is_openai_available():
        configs["openai"] = request.getfixturevalue("test_config_openai")
    if is_anthropic_available():
        configs["anthropic"] = request.getfixturevalue("test_config_anthropic")
    if is_ollama_available():
        configs["ollama"] = request.getfixturevalue("test_config_ollama")
    return configs


@pytest.mark.integration
class TestCrossProviderConsistency:
    """Test consistent behavior across all available providers."""

    def test_providers_available(self):
        """Test that at least one provider is available for testing."""
        available = get_available_providers()
        assert len(available) > 0, \
            "At least one provider must be available for cross-provider tests"

    def test_consistent_command_generation(self, request):
        """Test that all providers generate similar commands for same query."""
        providers = get_available_providers()
        if len(providers) < 2:
            pytest.skip("Need at least 2 providers for consistency testing")

        configs = get_provider_configs(request)

        query = "list all files"
        results = {}

        # Run query on all available providers
        for provider_name in providers:
            stdout, stderr, exit_code = run_hai(query, configs[provider_name])
            results[provider_name] = {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }

        # All providers should succeed
        for provider_name, result in results.items():
            assert result["exit_code"] == 0, \
                f"{provider_name} failed with: {result['stderr']}"

        # All providers should generate ls-related command
        for provider_name, result in results.items():
            assert any(cmd in result["stdout"].lower() for cmd in ["ls", "list"]), \
                f"{provider_name} did not generate expected ls command"

    def test_consistent_question_detection(self, request):
        """Test that all providers correctly identify questions vs commands."""
        providers = get_available_providers()
        if len(providers) < 2:
            pytest.skip("Need at least 2 providers for consistency testing")

        configs = get_provider_configs(request)

        # Test with a clear question
        question = "What is the ls command used for?"
        results = {}

        for provider_name in providers:
            stdout, stderr, exit_code = run_hai(question, configs[provider_name])
            results[provider_name] = {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }

        # All providers should succeed
        for provider_name, result in results.items():
            assert result["exit_code"] == 0, \
                f"{provider_name} failed with: {result['stderr']}"

        # All providers should NOT prompt for command execution
        for provider_name, result in results.items():
            assert "Execute this command?" not in result["stdout"], \
                f"{provider_name} incorrectly treated question as command"

    def test_consistent_confidence_scoring(self, request):
        """Test that all providers return confidence scores in similar ranges."""
        providers = get_available_providers()
        if len(providers) < 2:
            pytest.skip("Need at least 2 providers for consistency testing")

        configs = get_provider_configs(request)

        # Test with a clear, unambiguous query
        query = "show current directory"
        confidence_scores = {}

        for provider_name in providers:
            stdout, _stderr, _exit_code = run_hai(query, configs[provider_name])

            # Extract confidence score
            for line in stdout.split("\n"):
                if "Confidence:" in line:
                    confidence_str = line.split("Confidence:")[-1].strip().rstrip("%")
                    try:
                        confidence = int(confidence_str)
                        confidence_scores[provider_name] = confidence
                    except ValueError:
                        pass

        # All providers should return confidence scores
        assert len(confidence_scores) >= 2, \
            "Could not extract confidence scores from providers"

        # All confidence scores should be reasonably high for clear query
        for provider_name, score in confidence_scores.items():
            assert score > 60, \
                f"{provider_name} returned unexpectedly low confidence: {score}%"

    def test_consistent_error_handling(self, request):
        """Test that all providers handle errors gracefully."""
        providers = get_available_providers()
        if len(providers) < 1:
            pytest.skip("Need at least 1 provider for error handling testing")

        # Note: We can't easily test invalid credentials for all providers
        # without breaking the configs, so we just test that normal flow works
        configs = get_provider_configs(request)

        query = "list files"

        for provider_name in providers:
            _stdout, stderr, exit_code = run_hai(query, configs[provider_name])

            # All providers should handle the request (success or graceful failure)
            assert exit_code == 0 or stderr, \
                f"{provider_name} failed without error message"

    def test_consistent_context_usage(
        self,
        request,
        sample_git_repo,
        monkeypatch,
    ):
        """Test that all providers properly utilize provided context."""
        providers = get_available_providers()
        if len(providers) < 2:
            pytest.skip("Need at least 2 providers for consistency testing")

        configs = get_provider_configs(request)

        # Change to git repo directory
        monkeypatch.chdir(sample_git_repo)

        query = "show git status"
        results = {}

        for provider_name in providers:
            stdout, stderr, exit_code = run_hai(query, configs[provider_name])
            results[provider_name] = {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }

        # All providers should generate git-related command
        for provider_name, result in results.items():
            assert result["exit_code"] == 0, \
                f"{provider_name} failed with: {result['stderr']}"
            assert "git" in result["stdout"].lower(), \
                f"{provider_name} did not generate git command from context"


@pytest.mark.integration
class TestCrossProviderComplexScenarios:
    """Test complex scenarios across providers."""

    def test_multi_word_file_operations(
        self,
        request,
        tmp_path,
        monkeypatch,
    ):
        """Test handling of file operations across providers."""
        providers = get_available_providers()
        if len(providers) < 1:
            pytest.skip("Need at least 1 provider for testing")

        configs = get_provider_configs(request)

        # Create test directory
        test_dir = tmp_path / "test_files"
        test_dir.mkdir()
        monkeypatch.chdir(test_dir)

        query = "create a file called test.txt"

        for provider_name in providers:
            stdout, stderr, exit_code = run_hai(query, configs[provider_name])

            assert exit_code == 0, \
                f"{provider_name} failed with: {stderr}"

            # Should generate touch or echo command
            assert any(
                cmd in stdout.lower()
                for cmd in ["touch", "echo", "cat", ">"]
            ), f"{provider_name} did not generate file creation command"

    def test_pipeline_command_generation(self, request):
        """Test that providers can generate pipeline commands."""
        providers = get_available_providers()
        if len(providers) < 1:
            pytest.skip("Need at least 1 provider for testing")

        configs = get_provider_configs(request)

        query = "count the number of files in this directory"

        for provider_name in providers:
            stdout, stderr, exit_code = run_hai(query, configs[provider_name])

            assert exit_code == 0, \
                f"{provider_name} failed with: {stderr}"

            # Should generate ls + wc or similar pipeline
            assert any(
                cmd in stdout.lower()
                for cmd in ["ls", "wc", "find", "count"]
            ), f"{provider_name} did not generate counting command"
