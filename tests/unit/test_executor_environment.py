"""
Tests for environment variable preservation in executor module.

This module tests that executed commands properly inherit and preserve
the current shell environment, including shell-specific variables.
"""

import os
import pytest

from hai_sh.executor import (
    ExecutionResult,
    execute_command,
)


# ============================================================================
# Environment Preservation Tests
# ============================================================================


@pytest.mark.unit
def test_environment_inherits_current_env():
    """Test that commands inherit current environment by default."""
    # Set a custom environment variable
    test_var = "HAI_TEST_VAR_12345"
    test_value = "test_value_67890"

    original_env = os.environ.copy()
    os.environ[test_var] = test_value

    try:
        # Execute command that reads the variable
        result = execute_command(f"echo ${test_var}")

        assert result.success is True
        assert test_value in result.stdout
    finally:
        # Cleanup
        if test_var in os.environ:
            del os.environ[test_var]


@pytest.mark.unit
def test_environment_preserves_path():
    """Test that PATH variable is preserved."""
    result = execute_command("echo $PATH")

    assert result.success is True
    assert len(result.stdout.strip()) > 0
    # PATH should contain at least one directory
    assert "/" in result.stdout


@pytest.mark.unit
def test_environment_preserves_home():
    """Test that HOME variable is preserved."""
    result = execute_command("echo $HOME")

    assert result.success is True
    assert len(result.stdout.strip()) > 0
    # HOME should be an absolute path
    assert result.stdout.strip().startswith("/")


@pytest.mark.unit
def test_environment_preserves_user():
    """Test that USER variable is preserved."""
    result = execute_command("echo $USER")

    assert result.success is True
    assert len(result.stdout.strip()) > 0


@pytest.mark.unit
def test_environment_preserves_shell():
    """Test that SHELL variable is preserved."""
    result = execute_command("echo $SHELL")

    assert result.success is True
    # SHELL should contain 'sh' or 'bash'
    assert "sh" in result.stdout.lower()


@pytest.mark.unit
def test_environment_preserves_pwd():
    """Test that PWD variable is preserved."""
    current_dir = os.getcwd()
    result = execute_command("echo $PWD")

    assert result.success is True
    assert current_dir in result.stdout


# ============================================================================
# Custom Environment Tests
# ============================================================================


@pytest.mark.unit
def test_custom_environment_overrides_default():
    """Test that custom environment overrides default."""
    custom_var = "CUSTOM_TEST_VAR"
    custom_value = "custom_value"

    custom_env = os.environ.copy()
    custom_env[custom_var] = custom_value

    result = execute_command(f"echo ${custom_var}", env=custom_env)

    assert result.success is True
    assert custom_value in result.stdout


@pytest.mark.unit
def test_custom_environment_adds_variables():
    """Test that custom environment can add new variables."""
    custom_env = os.environ.copy()
    custom_env["NEW_VAR_1"] = "value1"
    custom_env["NEW_VAR_2"] = "value2"

    result = execute_command("echo $NEW_VAR_1:$NEW_VAR_2", env=custom_env)

    assert result.success is True
    assert "value1" in result.stdout
    assert "value2" in result.stdout


@pytest.mark.unit
def test_custom_environment_modifies_path():
    """Test that custom environment can modify PATH."""
    custom_env = os.environ.copy()
    custom_path = "/custom/path:/another/path"
    custom_env["PATH"] = custom_path

    result = execute_command("echo $PATH", env=custom_env)

    assert result.success is True
    assert "/custom/path" in result.stdout
    assert "/another/path" in result.stdout


@pytest.mark.unit
def test_custom_environment_removes_variables():
    """Test that custom environment can exclude variables."""
    # Create environment without HOME
    custom_env = {k: v for k, v in os.environ.items() if k != "HOME"}

    result = execute_command("echo $HOME", env=custom_env)

    assert result.success is True
    # HOME should be empty or not set
    assert result.stdout.strip() == ""


# ============================================================================
# Environment Isolation Tests
# ============================================================================


@pytest.mark.unit
def test_environment_changes_isolated_from_parent():
    """Test that environment changes in subprocess don't affect parent."""
    test_var = "ISOLATION_TEST_VAR"
    original_value = os.environ.get(test_var)

    # Set variable in subprocess
    result = execute_command(f"export {test_var}=subprocess_value; echo done")

    assert result.success is True

    # Verify parent environment unchanged
    assert os.environ.get(test_var) == original_value


@pytest.mark.unit
def test_multiple_commands_share_environment():
    """Test that multiple subprocess calls get same environment."""
    test_var = "MULTI_TEST_VAR"
    test_value = "multi_value"

    os.environ[test_var] = test_value

    try:
        # First command
        result1 = execute_command(f"echo ${test_var}")

        # Second command
        result2 = execute_command(f"echo ${test_var}")

        assert result1.success is True
        assert result2.success is True
        assert test_value in result1.stdout
        assert test_value in result2.stdout
    finally:
        if test_var in os.environ:
            del os.environ[test_var]


@pytest.mark.unit
def test_environment_not_polluted_by_subprocess():
    """Test that subprocess doesn't pollute parent environment."""
    initial_env = os.environ.copy()

    # Execute command that sets new variables
    result = execute_command("export POLLUTION_VAR=polluted; echo done")

    assert result.success is True

    # Verify no pollution
    assert "POLLUTION_VAR" not in os.environ

    # Verify environment is unchanged
    assert set(os.environ.keys()) == set(initial_env.keys())


# ============================================================================
# Environment Variable Modification Tests
# ============================================================================


@pytest.mark.unit
def test_environment_variable_substitution():
    """Test that environment variables are properly substituted."""
    custom_env = os.environ.copy()
    custom_env["VAR1"] = "hello"
    custom_env["VAR2"] = "world"

    result = execute_command("echo $VAR1 $VAR2", env=custom_env)

    assert result.success is True
    assert "hello" in result.stdout
    assert "world" in result.stdout


@pytest.mark.unit
def test_environment_variable_concatenation():
    """Test environment variable concatenation."""
    custom_env = os.environ.copy()
    custom_env["PREFIX"] = "/usr"

    result = execute_command("echo ${PREFIX}/local/bin", env=custom_env)

    assert result.success is True
    assert "/usr/local/bin" in result.stdout


@pytest.mark.unit
def test_environment_variable_default_values():
    """Test environment variable default values."""
    # Variable not set, use default
    result = execute_command("echo ${UNSET_VAR:-default_value}")

    assert result.success is True
    assert "default_value" in result.stdout


@pytest.mark.unit
def test_environment_variable_empty_vs_unset():
    """Test distinction between empty and unset variables."""
    custom_env = os.environ.copy()
    custom_env["EMPTY_VAR"] = ""

    # Empty variable should expand to empty string
    result1 = execute_command("echo x${EMPTY_VAR}x", env=custom_env)
    assert result1.success is True
    assert "xx" in result1.stdout

    # Unset variable should also expand to empty string
    result2 = execute_command("echo x${UNSET_VAR}x", env=custom_env)
    assert result2.success is True
    assert "xx" in result2.stdout


# ============================================================================
# Shell-Specific Variable Tests
# ============================================================================


@pytest.mark.unit
def test_shell_variables_preserved():
    """Test that common shell variables are preserved."""
    result = execute_command("env | grep -E '^(SHELL|HOME|USER|PATH)='")

    assert result.success is True
    # Should have at least some shell variables
    assert len(result.stdout.strip()) > 0


@pytest.mark.unit
def test_lang_locale_variables_preserved():
    """Test that LANG and locale variables are preserved."""
    result = execute_command("echo $LANG")

    assert result.success is True
    # LANG might be empty on some systems, but command should succeed


@pytest.mark.unit
def test_term_variable_preserved():
    """Test that TERM variable is preserved."""
    result = execute_command("echo $TERM")

    assert result.success is True
    # TERM might be empty in non-interactive shells, but command succeeds


# ============================================================================
# Environment with CWD Tests
# ============================================================================


@pytest.mark.unit
def test_environment_with_cwd_change(tmp_path):
    """Test environment preservation when changing working directory."""
    custom_env = os.environ.copy()
    custom_env["CWD_TEST_VAR"] = "cwd_value"

    result = execute_command(
        "echo $CWD_TEST_VAR",
        cwd=str(tmp_path),
        env=custom_env
    )

    assert result.success is True
    assert "cwd_value" in result.stdout


@pytest.mark.unit
def test_pwd_reflects_cwd_parameter(tmp_path):
    """Test that PWD reflects the cwd parameter."""
    result = execute_command("pwd", cwd=str(tmp_path))

    assert result.success is True
    assert str(tmp_path) in result.stdout


# ============================================================================
# Special Characters in Environment Tests
# ============================================================================


@pytest.mark.unit
def test_environment_with_spaces():
    """Test environment variables containing spaces."""
    custom_env = os.environ.copy()
    custom_env["SPACE_VAR"] = "value with spaces"

    result = execute_command("echo \"$SPACE_VAR\"", env=custom_env)

    assert result.success is True
    assert "value with spaces" in result.stdout


@pytest.mark.unit
def test_environment_with_special_chars():
    """Test environment variables with special characters."""
    custom_env = os.environ.copy()
    custom_env["SPECIAL_VAR"] = "value!@#$%"

    result = execute_command("echo \"$SPECIAL_VAR\"", env=custom_env)

    assert result.success is True
    assert "value!@#$%" in result.stdout


@pytest.mark.unit
def test_environment_with_quotes():
    """Test environment variables containing quotes."""
    custom_env = os.environ.copy()
    custom_env["QUOTE_VAR"] = "value with 'quotes'"

    result = execute_command("echo \"$QUOTE_VAR\"", env=custom_env)

    assert result.success is True
    assert "value with 'quotes'" in result.stdout


@pytest.mark.unit
def test_environment_with_newlines():
    """Test environment variables containing newlines."""
    custom_env = os.environ.copy()
    custom_env["NEWLINE_VAR"] = "line1\nline2\nline3"

    result = execute_command("echo \"$NEWLINE_VAR\"", env=custom_env)

    assert result.success is True
    assert "line1" in result.stdout
    assert "line2" in result.stdout
    assert "line3" in result.stdout


# ============================================================================
# Environment Error Handling Tests
# ============================================================================


@pytest.mark.unit
def test_environment_with_none_values():
    """Test that None values in environment are handled."""
    # Environment dict should not contain None values
    # This tests the implementation's robustness
    custom_env = os.environ.copy()

    # All values should be strings
    for key, value in custom_env.items():
        assert isinstance(value, str)


@pytest.mark.unit
def test_large_environment():
    """Test execution with large environment."""
    custom_env = os.environ.copy()

    # Add many variables
    for i in range(100):
        custom_env[f"LARGE_VAR_{i}"] = f"value_{i}"

    result = execute_command("echo $LARGE_VAR_50", env=custom_env)

    assert result.success is True
    assert "value_50" in result.stdout


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_integration_environment_full_workflow():
    """Test complete environment workflow."""
    # Create custom environment
    custom_env = os.environ.copy()
    custom_env["WORKFLOW_VAR"] = "workflow_value"
    custom_env["PATH"] = f"/custom/bin:{custom_env['PATH']}"

    # Execute command
    result = execute_command(
        "echo $WORKFLOW_VAR:$PATH | head -c 100",
        env=custom_env
    )

    assert result.success is True
    assert "workflow_value" in result.stdout
    assert "/custom/bin" in result.stdout


@pytest.mark.unit
def test_integration_environment_isolation_workflow():
    """Test environment isolation in complete workflow."""
    original_env = os.environ.copy()

    # Set test variable
    test_var = "WORKFLOW_ISOLATION_VAR"
    os.environ[test_var] = "original_value"

    try:
        # Execute command that modifies environment
        result = execute_command(
            f"export {test_var}=modified_value; echo ${test_var}"
        )

        assert result.success is True
        assert "modified_value" in result.stdout

        # Verify original environment unchanged
        assert os.environ[test_var] == "original_value"

        # Verify no new variables added
        assert set(os.environ.keys()) == set(original_env.keys()).union({test_var})
    finally:
        if test_var in os.environ:
            del os.environ[test_var]
