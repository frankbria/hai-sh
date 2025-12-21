"""
CLI entry point for hai.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from hai_sh import __version__, init_hai_directory
from hai_sh.config import load_config, ConfigError as ConfigLoadError
from hai_sh.context import get_cwd_context, get_git_context, get_env_context
from hai_sh.providers import get_provider
from hai_sh.prompt import build_system_prompt, generate_with_retry, parse_response
from hai_sh.executor import execute_command, ExecutionResult
from hai_sh.formatter import format_dual_layer
from hai_sh.output import should_use_color


# Help text and examples
DESCRIPTION = """
hai - AI-powered terminal assistant

Generate bash commands from natural language descriptions.
hai uses LLMs to translate your intentions into executable commands.
"""

EPILOG = """
examples:
  # Basic usage
  hai find large files in home directory
  hai show disk usage sorted by size
  hai compress all pdfs in current folder

  # With @hai prefix (optional)
  @hai list running docker containers
  @hai search for python files modified today

  # Get help
  hai --help
  hai --version

configuration:
  Config file: ~/.hai/config.yaml
  Shell integration: ~/.hai/bash_integration.sh
                    ~/.hai/zsh_integration.sh

environment variables:
  NO_COLOR         Disable colored output
  FORCE_COLOR      Enable colors even in non-TTY
  HAI_CONFIG       Custom config file path

documentation:
  GitHub:  https://github.com/frankbria/hai-sh
  Issues:  https://github.com/frankbria/hai-sh/issues

For more information and detailed documentation, visit the GitHub repository.
"""


class HaiError(Exception):
    """Base exception for hai errors."""
    pass


class ConfigError(HaiError):
    """Configuration error."""
    pass


class ProviderError(HaiError):
    """LLM provider error."""
    pass


def format_error(error_type: str, message: str, suggestion: str = None) -> str:
    """
    Format error message with optional suggestion.

    Args:
        error_type: Type of error (e.g., "Config Error", "API Error")
        message: Error message
        suggestion: Optional suggestion for fixing

    Returns:
        str: Formatted error message
    """
    lines = [
        f"Error: {error_type}",
        f"  {message}"
    ]

    if suggestion:
        lines.extend([
            "",
            "Suggestion:",
            f"  {suggestion}"
        ])

    return "\n".join(lines)


def print_error(error_type: str, message: str, suggestion: str = None):
    """Print formatted error to stderr."""
    error_msg = format_error(error_type, message, suggestion)
    print(error_msg, file=sys.stderr)


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser
    """
    parser = argparse.ArgumentParser(
        prog="hai",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"hai version {__version__}"
    )

    parser.add_argument(
        "--config",
        metavar="FILE",
        help="path to config file (default: ~/.hai/config.yaml)"
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable colored output"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable debug output"
    )

    parser.add_argument(
        "--suggest-only",
        action="store_true",
        help="generate command suggestion without executing (returns JSON for shell integration)"
    )

    parser.add_argument(
        "query",
        nargs="*",
        help="natural language command description"
    )

    return parser


def handle_init_error(error: str):
    """
    Handle initialization errors.

    Args:
        error: Error message from initialization
    """
    print_error(
        "Initialization Error",
        f"Failed to initialize hai directory: {error}",
        "Check that ~/.hai/ is accessible and you have write permissions."
    )


def handle_config_error(error: str):
    """
    Handle configuration errors.

    Args:
        error: Error message
    """
    print_error(
        "Configuration Error",
        error,
        "Run 'hai --help' for configuration information or check ~/.hai/config.yaml"
    )


def handle_provider_error(error: str):
    """
    Handle LLM provider errors.

    Args:
        error: Error message
    """
    print_error(
        "Provider Error",
        error,
        "Check your API keys and provider configuration in ~/.hai/config.yaml"
    )


def handle_execution_error(error: str):
    """
    Handle command execution errors.

    Args:
        error: Error message
    """
    print_error(
        "Execution Error",
        error,
        "Verify the command is valid and you have necessary permissions."
    )


def get_user_confirmation(command: str) -> bool:
    """
    Ask user to confirm command execution.

    Args:
        command: The command to execute

    Returns:
        bool: True if user confirms, False otherwise
    """
    print(f"\n{command}")
    while True:
        response = input("\nExecute this command? [y/N/e(dit)]: ").strip().lower()
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no', ''):
            return False
        elif response in ('e', 'edit'):
            print("Command editing not implemented in v0.1")
            print("Copy and paste the command to edit it manually.")
            return False
        else:
            print("Please answer 'y', 'n', or 'e'")


def main():
    """Main entry point for the hai CLI."""
    debug_mode = "--debug" in sys.argv

    try:
        # Initialize ~/.hai/ directory structure on first run
        success, error = init_hai_directory()
        if not success and error:
            # Only show warning, don't fail - might already exist
            if debug_mode:
                handle_init_error(error)

        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()

        # If no query provided, show help
        if not args.query:
            parser.print_help()
            return 0

        # Join query into single string
        user_query = ' '.join(args.query)

        # Set NO_COLOR environment variable if --no-color flag is set
        if args.no_color:
            os.environ['NO_COLOR'] = '1'

        # Load configuration
        config_path = Path(args.config) if args.config else None
        try:
            config = load_config(config_path=config_path, use_pydantic=False)
        except ConfigLoadError as e:
            handle_config_error(str(e))
            return 1

        # Gather context
        context = {
            'cwd': get_cwd_context(),
            'git': get_git_context(),
            'env': get_env_context()
        }

        # Build system prompt with context
        system_prompt = build_system_prompt(context)

        # Get LLM provider
        provider_name = config.get('provider', 'ollama')
        provider_config = config.get('providers', {}).get(provider_name, {})

        try:
            provider = get_provider(provider_name, provider_config)
        except Exception as e:
            handle_provider_error(f"Failed to initialize {provider_name} provider: {e}")
            return 1

        # Check if provider is available
        if not provider.is_available():
            handle_provider_error(
                f"{provider_name} provider is not available. "
                f"Check your configuration and API keys."
            )
            return 1

        # Generate command using LLM
        if debug_mode:
            print(f"Debug: Using {provider_name} provider", file=sys.stderr)
            print(f"Debug: Query: {user_query}", file=sys.stderr)

        try:
            # Combine system prompt and user query
            full_prompt = f"{system_prompt}\n\nUser request: {user_query}"

            # Generate with retry
            response = generate_with_retry(
                provider=provider,
                prompt=full_prompt,
                context=context,
                max_retries=3
            )

        except Exception as e:
            handle_provider_error(f"Failed to generate command: {e}")
            return 1

        # Extract fields from response
        explanation = response.get('explanation', 'No explanation provided')
        command = response.get('command', '')  # May be empty for question mode
        confidence = response.get('confidence', 0)

        # Handle --suggest-only mode (for shell integration)
        if args.suggest_only:
            import json
            output = {
                "conversation": explanation,
                "command": command,
                "confidence": confidence
            }
            print(json.dumps(output))
            return 0

        # Determine color settings
        use_colors = should_use_color()
        if use_colors:
            GREEN = "\033[92m"
            YELLOW = "\033[93m"
            RED = "\033[91m"
            RESET = "\033[0m"
            BOLD = "\033[1m"
        else:
            GREEN = YELLOW = RED = RESET = BOLD = ""

        # Color code confidence
        if confidence >= 80:
            conf_color = GREEN
        elif confidence >= 60:
            conf_color = YELLOW
        else:
            conf_color = RED

        # Check if this is question mode (no command) or command mode
        if not command:
            # Question Mode: Display explanation without command execution
            print(f"\n{explanation}")
            print(f"\n{BOLD}Confidence:{RESET} {conf_color}{confidence}%{RESET}")
            return 0

        # Command Mode: Display explanation, show command, ask for confirmation, execute
        print(f"\n{explanation}")

        # Show command and confidence
        print(f"\n{BOLD}Command:{RESET} {GREEN}{command}{RESET}")
        print(f"{BOLD}Confidence:{RESET} {conf_color}{confidence}%{RESET}")

        # Ask for user confirmation
        if not get_user_confirmation(command):
            print("\nCommand execution cancelled")
            return 0

        # Execute command
        print("\nExecuting...\n")
        result = execute_command(command)

        # Display result
        if result.success:
            if result.stdout:
                print(result.stdout)
        else:
            print(f"{RED}Command failed with exit code {result.exit_code}{RESET}")
            if result.stderr:
                print(f"{RED}Error: {result.stderr}{RESET}")

        # Return appropriate exit code
        return 0 if result.success else result.exit_code

    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130  # Standard exit code for Ctrl+C

    except ConfigError as e:
        handle_config_error(str(e))
        return 1

    except ProviderError as e:
        handle_provider_error(str(e))
        return 1

    except Exception as e:
        if debug_mode:
            # Show full traceback in debug mode
            import traceback
            traceback.print_exc()
        else:
            print_error(
                "Unexpected Error",
                str(e),
                "Run with --debug for more information."
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
