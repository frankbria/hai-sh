"""
System prompt and response formatting for hai-sh.

This module provides the system prompt template that instructs LLMs
to generate bash commands in a structured JSON format.

Also includes smart context injection with:
- Multi-source context collection (cwd, git, env, files, memory, history)
- Relevance-based filtering
- Token budgeting
"""

import json
import os
import re
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from hai_sh.memory import MemoryManager


# System prompt template
SYSTEM_PROMPT_TEMPLATE = """You are hai, a helpful terminal assistant that helps users with terminal commands and answers their questions.

## Your Role
You have two modes of operation:
1. **Command Mode**: Generate bash commands when users request actions
2. **Question Mode**: Answer informational questions without generating commands

## Response Format
You MUST respond with valid JSON in one of these formats:

**Command Mode** (when user requests an action):
{
    "explanation": "Brief explanation of what the command does",
    "command": "the actual bash command to execute",
    "confidence": 85
}

**Question Mode** (when user asks a question):
{
    "explanation": "Detailed answer to the user's question",
    "confidence": 95
}

### Field Descriptions
- explanation: 1-3 sentences (command purpose OR answer to question)
- command: Valid bash command (ONLY include if user requests an action)
- confidence: Integer 0-100 indicating confidence in your response

### Detecting Questions vs Commands
**Questions typically contain**: "what", "why", "how", "difference between", "explain", "tell me about", "which should I", "when to use"
**Commands typically contain**: "show", "find", "list", "create", "delete", "search", action verbs

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

### Command Mode Examples

User: "show me large files in my home directory"
Response:
{
    "explanation": "I'll search for files larger than 100MB in your home directory and sort by size.",
    "command": "find ~ -type f -size +100M -exec du -h {} + | sort -rh | head -20",
    "confidence": 90
}

User: "list python files modified today"
Response:
{
    "explanation": "I'll find all .py files modified in the last 24 hours.",
    "command": "find . -name '*.py' -mtime -1 -type f",
    "confidence": 90
}

### Question Mode Examples

User: "What's the difference between ls -la and ls -lah?"
Response:
{
    "explanation": "Both commands list all files including hidden ones (-a) in long format (-l). The only difference is the -h flag in 'ls -lah', which displays file sizes in human-readable format (KB, MB, GB) instead of bytes. For example, instead of 1048576, it shows 1.0M.",
    "confidence": 95
}

User: "How do I use git rebase?"
Response:
{
    "explanation": "Git rebase moves or combines commits from one branch onto another. Use 'git rebase <branch>' to rebase current branch onto <branch>, or 'git rebase -i HEAD~N' for interactive rebase of last N commits. It's useful for cleaning up commit history before merging, but avoid rebasing commits that have been pushed to shared branches.",
    "confidence": 90
}

User: "Why would I use grep instead of awk?"
Response:
{
    "explanation": "Use grep for simple pattern matching and filtering lines. Use awk for complex text processing that requires field extraction, arithmetic, or conditional logic. Grep is faster and simpler for basic searches, while awk is more powerful for data manipulation and formatted output.",
    "confidence": 95
}

## Important
- Always respond with valid JSON
- Include "command" field ONLY when user requests an action
- Omit "command" field when answering informational questions
- Keep explanations concise (1-3 sentences)
- For commands: Use standard bash, prefer simple readable commands
- For questions: Provide clear, helpful answers"""


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
    if "git" in context:
        git_info = context["git"]
        # Check for pre-formatted git context from collect_context
        if isinstance(git_info, dict) and "formatted" in git_info:
            parts.append(git_info["formatted"])
        elif isinstance(git_info, dict) and git_info.get("is_repo"):
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
        # Check for pre-formatted env context
        if isinstance(env_info, dict) and "formatted" in env_info:
            parts.append(env_info["formatted"])
        elif isinstance(env_info, dict):
            env_parts = []

            if "user" in env_info:
                env_parts.append(f"User: {env_info['user']}")

            if "shell" in env_info:
                env_parts.append(f"Shell: {env_info['shell']}")

            if env_parts:
                parts.append(", ".join(env_parts))

    # File listing context
    if "files" in context:
        files_info = context["files"]
        # Check for pre-formatted files context
        if isinstance(files_info, dict) and "formatted" in files_info:
            parts.append(files_info["formatted"])
        else:
            from hai_sh.context import format_file_listing_context
            file_listing = format_file_listing_context(files_info)
            if file_listing:
                parts.append(file_listing)

    # Shell history context (NEW)
    if "shell_history" in context:
        parts.append(context["shell_history"])

    # Session memory context (NEW)
    if "memory_session" in context:
        parts.append(context["memory_session"])

    # Directory memory context (NEW)
    if "memory_dir" in context:
        parts.append(context["memory_dir"])

    return "\n".join(parts) if parts else "No specific context provided."


def parse_response(response: str) -> dict[str, Any]:
    """
    Parse LLM JSON response into structured format.

    Supports both command mode (with command field) and question mode (without command field).

    Args:
        response: Raw LLM response (should be JSON)

    Returns:
        dict: Parsed response with explanation, confidence, and optionally command

    Raises:
        ValueError: If response is not valid JSON or missing required fields

    Examples:
        >>> # Command mode
        >>> response = '{"explanation": "test", "command": "ls", "confidence": 90}'
        >>> parsed = parse_response(response)
        >>> parsed["command"]
        'ls'

        >>> # Question mode
        >>> response = '{"explanation": "answer here", "confidence": 95}'
        >>> parsed = parse_response(response)
        >>> "command" in parsed
        False
    """
    # Check for empty response first
    if not response or not response.strip():
        raise ValueError("LLM returned empty response")

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

    # Validate required fields (command is now optional)
    required_fields = ["explanation", "confidence"]
    missing = [field for field in required_fields if field not in data]

    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    # Validate explanation
    if not isinstance(data["explanation"], str):
        raise ValueError("'explanation' must be a string")

    # Validate command if present
    if "command" in data and not isinstance(data["command"], str):
        raise ValueError("'command' must be a string")

    # Validate confidence
    if not isinstance(data["confidence"], (int, float)):
        raise ValueError("'confidence' must be a number")

    # Validate confidence range
    confidence = int(data["confidence"])
    if confidence < 0 or confidence > 100:
        raise ValueError("'confidence' must be between 0 and 100")

    # Build response
    result = {
        "explanation": data["explanation"].strip(),
        "confidence": confidence
    }

    # Add command if present
    if "command" in data:
        result["command"] = data["command"].strip()

    return result


def validate_command(command: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a command is safe to execute (v0.1 enhanced security).

    Uses multi-layer validation:
    1. Command injection pattern detection
    2. Allow-list of safe commands
    3. Dangerous operation blacklist (legacy, defense-in-depth)

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
        >>> validate_command("ls; curl attacker.com")
        (False, "Command injection detected: command chaining with semicolon")
    """
    if not command or not isinstance(command, str):
        return False, "Command must be a non-empty string"

    command_stripped = command.strip()
    if not command_stripped:
        return False, "Command is empty"

    # LAYER 1: Detect command injection patterns
    injection_check = _detect_command_injection(command)
    if not injection_check[0]:
        return injection_check

    # LAYER 2: Allow-list validation (primary security control)
    allowlist_check = _validate_command_allowlist(command_stripped)
    if not allowlist_check[0]:
        return allowlist_check

    # LAYER 3: Dangerous pattern blacklist (defense-in-depth)
    blacklist_check = _validate_command_blacklist(command.lower())
    if not blacklist_check[0]:
        return blacklist_check

    return True, None


def _detect_command_injection(command: str) -> tuple[bool, Optional[str]]:
    """
    Detect command injection patterns in the command string.

    Args:
        command: Command to check for injection attempts

    Returns:
        tuple: (is_safe, error_message)
    """
    # Command injection patterns
    injection_patterns = [
        (";", "command chaining with semicolon"),
        ("&&", "command chaining with AND operator"),
        ("||", "command chaining with OR operator"),
        ("$(" , "command substitution with $(...)"),
        ("`", "command substitution with backticks"),
        ("wget ", "network download (wget)"),
        ("curl http", "network request (curl http)"),
        ("curl -", "network request with curl flags"),
        ("nc ", "netcat network tool"),
        ("ncat ", "netcat network tool"),
        ("bash -c", "nested bash execution"),
        ("sh -c", "nested shell execution"),
        ("/bin/bash", "explicit bash invocation"),
        ("/bin/sh", "explicit shell invocation"),
        ("eval ", "code evaluation"),
        ("exec ", "code execution"),
        ("source ", "script sourcing"),
        (". /", "script sourcing with dot"),
    ]

    for pattern, description in injection_patterns:
        if pattern in command:
            return False, f"Command injection detected: {description}"

    return True, None


def _validate_command_allowlist(command: str) -> tuple[bool, Optional[str]]:
    """
    Validate command against allow-list of safe operations.

    This is the primary security control. Only explicitly allowed
    commands can be executed.

    Args:
        command: Command to validate

    Returns:
        tuple: (is_safe, error_message)
    """
    # Extract base command (first word)
    cmd_parts = command.split()
    if not cmd_parts:
        return False, "Empty command"

    base_cmd = cmd_parts[0]

    # Allow-list of safe commands (read-only operations)
    SAFE_COMMANDS = {
        # File viewing
        "ls", "cat", "head", "tail", "less", "more",
        "file", "stat", "wc", "grep", "find",

        # Git (validated separately)
        "git",

        # System info (read-only)
        "pwd", "whoami", "date", "uptime",
        "df", "du", "ps", "top", "free",

        # Text processing (safe operations)
        "awk", "sed", "cut", "sort", "uniq", "tr",
        "echo", "printf",

        # Development tools (read-only)
        "python", "python3", "node", "npm", "pytest",
        "pip", "uv", "poetry",
    }

    if base_cmd not in SAFE_COMMANDS:
        return False, (
            f"Command '{base_cmd}' is not in the allow-list of safe commands. "
            f"Only read-only and safe operations are permitted in v0.1."
        )

    # Special validation for git commands
    if base_cmd == "git":
        if len(cmd_parts) < 2:
            return False, "Git command requires a subcommand"

        git_subcmd = cmd_parts[1]
        safe_git_cmds = [
            "status", "diff", "log", "show", "branch",
            "rev-parse", "config", "remote", "fetch",
        ]

        if git_subcmd not in safe_git_cmds:
            return False, (
                f"Git subcommand '{git_subcmd}' is not allowed. "
                f"Only read-only git operations are permitted: {', '.join(safe_git_cmds)}"
            )

    # Special validation for Python/Node (no -c flag for code execution)
    if base_cmd in ["python", "python3", "node"]:
        if "-c" in cmd_parts:
            return False, f"{base_cmd} with -c flag (code execution) is not allowed"

    # Check for output redirection (even in safe commands)
    if ">" in command or "<" in command:
        return False, "Output/input redirection is not allowed"

    # Check for pipe (even between safe commands, can be used for chaining)
    if "|" in command:
        return False, "Pipe operator is not allowed (prevents command chaining)"

    return True, None


def _validate_command_blacklist(command_lower: str) -> tuple[bool, Optional[str]]:
    """
    Legacy blacklist validation for dangerous operations.

    This is defense-in-depth. The allow-list should catch most issues,
    but this provides additional protection.

    Args:
        command_lower: Lowercase command string

    Returns:
        tuple: (is_safe, error_message)
    """
    # Dangerous commands
    dangerous_patterns = [
        ("rm ", "rm"),
        ("rmdir ", "rmdir"),
        ("mkfs", "mkfs"),
        ("dd ", "dd"),
        ("fdisk", "fdisk"),
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
        if path in command_lower:
            return False, f"Command attempts to access system path: {path}"

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


def generate_with_retry(
    provider: Any,
    prompt: str,
    context: Optional[dict[str, Any]] = None,
    max_retries: int = 3,
    retry_prompt_suffix: str = "\n\nPlease respond with valid JSON only.",
    system_prompt: Optional[str] = None
) -> dict[str, Any]:
    """
    Generate response with automatic retry on parse failures.

    Supports both command generation and question answering modes.
    This function wraps provider.generate() with retry logic, rate limiting,
    and exponential backoff. If the LLM response cannot be parsed, it retries
    with additional instructions.

    Args:
        provider: LLM provider instance (OpenAI, Ollama, etc.)
        prompt: User's natural language request
        context: Optional context dictionary
        max_retries: Maximum number of retry attempts (default: 3)
        retry_prompt_suffix: Additional instruction added on retry
        system_prompt: Optional system prompt with JSON format instructions

    Returns:
        dict: Parsed response with explanation, confidence, and optionally command

    Raises:
        RuntimeError: If rate limit is exceeded
        ValueError: If all retry attempts fail

    Examples:
        >>> # Command mode
        >>> from hai_sh.providers import OllamaProvider
        >>> provider = OllamaProvider({"model": "llama3.2"})
        >>> result = generate_with_retry(provider, "list files")
        >>> "command" in result
        True

        >>> # Question mode
        >>> result = generate_with_retry(provider, "What does ls do?")
        >>> "command" in result
        False
    """
    import time
    from hai_sh.rate_limit import check_rate_limit

    # Check rate limit before making any API calls
    provider_name = provider.__class__.__name__
    allowed, error_msg = check_rate_limit(provider_name)
    if not allowed:
        raise RuntimeError(f"Rate limit exceeded: {error_msg}")

    last_error = None
    current_prompt = prompt

    for attempt in range(max_retries):
        try:
            # Exponential backoff between retries (not on first attempt)
            if attempt > 0:
                backoff_seconds = 2 ** attempt  # 2s, 4s, 8s
                time.sleep(backoff_seconds)

            # Generate response from LLM
            response = provider.generate(current_prompt, context, system_prompt)

            # Try to parse the response
            parsed = parse_response(response)

            # Validate the command is safe (only if command is present)
            if "command" in parsed:
                is_safe, safety_error = validate_command(parsed["command"])
                if not is_safe:
                    # Add safety context to the command response
                    parsed["safety_warning"] = safety_error

            return parsed

        except ValueError as e:
            last_error = e

            # On last attempt, try fallback extraction
            if attempt == max_retries - 1:
                try:
                    fallback = extract_fallback_response(response)
                    if fallback:
                        return fallback
                except Exception:
                    pass  # Fallback also failed, will raise original error

            # Add retry instruction for next attempt
            if attempt < max_retries - 1:
                current_prompt = prompt + retry_prompt_suffix

    # All retries failed
    raise ValueError(
        f"Failed to generate valid response after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


def extract_fallback_response(response: str) -> Optional[dict[str, Any]]:
    """
    Attempt to extract command information from malformed responses.

    This is a best-effort fallback for when strict JSON parsing fails.
    It tries to extract command and explanation from common patterns.

    Args:
        response: Raw LLM response that failed JSON parsing

    Returns:
        dict: Partial response if extraction succeeds, None otherwise

    Example:
        >>> response = "I'll list files: `ls -la`"
        >>> result = extract_fallback_response(response)
        >>> result is not None
        True
    """
    # Try to find command in backticks
    command = None
    explanation = None

    # Pattern 1: Command in backticks (inline code)
    import re
    backtick_match = re.search(r'`([^`]+)`', response)
    if backtick_match:
        command = backtick_match.group(1).strip()

    # Pattern 2: Command in code block without language specifier
    code_block_match = re.search(r'```(?:\w+)?\s*\n?(.+?)\n?\s*```', response, re.DOTALL)
    if code_block_match and not command:
        command = code_block_match.group(1).strip()

    # Pattern 3: Command after "command:" or "Command:"
    command_match = re.search(r'[Cc]ommand:\s*(.+?)(?:\n|$)', response)
    if command_match and not command:
        command = command_match.group(1).strip()

    # Extract explanation (first sentence or paragraph)
    sentences = response.split('.')
    if sentences:
        explanation = sentences[0].strip() + '.'

    # Only return if we found a command
    if command:
        return {
            "explanation": explanation or "Command extracted from response",
            "command": command,
            "confidence": 50  # Lower confidence for fallback extraction
        }

    return None


def validate_response_fields(response: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate that a parsed response has all required fields with valid values.

    Args:
        response: Parsed response dictionary

    Returns:
        tuple: (is_valid, error_message)
            - is_valid: True if all fields are valid
            - error_message: None if valid, otherwise description of problem

    Example:
        >>> response = {"explanation": "test", "command": "ls", "confidence": 90}
        >>> is_valid, error = validate_response_fields(response)
        >>> is_valid
        True
    """
    # Check required fields exist
    required = ["explanation", "command", "confidence"]
    missing = [f for f in required if f not in response]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    # Check field types and values
    if not isinstance(response["explanation"], str) or not response["explanation"].strip():
        return False, "Explanation must be a non-empty string"

    if not isinstance(response["command"], str) or not response["command"].strip():
        return False, "Command must be a non-empty string"

    if not isinstance(response["confidence"], (int, float)):
        return False, "Confidence must be a number"

    if not (0 <= response["confidence"] <= 100):
        return False, "Confidence must be between 0 and 100"

    return True, None


# ============================================================================
# Smart Context Injection
# ============================================================================


# Context priority order (higher priority = more likely to be kept under budget)
CONTEXT_PRIORITY = {
    "cwd": 10,           # Always included
    "git": 9,            # Very relevant for development
    "git_enhanced": 9,   # Enhanced git context
    "shell_history": 7,  # Recent commands
    "env": 6,            # Environment info
    "files": 5,          # File listing
    "memory_session": 4, # Session memory
    "memory_dir": 3,     # Directory memory
    "memory_prefs": 2,   # User preferences
}


def _estimate_tokens(text: str) -> int:
    """
    Estimate number of tokens in a string.

    Uses a simple heuristic: ~4 characters per token on average.
    This is a rough estimate suitable for context budgeting.

    Args:
        text: Text to estimate tokens for

    Returns:
        int: Estimated number of tokens
    """
    if not text:
        return 0
    # Rough estimate: ~4 characters per token
    return max(1, len(text) // 4)


def _calculate_relevance(context: str, query: str) -> float:
    """
    Calculate relevance score between context and query.

    Uses simple word overlap and domain keyword matching.

    Args:
        context: Context text
        query: User's query

    Returns:
        float: Relevance score between 0.0 and 1.0
    """
    if not context or not query:
        return 0.0

    # Normalize to lowercase
    context_lower = context.lower()
    query_lower = query.lower()

    # Extract words (alphanumeric sequences)
    context_words = set(re.findall(r'\b\w+\b', context_lower))
    query_words = set(re.findall(r'\b\w+\b', query_lower))

    if not query_words:
        return 0.0

    # Calculate word overlap
    overlap = len(context_words & query_words)
    if overlap == 0:
        return 0.0

    # Base relevance from overlap
    relevance = overlap / len(query_words)

    # Boost for domain-specific keywords
    domain_keywords = {
        "git", "branch", "commit", "status", "diff", "push", "pull",
        "file", "directory", "folder", "path",
        "python", "node", "npm", "pip", "uv",
        "test", "build", "run", "command",
    }

    domain_overlap = len(context_words & domain_keywords & query_words)
    if domain_overlap > 0:
        relevance = min(1.0, relevance + 0.1 * domain_overlap)

    return min(1.0, relevance)


def _budget_context(
    context_parts: dict[str, str],
    max_tokens: int,
) -> dict[str, str]:
    """
    Budget context parts to fit within token limit.

    Prioritizes higher-priority context sources and truncates
    or removes lower-priority ones as needed.

    Args:
        context_parts: Dictionary of context key -> content
        max_tokens: Maximum tokens allowed

    Returns:
        dict: Budgeted context parts
    """
    if not context_parts:
        return {}

    if max_tokens <= 0:
        # Return only essential CWD if present
        if "cwd" in context_parts:
            cwd_content = context_parts["cwd"]
            if _estimate_tokens(cwd_content) <= 10:
                return {"cwd": cwd_content}
        return {}

    # Sort by priority (highest first)
    sorted_parts = sorted(
        context_parts.items(),
        key=lambda x: CONTEXT_PRIORITY.get(x[0], 0),
        reverse=True
    )

    result = {}
    remaining_tokens = max_tokens

    for key, content in sorted_parts:
        content_tokens = _estimate_tokens(content)

        if content_tokens <= remaining_tokens:
            # Fits entirely
            result[key] = content
            remaining_tokens -= content_tokens
        elif remaining_tokens > 20:
            # Truncate to fit (keep first part)
            # Estimate chars from remaining tokens
            max_chars = remaining_tokens * 4
            truncated = content[:max_chars]
            if len(truncated) < len(content):
                truncated = truncated.rsplit('\n', 1)[0] + "\n..."
            result[key] = truncated
            remaining_tokens = 0
        # else: skip this part

        if remaining_tokens <= 0:
            break

    return result


def collect_context(
    config: Optional[dict[str, Any]] = None,
    query: str = "",
    memory_manager: Optional["MemoryManager"] = None,
) -> dict[str, Any]:
    """
    Collect context from all enabled sources with relevance filtering and budgeting.

    This is the main entry point for smart context injection. It:
    1. Collects context from enabled sources (cwd, git, env, files, memory, history)
    2. Filters by relevance threshold
    3. Budgets to fit within token limit

    Args:
        config: Configuration dictionary with context settings
        query: User's query for relevance calculation
        memory_manager: Optional MemoryManager instance for memory context

    Returns:
        dict: Collected and budgeted context ready for prompt building
    """
    # Default configuration
    if config is None:
        config = {}

    context_config = config.get("context", {})

    # Extract settings with defaults
    include_history = context_config.get("include_history", True)
    history_length = context_config.get("history_length", 10)
    include_env = context_config.get("include_env_vars", True)
    include_git = context_config.get("include_git_state", True)
    include_files = context_config.get("include_file_listing", False)
    include_session_memory = context_config.get("include_session_memory", False)
    include_dir_memory = context_config.get("include_directory_memory", False)
    max_tokens = context_config.get("max_context_tokens", 4000)
    relevance_threshold = context_config.get("context_relevance_threshold", 0.3)

    # File listing settings
    file_max_files = context_config.get("file_listing_max_files", 20)
    file_max_depth = context_config.get("file_listing_max_depth", 1)
    file_show_hidden = context_config.get("file_listing_show_hidden", False)

    # Collect raw context parts
    context_parts: dict[str, str] = {}

    # Always include CWD
    try:
        cwd = os.getcwd()
        context_parts["cwd"] = f"Current directory: {cwd}"
    except OSError:
        context_parts["cwd"] = "Current directory: unknown"

    # Git context
    if include_git:
        try:
            from hai_sh.context import get_git_context_enhanced, format_git_context_enhanced
            git_context = get_git_context_enhanced()
            if git_context.get("is_git_repo"):
                formatted_git = format_git_context_enhanced(git_context)
                context_parts["git"] = formatted_git
        except ImportError:
            pass
        except Exception:
            pass

    # Environment context
    if include_env:
        try:
            from hai_sh.context import get_env_context, format_env_context
            env_context = get_env_context()
            formatted_env = format_env_context(env_context)
            if formatted_env:
                context_parts["env"] = formatted_env
        except ImportError:
            pass
        except Exception:
            pass

    # File listing
    if include_files:
        try:
            from hai_sh.context import get_file_listing_context, format_file_listing_context
            files_context = get_file_listing_context(
                max_files=file_max_files,
                max_depth=file_max_depth,
                show_hidden=file_show_hidden,
            )
            formatted_files = format_file_listing_context(files_context)
            if formatted_files:
                context_parts["files"] = formatted_files
        except ImportError:
            pass
        except Exception:
            pass

    # Shell history
    if include_history:
        try:
            from hai_sh.context import get_shell_history, format_shell_history
            history_context = get_shell_history(length=history_length)
            formatted_history = format_shell_history(history_context)
            if formatted_history:
                context_parts["shell_history"] = formatted_history
        except ImportError:
            pass
        except Exception:
            pass

    # Memory context
    memory_config = config.get("memory", {})
    memory_enabled = memory_config.get("enabled", True)

    if memory_enabled and memory_manager:
        # Session memory
        if include_session_memory:
            session_ctx = memory_manager.session.format_for_context()
            if session_ctx:
                context_parts["memory_session"] = session_ctx

        # Directory memory
        if include_dir_memory:
            dir_ctx = memory_manager.directory.format_for_context()
            if dir_ctx:
                context_parts["memory_dir"] = dir_ctx

    # Apply relevance filtering (skip cwd - always included)
    if relevance_threshold > 0 and query:
        filtered_parts = {"cwd": context_parts.get("cwd", "")}
        for key, content in context_parts.items():
            if key == "cwd":
                continue
            relevance = _calculate_relevance(content, query)
            if relevance >= relevance_threshold:
                filtered_parts[key] = content
        context_parts = filtered_parts

    # Budget context
    budgeted_parts = _budget_context(context_parts, max_tokens)

    # Convert to the format expected by build_system_prompt
    result: dict[str, Any] = {}

    if "cwd" in budgeted_parts:
        # Extract just the path
        cwd_line = budgeted_parts["cwd"]
        if ":" in cwd_line:
            result["cwd"] = cwd_line.split(":", 1)[1].strip()
        else:
            result["cwd"] = cwd_line

    if "git" in budgeted_parts:
        # Store raw formatted git context
        result["git"] = {"is_repo": True, "formatted": budgeted_parts["git"]}

    if "env" in budgeted_parts:
        result["env"] = {"formatted": budgeted_parts["env"]}

    if "files" in budgeted_parts:
        result["files"] = {"formatted": budgeted_parts["files"]}

    if "shell_history" in budgeted_parts:
        result["shell_history"] = budgeted_parts["shell_history"]

    if "memory_session" in budgeted_parts:
        result["memory_session"] = budgeted_parts["memory_session"]

    if "memory_dir" in budgeted_parts:
        result["memory_dir"] = budgeted_parts["memory_dir"]

    return result
