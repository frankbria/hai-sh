"""
CLI entry point for hai.
"""

import argparse
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict

from hai_sh import __version__, init_hai_directory
from hai_sh.app_mode import is_app_mode, run_app_mode
from hai_sh.config import (
    load_config,
    ConfigError as ConfigLoadError,
    get_available_provider,
)
from hai_sh.context import get_cwd_context, get_git_context, get_env_context, get_file_listing_context
from hai_sh.prompt import build_system_prompt, generate_with_retry, collect_context
from hai_sh.executor import execute_command
from hai_sh import gum
from hai_sh.memory import MemoryManager
from hai_sh.output import should_use_color
from hai_sh.schema import validate_config_dict

# Module logger for debug output
_logger = logging.getLogger(__name__)


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
        "-y", "--yes",
        action="store_true",
        help="auto-execute commands without confirmation (overrides config)"
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help="always require confirmation before executing (overrides config)"
    )

    parser.add_argument(
        "--app-mode",
        action="store_true",
        help="launch interactive TUI mode"
    )

    parser.add_argument(
        "--setup",
        action="store_true",
        help="run interactive setup wizard to configure provider and API keys"
    )

    parser.add_argument(
        "--history",
        action="store_true",
        help="search and re-run commands from hai history"
    )

    parser.add_argument(
        "--provider",
        metavar="NAME",
        help="switch LLM provider for this invocation (openai, anthropic, ollama)"
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


def gather_context_parallel(user_query: str = "", config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Gather context information in parallel for faster startup.

    Args:
        user_query: User query for file relevance filtering
        config: Configuration dictionary for context settings

    Returns:
        Dict[str, Any]: Context dictionary with cwd, git, env, and file information
    """
    context: Dict[str, Any] = {}
    config = config or {}

    # Determine number of workers based on what we're collecting
    include_files = config.get('context', {}).get('include_file_listing', True)
    max_workers = 4 if include_files else 3

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_cwd_context): 'cwd',
            executor.submit(get_git_context): 'git',
            executor.submit(get_env_context): 'env',
        }

        # Add file listing if enabled
        if include_files:
            file_listing_config = config.get('context', {})
            futures[executor.submit(
                get_file_listing_context,
                max_files=file_listing_config.get('file_listing_max_files', 20),
                max_depth=file_listing_config.get('file_listing_max_depth', 1),
                show_hidden=file_listing_config.get('file_listing_show_hidden', False),
                query=user_query
            )] = 'files'

        for future in as_completed(futures):
            key = futures[future]
            try:
                context[key] = future.result()
            except Exception as e:
                # Log failure at debug level, then gracefully degrade to empty context
                _logger.debug(
                    "Context gathering failed for '%s': %s",
                    key,
                    e,
                    exc_info=True
                )
                context[key] = {}

    return context


def format_collapsed_explanation(explanation: str, use_colors: bool = True) -> str:
    """
    Format explanation as a collapsible/collapsed section.

    Args:
        explanation: The explanation text
        use_colors: Whether to use ANSI colors

    Returns:
        str: Formatted collapsed explanation
    """
    if use_colors:
        DIM = "\033[2m"
        RESET = "\033[0m"
        CYAN = "\033[36m"
    else:
        DIM = RESET = CYAN = ""

    # Truncate long explanations for collapsed view
    short_explanation = explanation[:100] + "..." if len(explanation) > 100 else explanation
    # Remove newlines for compact display
    short_explanation = short_explanation.replace("\n", " ")

    return f"{DIM}{CYAN}[Explanation: {short_explanation}]{RESET}"


def should_auto_execute(confidence: int, config: Dict[str, Any]) -> bool:
    """
    Determine if a command should be auto-executed based on confidence and config.

    Args:
        confidence: Confidence score (0-100)
        config: Configuration dictionary

    Returns:
        bool: True if command should be auto-executed
    """
    # Get execution settings with defaults
    execution = config.get('execution', {})

    # If require_confirmation is True, never auto-execute
    if execution.get('require_confirmation', False):
        return False

    # If auto_execute is disabled, don't auto-execute
    if not execution.get('auto_execute', True):
        return False

    # Check confidence threshold
    threshold = execution.get('auto_execute_threshold', 85)
    return confidence >= threshold


def get_user_confirmation(command: str) -> tuple:
    """
    Ask user to confirm, edit, or cancel command execution.

    Uses gum choose for rich interactive selection when available,
    falls back to text input otherwise.

    Args:
        command: The command to execute

    Returns:
        tuple: (action, command) where action is 'execute', 'cancel', or 'execute'
               with potentially edited command
    """
    if gum.has_gum() and gum._is_interactive():
        choice = gum.choose(
            ["Execute", "Edit", "Cancel"],
            header=f"$ {command}",
        )
        if choice == "Execute":
            return ("execute", command)
        elif choice == "Edit":
            edited = gum.input_text(
                placeholder="Edit command...",
                value=command,
                prompt_str="$ ",
            )
            if edited and edited.strip():
                return ("execute", edited.strip())
            return ("cancel", command)
        else:
            return ("cancel", command)
    else:
        # Fallback to text input
        print(f"\n{command}")
        while True:
            try:
                response = input("\nExecute this command? [y/N/e(dit)]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return ("cancel", command)
            if response in ('y', 'yes'):
                return ("execute", command)
            elif response in ('n', 'no', ''):
                return ("cancel", command)
            elif response in ('e', 'edit'):
                edited = gum.input_text(
                    placeholder="Edit command...",
                    value=command,
                    prompt_str="$ ",
                )
                if edited and edited.strip():
                    return ("execute", edited.strip())
                return ("cancel", command)
            else:
                print("Please answer 'y', 'n', or 'e'")


def run_setup_wizard() -> int:
    """
    Run interactive setup wizard for first-time configuration.

    Uses gum for rich interactive prompts when available, falls back
    to basic input() otherwise.

    Returns:
        int: Exit code (0 for success)
    """
    print(gum.styled("hai-sh Setup", bold=True, foreground="39"))
    print()

    # Provider selection
    provider = gum.choose(
        ["Ollama (local)", "OpenAI", "Anthropic"],
        header="Choose your LLM provider:",
    )
    if not provider:
        print("Setup cancelled.")
        return 0

    # Build config based on selection
    config_updates = {}

    if provider == "OpenAI":
        config_updates["provider"] = "openai"
        api_key = gum.input_text(
            placeholder="sk-...",
            password=True,
            prompt_str="OpenAI API Key: ",
        )
        if api_key:
            config_updates["openai_api_key"] = api_key
        model = gum.input_text(
            placeholder="Model name",
            value="gpt-4o-mini",
            prompt_str="Model: ",
        )
        if model:
            config_updates["openai_model"] = model

    elif provider == "Anthropic":
        config_updates["provider"] = "anthropic"
        api_key = gum.input_text(
            placeholder="sk-ant-...",
            password=True,
            prompt_str="Anthropic API Key: ",
        )
        if api_key:
            config_updates["anthropic_api_key"] = api_key
        model = gum.input_text(
            placeholder="Model name",
            value="claude-sonnet-4-5",
            prompt_str="Model: ",
        )
        if model:
            config_updates["anthropic_model"] = model

    else:  # Ollama
        config_updates["provider"] = "ollama"
        base_url = gum.input_text(
            placeholder="Ollama URL",
            value="http://localhost:11434",
            prompt_str="URL: ",
        )
        if base_url:
            config_updates["ollama_base_url"] = base_url
        model = gum.input_text(
            placeholder="Model name",
            value="llama3.2",
            prompt_str="Model: ",
        )
        if model:
            config_updates["ollama_model"] = model

    # Write config
    _write_setup_config(config_updates)
    print()
    print(gum.success(f"Configuration saved to ~/.hai/config.yaml"))

    # Offer shell integration
    print()
    if gum.confirm("Install shell integration (Ctrl+X Ctrl+H)?"):
        from hai_sh.install_shell import install_shell_integration
        install_shell_integration()
    else:
        print("Skipped shell integration. Run 'hai-install-shell' later to install.")

    print()
    print(gum.success("Setup complete! Try: hai show disk usage"))
    return 0


def _write_setup_config(updates: dict) -> None:
    """Write setup wizard selections to config.yaml."""
    from hai_sh.init import get_config_path, init_hai_directory

    # Ensure directory exists
    init_hai_directory()

    config_path = get_config_path()

    provider = updates.get("provider", "ollama")

    lines = [
        "# hai-sh configuration file",
        "# Generated by hai --setup",
        "",
        f'provider: "{provider}"',
        "",
        "providers:",
        "  openai:",
    ]

    if updates.get("openai_api_key"):
        lines.append(f'    api_key: "{updates["openai_api_key"]}"')
    else:
        lines.append('    # api_key: "sk-..."')
    lines.append(f'    model: "{updates.get("openai_model", "gpt-4o-mini")}"')

    lines.extend([
        "",
        "  anthropic:",
    ])
    if updates.get("anthropic_api_key"):
        lines.append(f'    api_key: "{updates["anthropic_api_key"]}"')
    else:
        lines.append('    # api_key: "sk-ant-..."')
    lines.append(f'    model: "{updates.get("anthropic_model", "claude-sonnet-4-5")}"')

    lines.extend([
        "",
        "  ollama:",
        f'    base_url: "{updates.get("ollama_base_url", "http://localhost:11434")}"',
        f'    model: "{updates.get("ollama_model", "llama3.2")}"',
        "",
        "context:",
        "  include_history: true",
        "  history_length: 10",
        "  include_env_vars: true",
        "  include_git_state: true",
        "",
        "output:",
        "  show_conversation: true",
        "  show_reasoning: true",
        "  use_colors: true",
    ])

    config_path.write_text("\n".join(lines) + "\n")
    import stat
    config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def run_history_search() -> int:
    """
    Search and display commands from hai history.

    Uses gum filter for fuzzy search when available.

    Returns:
        int: Exit code
    """
    from hai_sh.init import get_hai_dir
    import json

    history_dir = get_hai_dir() / "logs"
    if not history_dir.exists():
        print("No history found. Run some hai commands first!")
        return 0

    # Collect history entries from memory files
    commands = []
    memory_file = get_hai_dir() / "memory.json"
    if memory_file.exists():
        try:
            data = json.loads(memory_file.read_text())
            for entry in data.get("interactions", []):
                cmd = entry.get("command", "")
                if cmd:
                    commands.append(cmd)
        except (json.JSONDecodeError, KeyError):
            pass

    if not commands:
        print("No command history found yet.")
        return 0

    # Deduplicate while preserving order (most recent first)
    seen = set()
    unique_commands = []
    for cmd in reversed(commands):
        if cmd not in seen:
            seen.add(cmd)
            unique_commands.append(cmd)

    selected = gum.filter_list(unique_commands, placeholder="Search history...")
    if selected:
        print(f"\nSelected: {selected}")
        if gum.confirm("Execute this command?"):
            result = execute_command(selected)
            if result.success and result.stdout:
                print(result.stdout)
            elif not result.success:
                print(f"Command failed with exit code {result.exit_code}", file=sys.stderr)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
            return 0 if result.success else result.exit_code
    return 0


# Patterns that indicate a command could be destructive
DANGEROUS_COMMAND_PATTERNS = [
    "rm ",
    "rm -",
    "rmdir ",
    "mkfs",
    "dd if=",
    "chmod 777",
    "chmod -r",
    "chown -r",
    "> /dev/",
    "kill -9",
    "pkill",
    "reboot",
    "shutdown",
    "halt",
    "poweroff",
    "drop table",
    "drop database",
    "truncate ",
    "format ",
]


def is_dangerous_command(command: str) -> bool:
    """Check if a command matches known dangerous patterns."""
    cmd_lower = command.lower()
    return any(pattern in cmd_lower for pattern in DANGEROUS_COMMAND_PATTERNS)


def print_output(text: str) -> None:
    """
    Print command output, using gum pager for long content.

    Uses pager when output exceeds terminal height and gum is available.
    Always prints directly when output is short or gum is unavailable.
    """
    if not text:
        return

    line_count = text.count("\n") + 1
    try:
        terminal_height = os.get_terminal_size().lines
    except (OSError, ValueError):
        terminal_height = 40  # Reasonable default

    if line_count > terminal_height and gum.has_gum() and gum._is_interactive():
        gum.page(text)
    else:
        print(text)


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

        # Handle --setup wizard
        if args.setup:
            return run_setup_wizard()

        # Handle --history search
        if args.history:
            return run_history_search()

        # If no query provided, show help
        if not args.query:
            parser.print_help()
            return 0

        # Join query into single string
        user_query = ' '.join(args.query)

        # Set NO_COLOR environment variable if --no-color flag is set
        if args.no_color:
            os.environ['NO_COLOR'] = '1'

        # Check if app mode should be used (--app-mode flag or HAI_APP_MODE env var)
        if is_app_mode(args.app_mode):
            # Load and validate config for app mode
            config_path = Path(args.config) if args.config else None
            try:
                config_dict = load_config(config_path=config_path, use_pydantic=False)
                validated_config, _warnings = validate_config_dict(config_dict)
                return run_app_mode(validated_config, user_query)
            except ConfigLoadError as e:
                handle_config_error(str(e))
                return 1
            except Exception as e:
                handle_config_error(str(e))
                return 1

        # Load configuration for standard mode
        config_path = Path(args.config) if args.config else None
        try:
            config = load_config(config_path=config_path, use_pydantic=False)
        except ConfigLoadError as e:
            handle_config_error(str(e))
            return 1

        # Override provider if --provider flag is set
        if args.provider:
            config['provider'] = args.provider

        # Initialize memory manager
        memory_manager = MemoryManager(config)
        memory_manager.load_all()

        # Collect context using smart context injection
        # This includes memory, shell history, enhanced git, and relevance filtering
        context = collect_context(
            config=config,
            query=user_query,
            memory_manager=memory_manager
        )

        # Build system prompt with context
        system_prompt = build_system_prompt(context)

        # Determine color settings for status messages
        use_colors = should_use_color() and not args.no_color
        if use_colors:
            WARN = "\033[93m"  # Yellow
            SUCCESS = "\033[92m"  # Green
            RESET = "\033[0m"
        else:
            WARN = SUCCESS = RESET = ""

        # Define fallback callback for user feedback
        def handle_fallback(failed_provider: str, error: str, next_provider: str):
            """Print fallback message when switching providers."""
            # Truncate error message if too long
            short_error = error[:50] + "..." if len(error) > 50 else error
            print(
                f"{WARN}Provider '{failed_provider}' unavailable ({short_error}), "
                f"trying '{next_provider}'...{RESET}",
                file=sys.stderr
            )

        # Get LLM provider using fallback chain
        try:
            result = get_available_provider(
                config,
                debug_mode=debug_mode,
                on_fallback=handle_fallback
            )
            provider = result.provider
            provider_name = result.provider_name

            # Report successful provider selection if fallback occurred
            if result.had_fallback:
                print(
                    f"{SUCCESS}Using provider '{provider_name}'{RESET}",
                    file=sys.stderr
                )

        except ConfigLoadError as e:
            handle_provider_error(str(e))
            return 1

        # Generate command using LLM
        if debug_mode:
            print(f"Debug: Using {provider_name} provider", file=sys.stderr)
            print(f"Debug: Query: {user_query}", file=sys.stderr)
            print(f"Debug: System prompt: {system_prompt[:100]}...", file=sys.stderr)

        try:
            # Generate with retry - show spinner during LLM processing
            response = gum.spin(
                "hai is thinking...",
                generate_with_retry,
                provider=provider,
                prompt=user_query,
                context=context,
                max_retries=3,
                system_prompt=system_prompt,
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

        # Command Mode: Execute-first display with optional auto-execute
        # Get execution settings
        show_explanation_mode = config.get('execution', {}).get('show_explanation', 'collapsed')

        # Determine if we should auto-execute
        # CLI flags override config: --yes forces auto-execute, --confirm forces confirmation
        if args.yes:
            auto_exec = True
        elif args.confirm:
            auto_exec = False
        else:
            auto_exec = should_auto_execute(confidence, config)

        # Check for dangerous commands — override auto-execute to require confirmation
        if auto_exec and is_dangerous_command(command):
            print(f"\n{gum.warn('This command may modify or delete data')}")
            auto_exec = False  # Force confirmation for dangerous commands

        if auto_exec:
            # Auto-execute: Show command, execute immediately, then show collapsed explanation
            print(f"\n{BOLD}${RESET} {GREEN}{command}{RESET}")
            result = execute_command(command)

            # Display result (use pager for long output)
            if result.success:
                if result.stdout:
                    print_output(result.stdout)
            else:
                print(f"{RED}Command failed with exit code {result.exit_code}{RESET}")
                if result.stderr:
                    print(f"{RED}Error: {result.stderr}{RESET}")

            # Update memory with interaction
            memory_manager.update_memory(
                query=user_query,
                command=command,
                result=result.stdout if result.success else result.stderr,
                success=result.success
            )
            memory_manager.save_all()

            # Show explanation based on config
            if show_explanation_mode == 'expanded':
                print(f"\n{BOLD}Explanation:{RESET} {explanation}")
                print(f"{BOLD}Confidence:{RESET} {conf_color}{confidence}%{RESET}")
            elif show_explanation_mode == 'collapsed':
                collapsed = format_collapsed_explanation(explanation, use_colors)
                print(f"\n{collapsed} {conf_color}({confidence}%){RESET}")
            # 'hidden' mode: don't show explanation at all

            return 0 if result.success else result.exit_code

        else:
            # Manual confirmation required: Show explanation first, then ask
            # Use gum styled output for explanation when available
            styled_explanation = gum.styled(
                explanation,
                border="rounded",
                border_foreground="39",
                padding="0 1",
            )
            print(f"\n{styled_explanation}")
            print(f"\n{BOLD}Command:{RESET} {GREEN}{command}{RESET}")
            print(f"{BOLD}Confidence:{RESET} {conf_color}{confidence}%{RESET}")

            action, final_command = get_user_confirmation(command)
            if action == "cancel":
                print("\nCommand execution cancelled")
                return 0

            # Execute command (may have been edited)
            print("\nExecuting...\n")
            result = execute_command(final_command)

            # Display result (use pager for long output)
            if result.success:
                if result.stdout:
                    print_output(result.stdout)
            else:
                print(f"{RED}Command failed with exit code {result.exit_code}{RESET}")
                if result.stderr:
                    print(f"{RED}Error: {result.stderr}{RESET}")

            # Update memory with interaction
            memory_manager.update_memory(
                query=user_query,
                command=final_command,
                result=result.stdout if result.success else result.stderr,
                success=result.success
            )
            memory_manager.save_all()

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
