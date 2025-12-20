"""
System prompt and response formatting for hai-sh.

This module provides the system prompt template that instructs LLMs
to generate bash commands in a structured JSON format.
"""

import json
from typing import Any, Optional


# System prompt template
SYSTEM_PROMPT_TEMPLATE = """You are hai, a helpful terminal assistant that generates bash commands based on natural language requests.

## Your Role
You help users execute terminal commands by understanding their intent and generating safe, effective bash commands.

## Response Format
You MUST respond with valid JSON in this exact format:
{
    "explanation": "Brief explanation of what the command does",
    "command": "the actual bash command to execute",
    "confidence": 85
}

- explanation: 1-2 sentences explaining the command's purpose
- command: Valid bash command (single line or using && for multiple steps)
- confidence: Integer 0-100 indicating how confident you are this command is correct

## Context
{context}

## Safety Guidelines (v0.1)
DO NOT generate commands that:
- Delete files or directories (rm, rmdir)
- Modify system files (/etc, /sys, /boot)
- Change permissions on system directories
- Kill system processes
- Format drives or partitions
- Modify network settings
- Install/uninstall software without explicit request

DO generate commands that:
- List, search, and view files (ls, find, grep, cat, less)
- Navigate directories (cd, pwd)
- Show system information (df, du, ps, top)
- Work with git (status, diff, log, add, commit, push)
- Process text (awk, sed, cut, sort, uniq)
- Create/edit files in user space
- Run tests and builds

## Examples

User: "show me large files in my home directory"
Response:
{
    "explanation": "I'll search for files larger than 100MB in your home directory and sort by size.",
    "command": "find ~ -type f -size +100M -exec du -h {} + | sort -rh | head -20",
    "confidence": 90
}

User: "what changed in the last commit?"
Response:
{
    "explanation": "I'll show the diff for the most recent commit.",
    "command": "git show HEAD",
    "confidence": 95
}

User: "list python files modified today"
Response:
{
    "explanation": "I'll find all .py files modified in the last 24 hours.",
    "command": "find . -name '*.py' -mtime -1 -type f",
    "confidence": 90
}

## Important
- Always respond with valid JSON
- Keep explanations concise
- Use standard bash commands
- Prefer simple, readable commands
- Only use one command unless multiple steps are clearly needed"""


# Context template for variable substitution
CONTEXT_TEMPLATE = """Current directory: {cwd}
{git_context}
{env_context}"""


def build_system_prompt(context: Optional[dict[str, Any]] = None) -> str:
    """
    Build the system prompt with optional context injection.

    Args:
        context: Optional context dictionary with:
            - cwd: Current working directory
            - git: Git repository information
            - env: Environment variables

    Returns:
        str: Complete system prompt with context

    Example:
        >>> context = {"cwd": "/home/user/project"}
        >>> prompt = build_system_prompt(context)
        >>> "Current directory:" in prompt
        True
    """
    if not context:
        # No context - use minimal placeholder
        context_str = "No specific context provided."
    else:
        context_str = _format_context(context)

    return SYSTEM_PROMPT_TEMPLATE.replace("{context}", context_str)


def _format_context(context: dict[str, Any]) -> str:
    """
    Format context dictionary into human-readable string.

    Args:
        context: Context dictionary

    Returns:
        str: Formatted context string
    """
    parts = []

    # Current directory
    if "cwd" in context:
        parts.append(f"Current directory: {context['cwd']}")

    # Git context
    if "git" in context and context["git"].get("is_repo"):
        git_info = context["git"]
        git_parts = [f"Git branch: {git_info.get('branch', 'unknown')}"]

        if git_info.get("has_changes"):
            git_parts.append("Uncommitted changes present")

        if git_info.get("staged_files"):
            git_parts.append(f"Staged files: {len(git_info['staged_files'])}")

        if git_info.get("unstaged_files"):
            git_parts.append(f"Unstaged files: {len(git_info['unstaged_files'])}")

        parts.append(", ".join(git_parts))

    # Environment context
    if "env" in context:
        env_info = context["env"]
        env_parts = []

        if "user" in env_info:
            env_parts.append(f"User: {env_info['user']}")

        if "shell" in env_info:
            env_parts.append(f"Shell: {env_info['shell']}")

        if env_parts:
            parts.append(", ".join(env_parts))

    return "\n".join(parts) if parts else "No specific context provided."


def parse_response(response: str) -> dict[str, Any]:
    """
    Parse LLM JSON response into structured format.

    Args:
        response: Raw LLM response (should be JSON)

    Returns:
        dict: Parsed response with explanation, command, confidence

    Raises:
        ValueError: If response is not valid JSON or missing required fields

    Example:
        >>> response = '{"explanation": "test", "command": "ls", "confidence": 90}'
        >>> parsed = parse_response(response)
        >>> parsed["command"]
        'ls'
    """
    try:
        # Try to parse as JSON
        data = json.loads(response.strip())
    except json.JSONDecodeError as e:
        # Try to extract JSON from markdown code blocks
        if "```json" in response or "```" in response:
            # Extract JSON from code block
            lines = response.split("\n")
            json_lines = []
            in_block = False

            for line in lines:
                if line.strip().startswith("```"):
                    if in_block:
                        break
                    in_block = True
                    continue
                if in_block:
                    json_lines.append(line)

            if json_lines:
                try:
                    data = json.loads("\n".join(json_lines))
                except json.JSONDecodeError:
                    raise ValueError(f"Invalid JSON in response: {e}")
            else:
                raise ValueError(f"Could not extract JSON from response: {e}")
        else:
            raise ValueError(f"Response is not valid JSON: {e}")

    # Validate required fields
    required_fields = ["explanation", "command", "confidence"]
    missing = [field for field in required_fields if field not in data]

    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    # Validate types
    if not isinstance(data["explanation"], str):
        raise ValueError("'explanation' must be a string")

    if not isinstance(data["command"], str):
        raise ValueError("'command' must be a string")

    if not isinstance(data["confidence"], (int, float)):
        raise ValueError("'confidence' must be a number")

    # Validate confidence range
    confidence = int(data["confidence"])
    if confidence < 0 or confidence > 100:
        raise ValueError("'confidence' must be between 0 and 100")

    # Return normalized response
    return {
        "explanation": data["explanation"].strip(),
        "command": data["command"].strip(),
        "confidence": confidence
    }


def validate_command(command: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a command is safe to execute (v0.1 safety rules).

    Args:
        command: Bash command to validate

    Returns:
        tuple: (is_safe, error_message)
            - is_safe: True if command passes safety checks
            - error_message: None if safe, otherwise explanation of why it's unsafe

    Example:
        >>> validate_command("ls -la")
        (True, None)
        >>> validate_command("rm -rf /")
        (False, "Command contains dangerous operation: rm")
    """
    command_lower = command.lower()

    # Dangerous commands
    dangerous_patterns = [
        ("rm ", "rm"),
        ("rmdir ", "rmdir"),
        ("mkfs", "mkfs"),
        ("dd ", "dd"),
        ("fdisk", "fdisk"),
        ("> /dev/", "writing to device files"),
        ("chmod 777", "overly permissive chmod"),
        ("chmod -r", "recursive chmod on system paths"),
        ("chown -r", "recursive chown on system paths"),
        ("kill -9 1", "killing init process"),
        ("pkill -9", "force killing processes"),
        ("reboot", "reboot"),
        ("shutdown", "shutdown"),
        ("halt", "halt"),
        ("poweroff", "poweroff"),
        ("passwd", "passwd"),
        ("useradd", "useradd"),
        ("userdel", "userdel"),
        ("groupadd", "groupadd"),
        ("systemctl", "systemctl"),
    ]

    for pattern, description in dangerous_patterns:
        if pattern in command_lower:
            return False, f"Command contains dangerous operation: {description}"

    # Check for system path modifications
    system_paths = ["/etc/", "/sys/", "/boot/", "/dev/", "/proc/"]
    for path in system_paths:
        if path in command and (">" in command or "rm" in command_lower):
            return False, f"Command attempts to modify system path: {path}"

    # Check for suspicious redirects
    if "> /etc/" in command or ">> /etc/" in command:
        return False, "Command attempts to write to /etc/"

    return True, None


def format_command_output(
    explanation: str,
    command: str,
    confidence: int,
    use_colors: bool = True
) -> str:
    """
    Format command output for display to user.

    Args:
        explanation: Command explanation
        command: Bash command
        confidence: Confidence score (0-100)
        use_colors: Whether to use ANSI colors

    Returns:
        str: Formatted output for terminal display

    Example:
        >>> output = format_command_output("List files", "ls -la", 90, use_colors=False)
        >>> "Explanation:" in output
        True
    """
    if use_colors:
        # ANSI color codes
        BOLD = "\033[1m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        RESET = "\033[0m"
    else:
        BOLD = GREEN = YELLOW = RED = RESET = ""

    # Determine confidence color
    if confidence >= 80:
        conf_color = GREEN
    elif confidence >= 60:
        conf_color = YELLOW
    else:
        conf_color = RED

    output = []
    output.append(f"\n{BOLD}Explanation:{RESET} {explanation}")
    output.append(f"{BOLD}Command:{RESET} {GREEN}{command}{RESET}")
    output.append(f"{BOLD}Confidence:{RESET} {conf_color}{confidence}%{RESET}\n")

    return "\n".join(output)
