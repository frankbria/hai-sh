"""
Input detection for @hai prefix in shell commands.

This module provides functionality to detect when user input starts with
the @hai prefix and extract the query text for processing by hai-sh.
"""

import re
from typing import Optional


# Supported prefix patterns
HAI_PREFIX_PATTERN = re.compile(
    r'^\s*@hai\s*:?\s*(.*)$',
    re.IGNORECASE
)


def is_hai_input(text: str) -> bool:
    """
    Check if the input text starts with @hai prefix.

    Supports various formats:
    - @hai show me large files
    - @hai: what's my git status?
    - @hai find TypeScript files
    - @HAI (case-insensitive)
    -   @hai   (with leading/trailing whitespace)

    Args:
        text: Input text to check

    Returns:
        bool: True if text starts with @hai prefix

    Example:
        >>> is_hai_input("@hai show files")
        True
        >>> is_hai_input("show files")
        False
        >>> is_hai_input("  @hai:  find *.py")
        True
    """
    if not text or not isinstance(text, str):
        return False

    return HAI_PREFIX_PATTERN.match(text) is not None


def extract_query(text: str) -> Optional[str]:
    """
    Extract the query text after @hai prefix.

    Args:
        text: Input text with @hai prefix

    Returns:
        str: Query text after prefix, or None if no @hai prefix found
             Returns empty string if prefix exists but no query follows

    Example:
        >>> extract_query("@hai show me large files")
        'show me large files'
        >>> extract_query("@hai: what's my git status?")
        "what's my git status?"
        >>> extract_query("@hai")
        ''
        >>> extract_query("show files")
        None
    """
    if not text or not isinstance(text, str):
        return None

    match = HAI_PREFIX_PATTERN.match(text)
    if not match:
        return None

    # Extract and strip the query portion
    query = match.group(1).strip()
    return query


def parse_hai_input(text: str) -> Optional[str]:
    """
    Parse input text and return query if it's a valid @hai command.

    This is a convenience function that combines detection and extraction.
    Returns None if:
    - Input doesn't start with @hai prefix
    - Query text is empty after prefix

    Args:
        text: Input text to parse

    Returns:
        str: Query text if valid @hai input with non-empty query
        None: If not a @hai input or query is empty

    Example:
        >>> parse_hai_input("@hai show me large files")
        'show me large files'
        >>> parse_hai_input("@hai")
        None
        >>> parse_hai_input("show files")
        None
        >>> parse_hai_input("  @hai:  find *.py  ")
        'find *.py'
    """
    query = extract_query(text)

    # Return None if no prefix found or query is empty
    if query is None or not query:
        return None

    return query


def normalize_input(text: str) -> str:
    """
    Normalize input text for consistent processing.

    Performs:
    - Strip leading/trailing whitespace
    - Collapse multiple spaces to single space
    - Preserve special characters and quotes

    Args:
        text: Input text to normalize

    Returns:
        str: Normalized text

    Example:
        >>> normalize_input("  @hai   show    files  ")
        '@hai show files'
        >>> normalize_input("@hai find 'my file.txt'")
        "@hai find 'my file.txt'"
    """
    if not text or not isinstance(text, str):
        return ""

    # Strip leading/trailing whitespace
    normalized = text.strip()

    # Collapse multiple spaces to single space (but preserve quotes)
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized


def get_prefix_variants() -> list[str]:
    """
    Get list of supported @hai prefix variants.

    Returns:
        list[str]: List of prefix patterns that are recognized

    Example:
        >>> variants = get_prefix_variants()
        >>> '@hai' in variants
        True
        >>> '@hai:' in variants
        True
    """
    return [
        '@hai',
        '@hai:',
        '@HAI',
        '@HAI:',
        '@Hai',
        '@Hai:',
    ]


def validate_query(query: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a query string is safe and well-formed.

    Checks for:
    - Non-empty query
    - Reasonable length (< 10000 chars to prevent abuse)
    - No null bytes or control characters (except newlines/tabs)

    Args:
        query: Query text to validate

    Returns:
        tuple: (is_valid, error_message)
            - is_valid: True if query is valid
            - error_message: None if valid, otherwise description of problem

    Example:
        >>> validate_query("show me files")
        (True, None)
        >>> validate_query("")
        (False, 'Query cannot be empty')
        >>> validate_query("a" * 20000)
        (False, 'Query too long (max 10000 characters)')
    """
    if not query:
        return False, "Query cannot be empty"

    if not isinstance(query, str):
        return False, "Query must be a string"

    # Check length
    if len(query) > 10000:
        return False, "Query too long (max 10000 characters)"

    # Check for null bytes
    if '\x00' in query:
        return False, "Query contains invalid null bytes"

    # Check for problematic control characters (allow newlines and tabs)
    control_chars = [chr(i) for i in range(32) if i not in (9, 10, 13)]
    if any(char in query for char in control_chars):
        return False, "Query contains invalid control characters"

    return True, None
