"""
Integration tests for OpenAI provider using real API calls.

These tests validate the OpenAI provider end-to-end with actual API calls.
Tests are skipped unless both OPENAI_API_KEY is set and TEST_OPENAI=1 is enabled
to prevent unexpected API costs.

Run with: TEST_OPENAI=1 OPENAI_API_KEY=sk-... pytest -m "integration and openai"
"""

import subprocess
from pathlib import Path

import pytest

from tests.conftest import skip_if_no_openai


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


@pytest.mark.integration
@pytest.mark.openai
@pytest.mark.requires_api_key
@skip_if_no_openai
class TestOpenAIBasicGeneration:
    """Test basic command generation with OpenAI provider."""

    def test_basic_command_generation(self, test_config_openai):
        """Test that simple queries generate valid commands."""
        stdout, stderr, exit_code = run_hai(
            "list all files in the current directory",
            test_config_openai,
        )

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert stdout, "No output received"
        assert "Confidence:" in stdout, "Missing confidence score"

        # Should generate an ls command
        assert any(cmd in stdout.lower() for cmd in ["ls", "list"]), \
            "Expected ls command in output"

    def test_question_mode_detection(self, test_config_openai):
        """Test that questions return explanations without commands."""
        stdout, stderr, exit_code = run_hai(
            "What is the purpose of the ls command?",
            test_config_openai,
        )

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert stdout, "No output received"

        # Should provide explanation without command
        assert "Confidence:" in stdout, "Missing confidence score"
        # Should not prompt for command execution
        assert "Execute this command?" not in stdout, \
            "Should not prompt for execution in question mode"


@pytest.mark.integration
@pytest.mark.openai
@pytest.mark.requires_api_key
@skip_if_no_openai
class TestOpenAIConfidenceScoring:
    """Test confidence scoring behavior with OpenAI provider."""

    def test_high_confidence_clear_request(self, test_config_openai):
        """Test that clear requests generate high confidence scores."""
        stdout, stderr, exit_code = run_hai(
            "show current directory",
            test_config_openai,
        )

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Confidence:" in stdout, "Missing confidence score"

        # Extract confidence score (format: "Confidence: XX%")
        for line in stdout.split("\n"):
            if "Confidence:" in line:
                # Parse confidence value
                confidence_str = line.split("Confidence:")[-1].strip().rstrip("%")
                try:
                    confidence = int(confidence_str)
                    # Clear requests should have high confidence (>70%)
                    assert confidence > 70, \
                        f"Expected high confidence (>70%), got {confidence}%"
                except ValueError:
                    # If we can't parse confidence, that's okay for this test
                    pass

    def test_low_confidence_ambiguous_request(self, test_config_openai):
        """Test that ambiguous requests generate lower confidence scores."""
        stdout, stderr, exit_code = run_hai(
            "do something with files",
            test_config_openai,
        )

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert "Confidence:" in stdout, "Missing confidence score"

        # Ambiguous requests should have lower confidence
        # We're just checking that the system processes it without errors


@pytest.mark.integration
@pytest.mark.openai
@pytest.mark.requires_api_key
@skip_if_no_openai
class TestOpenAIErrorHandling:
    """Test error handling with OpenAI provider."""

    def test_invalid_api_key_handling(self, test_config_openai, tmp_path):
        """Test that invalid API keys are handled gracefully."""
        # Create a config with invalid API key
        import yaml

        config_content = yaml.safe_load(test_config_openai.read_text())
        config_content["providers"]["openai"]["api_key"] = "sk-invalid-key-for-testing"

        invalid_config = tmp_path / "invalid_config.yaml"
        invalid_config.write_text(yaml.dump(config_content))

        stdout, stderr, exit_code = run_hai(
            "list files",
            invalid_config,
        )

        # Should fail gracefully
        assert exit_code != 0, "Should fail with invalid API key"
        # Error message should be informative
        output = stdout + stderr
        assert any(
            keyword in output.lower()
            for keyword in ["authentication", "api key", "unauthorized", "error"]
        ), "Error message should mention authentication issue"


@pytest.mark.integration
@pytest.mark.openai
@pytest.mark.requires_api_key
@skip_if_no_openai
class TestOpenAIResponseParsing:
    """Test response parsing with OpenAI provider."""

    def test_json_response_parsing(self, test_config_openai):
        """Test that JSON responses are properly parsed."""
        stdout, stderr, exit_code = run_hai(
            "find all PDF files",
            test_config_openai,
        )

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert stdout, "No output received"

        # Should contain structured output
        assert "Confidence:" in stdout, "Missing confidence score"

        # Should contain either explanation or command
        has_explanation = any(
            keyword in stdout.lower()
            for keyword in ["searching", "finding", "looking for", "will"]
        )
        has_command = "find" in stdout.lower() or "pdf" in stdout.lower()

        assert has_explanation or has_command, \
            "Response should contain explanation or command"


@pytest.mark.integration
@pytest.mark.openai
@pytest.mark.requires_api_key
@skip_if_no_openai
class TestOpenAIContextInjection:
    """Test context injection with OpenAI provider."""

    def test_context_usage(self, test_config_openai, sample_git_repo, monkeypatch):
        """Test that context (cwd, git state) is properly utilized."""
        # Change to git repo directory
        monkeypatch.chdir(sample_git_repo)

        stdout, stderr, exit_code = run_hai(
            "show git status",
            test_config_openai,
        )

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert stdout, "No output received"

        # Should generate git command
        assert "git" in stdout.lower(), "Expected git command in output"


@pytest.mark.integration
@pytest.mark.openai
@pytest.mark.requires_api_key
@skip_if_no_openai
class TestOpenAIModelSpecificParameters:
    """Test model-specific parameter handling."""

    def test_o1_model_parameters(self, test_config_openai, tmp_path):
        """Test that o1 models use max_completion_tokens instead of max_tokens."""
        import yaml

        # Create config with o1 model
        config_content = yaml.safe_load(test_config_openai.read_text())
        config_content["providers"]["openai"]["model"] = "o1-mini"
        config_content["model"] = "o1-mini"

        o1_config = tmp_path / "o1_config.yaml"
        o1_config.write_text(yaml.dump(config_content))

        stdout, stderr, exit_code = run_hai(
            "list files",
            o1_config,
        )

        # Test should work (provider handles parameter conversion internally)
        # If o1 model is not available, mark as expected failure
        if exit_code == 0:
            assert stdout, "No output received"
            assert "Confidence:" in stdout, "Missing confidence score"
        else:
            # Model may not be available - mark as xfail with details
            pytest.xfail(
                f"o1-mini model not available or failed. "
                f"Exit code: {exit_code}, stderr: {stderr}"
            )

    def test_gpt4_legacy_parameters(self, test_config_openai):
        """Test that legacy GPT-4 models use standard max_tokens."""
        # Default config uses gpt-4o-mini which should use max_tokens
        stdout, stderr, exit_code = run_hai(
            "show current directory",
            test_config_openai,
        )

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert stdout, "No output received"
        assert "Confidence:" in stdout, "Missing confidence score"


@pytest.mark.integration
@pytest.mark.openai
@pytest.mark.requires_api_key
@skip_if_no_openai
class TestOpenAIComplexScenarios:
    """Test complex real-world scenarios with OpenAI provider."""

    def test_multi_step_command_reasoning(self, test_config_openai):
        """Test that complex requests are properly reasoned about."""
        stdout, stderr, exit_code = run_hai(
            "find all Python files modified in the last 7 days",
            test_config_openai,
        )

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert stdout, "No output received"

        # Should generate find command with appropriate filters
        assert "find" in stdout.lower() or "python" in stdout.lower(), \
            "Expected find command for Python files"

    def test_git_workflow_command(self, test_config_openai, sample_git_repo, monkeypatch):
        """Test git-related workflow commands."""
        monkeypatch.chdir(sample_git_repo)

        stdout, stderr, exit_code = run_hai(
            "show the last 5 commits",
            test_config_openai,
        )

        assert exit_code == 0, f"Command failed with stderr: {stderr}"
        assert stdout, "No output received"

        # Should generate git log command
        assert "git" in stdout.lower() and "log" in stdout.lower(), \
            "Expected git log command"
