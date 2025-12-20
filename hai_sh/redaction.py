"""
Output redaction for sensitive data protection.

This module provides redaction capabilities to prevent sensitive
information from leaking through command outputs.
"""

import re
from typing import Optional


def redact_sensitive_output(output: str) -> str:
    """
    Redact sensitive information from command output.

    Detects and redacts:
    - API keys (various formats)
    - AWS credentials
    - JWT tokens
    - Passwords and secrets
    - SSH keys
    - Generic credential patterns

    Args:
        output: Raw command output

    Returns:
        str: Output with sensitive information redacted

    Example:
        >>> output = "OPENAI_API_KEY=sk-1234567890abcdef"
        >>> redacted = redact_sensitive_output(output)
        >>> "***REDACTED***" in redacted
        True
    """
    if not output:
        return output

    redacted = output

    # Pattern 1: OpenAI API keys (sk-...)
    redacted = re.sub(
        r'sk-[a-zA-Z0-9]{32,}',
        '***OPENAI_KEY_REDACTED***',
        redacted
    )

    # Pattern 2: Anthropic API keys (sk-ant-...)
    redacted = re.sub(
        r'sk-ant-[a-zA-Z0-9_-]{32,}',
        '***ANTHROPIC_KEY_REDACTED***',
        redacted
    )

    # Pattern 3: AWS Access Key IDs
    redacted = re.sub(
        r'AKIA[0-9A-Z]{16}',
        '***AWS_ACCESS_KEY_REDACTED***',
        redacted
    )

    # Pattern 4: AWS Secret Access Keys (after equals sign or colon)
    redacted = re.sub(
        r'(aws_secret_access_key\s*[:=]\s*)[^\s\n]+',
        r'\1***AWS_SECRET_REDACTED***',
        redacted,
        flags=re.IGNORECASE
    )

    # Pattern 5: JWT tokens
    redacted = re.sub(
        r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',
        '***JWT_TOKEN_REDACTED***',
        redacted
    )

    # Pattern 6: Generic password patterns
    redacted = re.sub(
        r'(password\s*[:=]\s*)[^\s\n]+',
        r'\1***PASSWORD_REDACTED***',
        redacted,
        flags=re.IGNORECASE
    )

    # Pattern 7: Generic token patterns
    redacted = re.sub(
        r'(token\s*[:=]\s*)[^\s\n]+',
        r'\1***TOKEN_REDACTED***',
        redacted,
        flags=re.IGNORECASE
    )

    # Pattern 8: Generic secret patterns
    redacted = re.sub(
        r'(secret\s*[:=]\s*)[^\s\n]+',
        r'\1***SECRET_REDACTED***',
        redacted,
        flags=re.IGNORECASE
    )

    # Pattern 9: Generic API key patterns
    redacted = re.sub(
        r'(api[_-]?key\s*[:=]\s*)[^\s\n]+',
        r'\1***API_KEY_REDACTED***',
        redacted,
        flags=re.IGNORECASE
    )

    # Pattern 10: SSH private keys
    redacted = re.sub(
        r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        '***SSH_PRIVATE_KEY_REDACTED***',
        redacted
    )

    # Pattern 11: Generic long alphanumeric strings (likely keys/tokens)
    # Only redact if they appear after common key indicators
    redacted = re.sub(
        r'([A-Z_]+(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|PWD)\s*[:=]\s*)([a-zA-Z0-9+/=]{20,})',
        r'\1***CREDENTIAL_REDACTED***',
        redacted
    )

    # Pattern 12: GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_)
    redacted = re.sub(
        r'gh[pousr]_[a-zA-Z0-9]{36,}',
        '***GITHUB_TOKEN_REDACTED***',
        redacted
    )

    # Pattern 13: MongoDB connection strings
    redacted = re.sub(
        r'mongodb(\+srv)?://[^@]+@[^\s\n]+',
        r'mongodb://***USER:PASS_REDACTED***@***HOST_REDACTED***',
        redacted
    )

    # Pattern 14: PostgreSQL connection strings
    redacted = re.sub(
        r'postgres(ql)?://[^@]+@[^\s\n]+',
        r'postgresql://***USER:PASS_REDACTED***@***HOST_REDACTED***',
        redacted
    )

    # Pattern 15: Generic URLs with credentials
    redacted = re.sub(
        r'https?://([^:@\s]+):([^:@\s]+)@',
        r'https://***USER_REDACTED***:***PASS_REDACTED***@',
        redacted
    )

    return redacted


def should_redact_output(config: Optional[dict] = None) -> bool:
    """
    Check if output redaction should be enabled.

    Args:
        config: Configuration dictionary (checks privacy.redact_output)

    Returns:
        bool: True if redaction should be enabled
    """
    if config is None:
        return True  # Default: always redact

    # Check privacy settings in config
    privacy_settings = config.get("privacy", {})
    return privacy_settings.get("redact_output", True)
