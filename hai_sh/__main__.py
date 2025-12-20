"""
CLI entry point for hai.
"""

import argparse
import sys
from hai_sh import __version__, init_hai_directory


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
  Config file: ~/.hai/config.yml
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
        help="path to config file (default: ~/.hai/config.yml)"
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
        "Run 'hai --help' for configuration information or check ~/.hai/config.yml"
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
        "Check your API keys and provider configuration in ~/.hai/config.yml"
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


def main():
    """Main entry point for the hai CLI."""
    try:
        # Initialize ~/.hai/ directory structure on first run
        success, error = init_hai_directory()
        if not success and error:
            # Only show warning, don't fail - might already exist
            if "--debug" in sys.argv:
                handle_init_error(error)

        # Parse arguments
        parser = create_parser()
        args = parser.parse_args()

        # Placeholder for future functionality
        if args.query:
            print("hai v0.1 is under development.")
            print("Command execution will be available soon!")
            print(f"\nYou asked: {' '.join(args.query)}")

            # Show helpful information
            print("\nCurrent status:")
            print("  ✓ Configuration system")
            print("  ✓ Context gathering (cwd, git, env)")
            print("  ✓ LLM providers (OpenAI, Ollama)")
            print("  ✓ Command execution engine")
            print("  ✓ Shell integration (bash, zsh)")
            print("  ⧗ Main CLI integration (coming soon)")

            return 0

        # If no arguments, show help
        parser.print_help()
        return 0

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
        if "--debug" in sys.argv:
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
