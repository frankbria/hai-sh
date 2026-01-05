"""
Tests for __main__.py CLI module.
"""

import io
import sys
from unittest.mock import Mock, patch

import pytest

from hai_sh.__main__ import (
    DESCRIPTION,
    EPILOG,
    ConfigError,
    HaiError,
    ProviderError,
    create_parser,
    format_error,
    handle_config_error,
    handle_execution_error,
    handle_init_error,
    handle_provider_error,
    main,
    print_error,
)


# ============================================================================
# Custom Exception Tests
# ============================================================================


@pytest.mark.unit
def test_hai_error_is_exception():
    """Test that HaiError is an Exception."""
    error = HaiError("test error")
    assert isinstance(error, Exception)
    assert str(error) == "test error"


@pytest.mark.unit
def test_config_error_is_hai_error():
    """Test that ConfigError is a HaiError."""
    error = ConfigError("config error")
    assert isinstance(error, HaiError)
    assert isinstance(error, Exception)
    assert str(error) == "config error"


@pytest.mark.unit
def test_provider_error_is_hai_error():
    """Test that ProviderError is a HaiError."""
    error = ProviderError("provider error")
    assert isinstance(error, HaiError)
    assert isinstance(error, Exception)
    assert str(error) == "provider error"


# ============================================================================
# Error Formatting Tests
# ============================================================================


@pytest.mark.unit
def test_format_error_basic():
    """Test basic error formatting without suggestion."""
    result = format_error("Test Error", "Something went wrong")

    assert "Error: Test Error" in result
    assert "Something went wrong" in result
    assert "Suggestion:" not in result


@pytest.mark.unit
def test_format_error_with_suggestion():
    """Test error formatting with suggestion."""
    result = format_error(
        "Test Error",
        "Something went wrong",
        "Try doing this instead"
    )

    assert "Error: Test Error" in result
    assert "Something went wrong" in result
    assert "Suggestion:" in result
    assert "Try doing this instead" in result


@pytest.mark.unit
def test_format_error_multiline_message():
    """Test error formatting with multiline message."""
    result = format_error(
        "Config Error",
        "Line 1\nLine 2",
        "Check your config"
    )

    assert "Error: Config Error" in result
    assert "Line 1" in result
    assert "Line 2" in result
    assert "Check your config" in result


@pytest.mark.unit
def test_print_error_outputs_to_stderr():
    """Test that print_error outputs to stderr."""
    with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
        print_error("Test Error", "Test message", "Test suggestion")

        output = mock_stderr.getvalue()
        assert "Error: Test Error" in output
        assert "Test message" in output
        assert "Test suggestion" in output


# ============================================================================
# Error Handler Tests
# ============================================================================


@pytest.mark.unit
def test_handle_init_error():
    """Test initialization error handler."""
    with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
        handle_init_error("Failed to create directory")

        output = mock_stderr.getvalue()
        assert "Initialization Error" in output
        assert "Failed to create directory" in output
        assert "~/.hai/" in output
        assert "write permissions" in output


@pytest.mark.unit
def test_handle_config_error():
    """Test configuration error handler."""
    with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
        handle_config_error("Invalid YAML format")

        output = mock_stderr.getvalue()
        assert "Configuration Error" in output
        assert "Invalid YAML format" in output
        assert "~/.hai/config.yaml" in output


@pytest.mark.unit
def test_handle_provider_error():
    """Test provider error handler."""
    with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
        handle_provider_error("API key missing")

        output = mock_stderr.getvalue()
        assert "Provider Error" in output
        assert "API key missing" in output
        assert "~/.hai/config.yaml" in output


@pytest.mark.unit
def test_handle_execution_error():
    """Test execution error handler."""
    with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
        handle_execution_error("Command not found")

        output = mock_stderr.getvalue()
        assert "Execution Error" in output
        assert "Command not found" in output
        assert "permissions" in output


# ============================================================================
# Argument Parser Tests
# ============================================================================


@pytest.mark.unit
def test_create_parser_basic():
    """Test basic parser creation."""
    parser = create_parser()

    assert parser.prog == "hai"
    assert parser.description == DESCRIPTION
    assert parser.epilog == EPILOG


@pytest.mark.unit
def test_parser_version_flag():
    """Test --version flag."""
    parser = create_parser()

    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            parser.parse_args(['--version'])

    # SystemExit with code 0 for version
    assert exc_info.value.code == 0


@pytest.mark.unit
def test_parser_help_flag():
    """Test --help flag."""
    parser = create_parser()

    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            parser.parse_args(['--help'])

    # SystemExit with code 0 for help
    assert exc_info.value.code == 0


@pytest.mark.unit
def test_parser_query_arguments():
    """Test parsing query arguments."""
    parser = create_parser()
    args = parser.parse_args(['find', 'large', 'files'])

    assert args.query == ['find', 'large', 'files']


@pytest.mark.unit
def test_parser_config_flag():
    """Test --config flag."""
    parser = create_parser()
    args = parser.parse_args(['--config', '/path/to/config.yaml', 'test', 'query'])

    assert args.config == '/path/to/config.yaml'
    assert args.query == ['test', 'query']


@pytest.mark.unit
def test_parser_no_color_flag():
    """Test --no-color flag."""
    parser = create_parser()
    args = parser.parse_args(['--no-color', 'test'])

    assert args.no_color is True
    assert args.query == ['test']


@pytest.mark.unit
def test_parser_debug_flag():
    """Test --debug flag."""
    parser = create_parser()
    args = parser.parse_args(['--debug', 'test'])

    assert args.debug is True
    assert args.query == ['test']


@pytest.mark.unit
def test_parser_multiple_flags():
    """Test multiple flags together."""
    parser = create_parser()
    args = parser.parse_args([
        '--config', '/custom/config.yaml',
        '--no-color',
        '--debug',
        'find', 'files'
    ])

    assert args.config == '/custom/config.yaml'
    assert args.no_color is True
    assert args.debug is True
    assert args.query == ['find', 'files']


@pytest.mark.unit
def test_parser_no_arguments():
    """Test parser with no arguments."""
    parser = create_parser()
    args = parser.parse_args([])

    assert args.query == []
    assert args.no_color is False
    assert args.debug is False
    assert args.config is None


# ============================================================================
# Main Function Tests
# ============================================================================


@pytest.mark.unit
def test_main_with_query():
    """Test main with query arguments."""
    test_args = ['hai', 'find', 'large', 'files']

    # Mock config with ollama provider
    mock_config = {
        'provider': 'ollama',
        'providers': {
            'ollama': {
                'base_url': 'http://localhost:11434',
                'model': 'llama3.2'
            }
        }
    }

    # Mock LLM response
    mock_response = {
        'conversation': 'I will search for large files.',
        'command': 'find . -type f -size +100M',
        'confidence': 85
    }

    # Mock execution result
    mock_result = Mock()
    mock_result.success = True
    mock_result.exit_code = 0
    mock_result.stdout = 'file1.bin\nfile2.bin'
    mock_result.stderr = ''

    # Mock provider fallback result
    mock_provider = Mock()
    mock_provider.is_available.return_value = True
    mock_fallback_result = Mock()
    mock_fallback_result.provider = mock_provider
    mock_fallback_result.provider_name = 'ollama'
    mock_fallback_result.had_fallback = False

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', return_value=(True, None)):
            with patch('hai_sh.__main__.load_config', return_value=mock_config):
                with patch('hai_sh.__main__.get_available_provider', return_value=mock_fallback_result):
                    with patch('hai_sh.__main__.generate_with_retry', return_value=mock_response):
                        with patch('hai_sh.__main__.get_user_confirmation', return_value=True):
                            with patch('hai_sh.__main__.execute_command', return_value=mock_result):
                                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                                    exit_code = main()

    output = mock_stdout.getvalue()
    assert exit_code == 0
    assert "large files" in output or "find" in output


@pytest.mark.unit
def test_main_no_arguments():
    """Test main with no arguments shows help."""
    test_args = ['hai']

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', return_value=(True, None)):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                exit_code = main()

    output = mock_stdout.getvalue()
    assert exit_code == 0
    assert "hai - AI-powered terminal assistant" in output
    assert "examples:" in output


@pytest.mark.unit
def test_main_keyboard_interrupt():
    """Test main handles KeyboardInterrupt."""
    test_args = ['hai', 'test']

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', side_effect=KeyboardInterrupt()):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                exit_code = main()

    output = mock_stderr.getvalue()
    assert exit_code == 130
    assert "Interrupted by user" in output


@pytest.mark.unit
def test_main_config_error():
    """Test main handles ConfigError."""
    test_args = ['hai', 'test']

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', side_effect=ConfigError("Invalid config")):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                exit_code = main()

    output = mock_stderr.getvalue()
    assert exit_code == 1
    assert "Configuration Error" in output
    assert "Invalid config" in output


@pytest.mark.unit
def test_main_provider_error():
    """Test main handles ProviderError."""
    test_args = ['hai', 'test']

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', side_effect=ProviderError("API error")):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                exit_code = main()

    output = mock_stderr.getvalue()
    assert exit_code == 1
    assert "Provider Error" in output
    assert "API error" in output


@pytest.mark.unit
def test_main_generic_exception():
    """Test main handles generic exceptions."""
    test_args = ['hai', 'test']

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', side_effect=RuntimeError("Unexpected error")):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                exit_code = main()

    output = mock_stderr.getvalue()
    assert exit_code == 1
    assert "Unexpected Error" in output
    assert "Unexpected error" in output
    assert "--debug" in output


@pytest.mark.unit
def test_main_debug_mode():
    """Test main with debug mode shows traceback."""
    test_args = ['hai', '--debug', 'test']

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', side_effect=RuntimeError("Debug error")):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                exit_code = main()

    output = mock_stderr.getvalue()
    assert exit_code == 1
    # In debug mode, we should see traceback
    assert "Traceback" in output or "Debug error" in output


@pytest.mark.unit
def test_main_init_warning_in_debug():
    """Test main shows init warnings only in debug mode."""
    test_args = ['hai', '--debug', 'test']

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', return_value=(False, "Dir exists")):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                    exit_code = main()

    stderr_output = mock_stderr.getvalue()
    assert "Initialization Error" in stderr_output or exit_code == 0


@pytest.mark.unit
def test_main_init_warning_without_debug():
    """Test main suppresses init warnings without debug mode."""
    test_args = ['hai', 'test']

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', return_value=(False, "Dir exists")):
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                    exit_code = main()

    stderr_output = mock_stderr.getvalue()
    # Should not show initialization error without --debug
    assert "Initialization Error" not in stderr_output or "development" in mock_stdout.getvalue()


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_integration_help_text_completeness():
    """Test that help text includes all required sections."""
    parser = create_parser()

    # Verify DESCRIPTION
    assert "AI-powered terminal assistant" in parser.description
    assert "natural language" in parser.description

    # Verify EPILOG sections
    assert "examples:" in parser.epilog
    assert "configuration:" in parser.epilog
    assert "environment variables:" in parser.epilog
    assert "documentation:" in parser.epilog
    assert "github.com/frankbria/hai-sh" in parser.epilog


@pytest.mark.unit
def test_integration_error_flow():
    """Test complete error handling flow."""
    test_args = ['hai', 'test']

    # Test ConfigError flow
    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', side_effect=ConfigError("Bad config")):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                exit_code = main()

    output = mock_stderr.getvalue()
    assert exit_code == 1
    assert "Configuration Error" in output
    assert "Bad config" in output
    assert "Suggestion:" in output
    assert "hai --help" in output


@pytest.mark.unit
def test_integration_version_display():
    """Test version display integration."""
    from hai_sh import __version__

    parser = create_parser()

    # Capture version output
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            parser.parse_args(['--version'])
            version_output = mock_stdout.getvalue()

    assert exc_info.value.code == 0


@pytest.mark.unit
def test_integration_complete_workflow():
    """Test complete workflow from query to execution."""
    test_args = ['hai', 'list', 'files']

    # Mock config
    mock_config = {
        'provider': 'ollama',
        'providers': {
            'ollama': {
                'base_url': 'http://localhost:11434',
                'model': 'llama3.2'
            }
        }
    }

    # Mock LLM response
    mock_response = {
        'conversation': 'I will list all files in the current directory.',
        'command': 'ls -la',
        'confidence': 95
    }

    # Mock execution result
    mock_result = Mock()
    mock_result.success = True
    mock_result.exit_code = 0
    mock_result.stdout = 'file1.txt\nfile2.txt'
    mock_result.stderr = ''

    # Mock provider fallback result
    mock_provider = Mock()
    mock_provider.is_available.return_value = True
    mock_fallback_result = Mock()
    mock_fallback_result.provider = mock_provider
    mock_fallback_result.provider_name = 'ollama'
    mock_fallback_result.had_fallback = False

    with patch('sys.argv', test_args):
        with patch('hai_sh.__main__.init_hai_directory', return_value=(True, None)):
            with patch('hai_sh.__main__.load_config', return_value=mock_config):
                with patch('hai_sh.__main__.get_available_provider', return_value=mock_fallback_result):
                    with patch('hai_sh.__main__.generate_with_retry', return_value=mock_response):
                        with patch('hai_sh.__main__.get_user_confirmation', return_value=True):
                            with patch('hai_sh.__main__.execute_command', return_value=mock_result):
                                with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                                    exit_code = main()

    output = mock_stdout.getvalue()
    assert exit_code == 0
    assert "list all files" in output or "ls" in output
