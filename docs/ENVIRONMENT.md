# Environment Variable Handling in hai-sh

This document describes how hai-sh handles environment variables during command execution.

## Overview

hai-sh ensures that executed commands inherit and preserve the current shell environment, including all environment variables, PATH settings, and shell-specific variables. This behavior is essential for commands to execute in the expected context with access to the same tools and settings as your interactive shell.

## Default Behavior

### Automatic Environment Inheritance

By default, all executed commands inherit the complete environment from the parent process:

```python
from hai_sh import execute_command

# Command automatically inherits current environment
result = execute_command("echo $HOME")
print(result.stdout)  # Shows your home directory
```

This includes all standard environment variables:
- `PATH` - Command search path
- `HOME` - User home directory
- `USER` - Current username
- `SHELL` - Current shell path
- `PWD` - Current working directory
- `LANG` - Locale settings
- `TERM` - Terminal type
- All custom environment variables

### Environment Preservation

The executor automatically preserves the environment by:
1. Creating a copy of `os.environ` when no custom environment is provided
2. Passing this environment to the subprocess
3. Ensuring no pollution of the parent process environment

## Custom Environment

### Providing Custom Environment

You can provide a custom environment dictionary to modify or replace variables:

```python
from hai_sh import execute_command
import os

# Create custom environment
custom_env = os.environ.copy()
custom_env["MY_VAR"] = "custom_value"
custom_env["PATH"] = f"/custom/bin:{custom_env['PATH']}"

result = execute_command("echo $MY_VAR:$PATH", env=custom_env)
```

### Adding Variables

Add new environment variables without affecting the parent:

```python
custom_env = os.environ.copy()
custom_env["NEW_VAR"] = "new_value"

result = execute_command("echo $NEW_VAR", env=custom_env)
# Parent environment remains unchanged
```

### Modifying Variables

Modify existing variables for a specific command:

```python
custom_env = os.environ.copy()
custom_env["LANG"] = "en_US.UTF-8"
custom_env["TZ"] = "America/New_York"

result = execute_command("date", env=custom_env)
```

### Removing Variables

Exclude specific variables from the subprocess environment:

```python
# Create environment without sensitive variables
safe_env = {
    k: v for k, v in os.environ.items()
    if not k.startswith("SECRET_")
}

result = execute_command("env", env=safe_env)
```

## Environment Isolation

### Parent Environment Protection

Changes made within a subprocess **do not** affect the parent process:

```python
import os

# Parent environment
os.environ["TEST_VAR"] = "original"

# Subprocess modifies variable
result = execute_command("export TEST_VAR=modified; echo $TEST_VAR")
print(result.stdout)  # Shows "modified"

# Parent environment unchanged
print(os.environ["TEST_VAR"])  # Still "original"
```

### No Environment Pollution

The executor ensures subprocess environments don't pollute the parent:

```python
# Subprocess sets new variable
execute_command("export NEW_VAR=value")

# Parent environment unaffected
assert "NEW_VAR" not in os.environ
```

## Shell-Specific Variables

### Preserved Shell Variables

The following shell-specific variables are automatically preserved:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `SHELL` | Current shell path | `/bin/bash` |
| `HOME` | User home directory | `/home/username` |
| `USER` | Username | `username` |
| `PWD` | Current working directory | `/path/to/directory` |
| `PATH` | Command search path | `/usr/bin:/bin:/usr/local/bin` |
| `LANG` | Locale setting | `en_US.UTF-8` |
| `TERM` | Terminal type | `xterm-256color` |

### Working with Shell Variables

Access shell variables in commands:

```python
# Use shell variable substitution
result = execute_command("ls $HOME")

# Use variable concatenation
result = execute_command("echo ${HOME}/Documents")

# Use variable with default values
result = execute_command("echo ${UNSET_VAR:-default}")
```

## Environment with Directory Changes

### PWD Updates

When specifying a working directory, `PWD` is automatically updated:

```python
result = execute_command("pwd", cwd="/tmp")
print(result.stdout)  # Shows "/tmp"
```

### Environment Preservation with CWD

Custom environment variables work with directory changes:

```python
custom_env = os.environ.copy()
custom_env["PROJECT_DIR"] = "/path/to/project"

result = execute_command(
    "echo $PWD:$PROJECT_DIR",
    cwd="/tmp",
    env=custom_env
)
```

## Special Cases

### Variables with Spaces

Handle variables containing spaces:

```python
custom_env = os.environ.copy()
custom_env["MESSAGE"] = "hello world"

result = execute_command('echo "$MESSAGE"', env=custom_env)
```

### Variables with Special Characters

Handle special characters in values:

```python
custom_env = os.environ.copy()
custom_env["SPECIAL"] = "value!@#$%"

result = execute_command('echo "$SPECIAL"', env=custom_env)
```

### Variables with Newlines

Handle multi-line values:

```python
custom_env = os.environ.copy()
custom_env["MULTILINE"] = "line1\\nline2\\nline3"

result = execute_command('echo "$MULTILINE"', env=custom_env)
```

### Empty vs Unset Variables

Distinguish between empty and unset variables:

```python
custom_env = os.environ.copy()
custom_env["EMPTY"] = ""
# UNSET is not in the dictionary

# Both expand to empty string in bash
result1 = execute_command("echo x${EMPTY}x", env=custom_env)  # "xx"
result2 = execute_command("echo x${UNSET}x", env=custom_env)  # "xx"
```

## Best Practices

### 1. Always Copy os.environ

When creating custom environments, always start with a copy:

```python
# Good: Start with copy
custom_env = os.environ.copy()
custom_env["MY_VAR"] = "value"

# Bad: Modify os.environ directly
os.environ["MY_VAR"] = "value"  # Affects parent process!
```

### 2. Preserve Essential Variables

Ensure essential variables remain in custom environments:

```python
custom_env = os.environ.copy()

# Keep PATH for command execution
assert "PATH" in custom_env

# Keep HOME for user context
assert "HOME" in custom_env
```

### 3. Clean Up Test Variables

Remove test variables after use:

```python
test_var = "TEST_VAR"
os.environ[test_var] = "test_value"

try:
    result = execute_command(f"echo ${test_var}")
    # ... test code ...
finally:
    if test_var in os.environ:
        del os.environ[test_var]
```

### 4. Use Environment for Configuration

Pass configuration through environment variables:

```python
custom_env = os.environ.copy()
custom_env["LOG_LEVEL"] = "DEBUG"
custom_env["CONFIG_FILE"] = "/path/to/config.yaml"

result = execute_command("./my_script.sh", env=custom_env)
```

### 5. Isolate Sensitive Data

Keep sensitive data out of subprocess environments:

```python
# Remove API keys before execution
safe_env = {
    k: v for k, v in os.environ.items()
    if not k.endswith("_API_KEY")
}

result = execute_command("external_command", env=safe_env)
```

## Implementation Details

### Environment Copying

The executor uses `os.environ.copy()` to create a snapshot:

```python
def execute_command(command, env=None, ...):
    if env is None:
        env = os.environ.copy()
    # ... execute with env
```

This ensures:
- All current variables are included
- Parent environment remains unchanged
- Subprocess gets independent copy

### Subprocess Integration

Environment is passed to `subprocess.run()`:

```python
result = subprocess.run(
    command,
    shell=True,
    env=env,  # Custom or copied environment
    # ... other parameters
)
```

### Cross-Platform Compatibility

Environment handling works consistently across:
- Linux
- macOS
- Windows (with WSL)

## Testing

The environment behavior is thoroughly tested with 30+ test cases covering:

- ✅ Environment inheritance
- ✅ Variable preservation (PATH, HOME, USER, SHELL, etc.)
- ✅ Custom environment handling
- ✅ Environment isolation
- ✅ Variable modifications
- ✅ Shell-specific variables
- ✅ Special characters and edge cases
- ✅ Integration with working directory changes

See `tests/unit/test_executor_environment.py` for comprehensive test coverage.

## Troubleshooting

### Command Not Found

If commands aren't found, check PATH:

```python
result = execute_command("echo $PATH")
print(result.stdout)  # Verify PATH includes command location
```

### Variable Not Expanding

Ensure proper quoting:

```python
# Wrong: Single quotes prevent expansion
result = execute_command('echo \'$HOME\'')  # Shows literal "$HOME"

# Right: Double quotes allow expansion
result = execute_command('echo "$HOME"')  # Shows /home/username
```

### Environment Changes Not Visible

Remember subprocess changes don't affect parent:

```python
# This sets variable only in subprocess
execute_command("export MY_VAR=value")

# Parent doesn't see it
assert "MY_VAR" not in os.environ
```

To set in parent, modify `os.environ` directly:

```python
os.environ["MY_VAR"] = "value"
result = execute_command("echo $MY_VAR")  # Now visible
```

## Security Considerations

### Avoid Exposing Secrets

Don't pass secrets through environment when possible:

```python
# Prefer: Use secure credential storage
# Avoid: Passing secrets in environment
custom_env["API_KEY"] = "secret123"  # Risky!
```

### Validate Environment Input

Validate environment values from untrusted sources:

```python
user_input = get_user_input()

# Validate before using
if not is_safe(user_input):
    raise ValueError("Unsafe environment value")

custom_env["USER_VAR"] = user_input
```

### Limit Environment Exposure

Only include necessary variables for external commands:

```python
# Minimal environment
minimal_env = {
    "PATH": os.environ["PATH"],
    "HOME": os.environ["HOME"],
}

result = execute_command("untrusted_command", env=minimal_env)
```

## See Also

- [Executor Documentation](EXECUTOR.md) - Command execution details
- [Context Documentation](CONTEXT.md) - Context gathering for LLM
- [API Reference](API.md) - Complete API documentation
