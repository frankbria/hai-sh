"""
Tests for input detection module.
"""

import pytest

from hai_sh.input_detector import (
    extract_query,
    get_prefix_variants,
    is_hai_input,
    normalize_input,
    parse_hai_input,
    validate_query,
)


# ============================================================================
# is_hai_input() Tests
# ============================================================================


@pytest.mark.unit
def test_is_hai_input_basic():
    """Test basic @hai prefix detection."""
    assert is_hai_input("@hai show me files") is True
    assert is_hai_input("@hai: what's my git status?") is True
    assert is_hai_input("@hai find *.py") is True


@pytest.mark.unit
def test_is_hai_input_case_insensitive():
    """Test case-insensitive prefix detection."""
    assert is_hai_input("@hai show files") is True
    assert is_hai_input("@HAI show files") is True
    assert is_hai_input("@Hai show files") is True
    assert is_hai_input("@HaI show files") is True


@pytest.mark.unit
def test_is_hai_input_with_whitespace():
    """Test prefix detection with leading/trailing whitespace."""
    assert is_hai_input("  @hai show files") is True
    assert is_hai_input("@hai  show files") is True
    assert is_hai_input("  @hai:  show files  ") is True
    assert is_hai_input("\t@hai show files") is True


@pytest.mark.unit
def test_is_hai_input_without_prefix():
    """Test rejection of input without @hai prefix."""
    assert is_hai_input("show me files") is False
    assert is_hai_input("hai show files") is False
    assert is_hai_input("@hello show files") is False
    assert is_hai_input("#hai show files") is False


@pytest.mark.unit
def test_is_hai_input_empty_query():
    """Test detection with empty query (just prefix)."""
    assert is_hai_input("@hai") is True
    assert is_hai_input("@hai:") is True
    assert is_hai_input("@hai  ") is True
    assert is_hai_input("  @hai:  ") is True


@pytest.mark.unit
def test_is_hai_input_edge_cases():
    """Test edge cases for prefix detection."""
    assert is_hai_input("") is False
    assert is_hai_input("   ") is False
    assert is_hai_input(None) is False
    assert is_hai_input(123) is False


@pytest.mark.unit
def test_is_hai_input_special_characters():
    """Test prefix detection with special characters in query."""
    assert is_hai_input("@hai find '*.py'") is True
    assert is_hai_input("@hai ls -la | grep foo") is True
    assert is_hai_input("@hai echo $HOME") is True
    assert is_hai_input("@hai: what's up?") is True


# ============================================================================
# extract_query() Tests
# ============================================================================


@pytest.mark.unit
def test_extract_query_basic():
    """Test basic query extraction."""
    assert extract_query("@hai show me files") == "show me files"
    assert extract_query("@hai: what's my git status?") == "what's my git status?"
    assert extract_query("@hai find *.py") == "find *.py"


@pytest.mark.unit
def test_extract_query_with_colon():
    """Test query extraction with optional colon."""
    assert extract_query("@hai show files") == "show files"
    assert extract_query("@hai: show files") == "show files"
    assert extract_query("@hai:show files") == "show files"
    assert extract_query("@hai :show files") == "show files"


@pytest.mark.unit
def test_extract_query_case_insensitive():
    """Test case-insensitive query extraction."""
    assert extract_query("@hai show files") == "show files"
    assert extract_query("@HAI show files") == "show files"
    assert extract_query("@Hai show files") == "show files"


@pytest.mark.unit
def test_extract_query_with_whitespace():
    """Test query extraction with extra whitespace."""
    assert extract_query("  @hai  show files  ") == "show files"
    assert extract_query("@hai:  show files") == "show files"
    assert extract_query("  @hai:  show files  ") == "show files"


@pytest.mark.unit
def test_extract_query_empty_query():
    """Test query extraction with empty query."""
    assert extract_query("@hai") == ""
    assert extract_query("@hai:") == ""
    assert extract_query("@hai  ") == ""
    assert extract_query("  @hai:  ") == ""


@pytest.mark.unit
def test_extract_query_without_prefix():
    """Test query extraction without @hai prefix."""
    assert extract_query("show me files") is None
    assert extract_query("hai show files") is None
    assert extract_query("@hello show files") is None


@pytest.mark.unit
def test_extract_query_edge_cases():
    """Test edge cases for query extraction."""
    assert extract_query("") is None
    assert extract_query("   ") is None
    assert extract_query(None) is None
    assert extract_query(123) is None


@pytest.mark.unit
def test_extract_query_special_characters():
    """Test query extraction with special characters."""
    assert extract_query("@hai find '*.py'") == "find '*.py'"
    assert extract_query("@hai ls -la | grep foo") == "ls -la | grep foo"
    assert extract_query("@hai echo $HOME") == "echo $HOME"
    assert extract_query("@hai: what's up?") == "what's up?"


@pytest.mark.unit
def test_extract_query_multiline():
    """Test query extraction with newlines."""
    query = "@hai find . -name '*.py'"
    assert extract_query(query) == "find . -name '*.py'"


# ============================================================================
# parse_hai_input() Tests
# ============================================================================


@pytest.mark.unit
def test_parse_hai_input_valid():
    """Test parsing valid @hai input."""
    assert parse_hai_input("@hai show me files") == "show me files"
    assert parse_hai_input("@hai: what's my git status?") == "what's my git status?"
    assert parse_hai_input("@hai find *.py") == "find *.py"


@pytest.mark.unit
def test_parse_hai_input_empty_query():
    """Test parsing with empty query returns None."""
    assert parse_hai_input("@hai") is None
    assert parse_hai_input("@hai:") is None
    assert parse_hai_input("@hai  ") is None
    assert parse_hai_input("  @hai:  ") is None


@pytest.mark.unit
def test_parse_hai_input_without_prefix():
    """Test parsing without prefix returns None."""
    assert parse_hai_input("show me files") is None
    assert parse_hai_input("hai show files") is None
    assert parse_hai_input("@hello show files") is None


@pytest.mark.unit
def test_parse_hai_input_edge_cases():
    """Test edge cases for parsing."""
    assert parse_hai_input("") is None
    assert parse_hai_input("   ") is None
    assert parse_hai_input(None) is None
    assert parse_hai_input(123) is None


@pytest.mark.unit
def test_parse_hai_input_with_whitespace():
    """Test parsing with extra whitespace."""
    assert parse_hai_input("  @hai  show files  ") == "show files"
    assert parse_hai_input("@hai:  show files") == "show files"


@pytest.mark.unit
def test_parse_hai_input_case_insensitive():
    """Test case-insensitive parsing."""
    assert parse_hai_input("@hai show files") == "show files"
    assert parse_hai_input("@HAI show files") == "show files"
    assert parse_hai_input("@Hai show files") == "show files"


# ============================================================================
# normalize_input() Tests
# ============================================================================


@pytest.mark.unit
def test_normalize_input_basic():
    """Test basic input normalization."""
    assert normalize_input("@hai show files") == "@hai show files"
    assert normalize_input("  @hai show files  ") == "@hai show files"


@pytest.mark.unit
def test_normalize_input_multiple_spaces():
    """Test normalization of multiple spaces."""
    assert normalize_input("@hai   show    files") == "@hai show files"
    assert normalize_input("@hai  show  files") == "@hai show files"


@pytest.mark.unit
def test_normalize_input_preserve_quotes():
    """Test that quotes are preserved during normalization."""
    assert normalize_input("@hai find 'my file.txt'") == "@hai find 'my file.txt'"
    assert normalize_input('@hai echo "hello world"') == '@hai echo "hello world"'


@pytest.mark.unit
def test_normalize_input_tabs_and_newlines():
    """Test normalization of tabs and newlines."""
    assert normalize_input("@hai\tshow\tfiles") == "@hai show files"
    assert normalize_input("@hai\nshow\nfiles") == "@hai show files"


@pytest.mark.unit
def test_normalize_input_edge_cases():
    """Test edge cases for normalization."""
    assert normalize_input("") == ""
    assert normalize_input("   ") == ""
    assert normalize_input(None) == ""
    assert normalize_input(123) == ""


@pytest.mark.unit
def test_normalize_input_special_chars():
    """Test normalization preserves special characters."""
    assert normalize_input("@hai ls -la | grep foo") == "@hai ls -la | grep foo"
    assert normalize_input("@hai echo $HOME") == "@hai echo $HOME"


# ============================================================================
# get_prefix_variants() Tests
# ============================================================================


@pytest.mark.unit
def test_get_prefix_variants_returns_list():
    """Test that get_prefix_variants returns a list."""
    variants = get_prefix_variants()
    assert isinstance(variants, list)
    assert len(variants) > 0


@pytest.mark.unit
def test_get_prefix_variants_contains_expected():
    """Test that variants list contains expected prefixes."""
    variants = get_prefix_variants()
    assert '@hai' in variants
    assert '@hai:' in variants
    assert '@HAI' in variants
    assert '@HAI:' in variants


@pytest.mark.unit
def test_get_prefix_variants_all_unique():
    """Test that all variants are unique."""
    variants = get_prefix_variants()
    assert len(variants) == len(set(variants))


# ============================================================================
# validate_query() Tests
# ============================================================================


@pytest.mark.unit
def test_validate_query_valid():
    """Test validation of valid queries."""
    is_valid, error = validate_query("show me files")
    assert is_valid is True
    assert error is None

    is_valid, error = validate_query("find . -name '*.py'")
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_query_empty():
    """Test validation rejects empty queries."""
    is_valid, error = validate_query("")
    assert is_valid is False
    assert "empty" in error.lower()


@pytest.mark.unit
def test_validate_query_too_long():
    """Test validation rejects queries that are too long."""
    long_query = "a" * 20000
    is_valid, error = validate_query(long_query)
    assert is_valid is False
    assert "too long" in error.lower()


@pytest.mark.unit
def test_validate_query_max_length():
    """Test validation accepts queries at max length."""
    max_query = "a" * 10000
    is_valid, error = validate_query(max_query)
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_query_null_bytes():
    """Test validation rejects queries with null bytes."""
    is_valid, error = validate_query("show\x00files")
    assert is_valid is False
    assert "null" in error.lower()


@pytest.mark.unit
def test_validate_query_control_characters():
    """Test validation rejects control characters (except tabs/newlines)."""
    # Bell character (control character)
    is_valid, error = validate_query("show\x07files")
    assert is_valid is False
    assert "control" in error.lower()


@pytest.mark.unit
def test_validate_query_allows_tabs_and_newlines():
    """Test validation allows tabs and newlines."""
    is_valid, error = validate_query("show\tfiles")
    assert is_valid is True
    assert error is None

    is_valid, error = validate_query("show\nfiles")
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_query_not_string():
    """Test validation rejects non-string queries."""
    is_valid, error = validate_query(123)
    assert is_valid is False
    assert "string" in error.lower()

    is_valid, error = validate_query(None)
    assert is_valid is False
    assert "empty" in error.lower()


@pytest.mark.unit
def test_validate_query_special_chars():
    """Test validation allows special characters."""
    is_valid, error = validate_query("find '*.py' | grep foo")
    assert is_valid is True
    assert error is None

    is_valid, error = validate_query("echo $HOME && ls -la")
    assert is_valid is True
    assert error is None


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
def test_integration_full_workflow():
    """Test full workflow from detection to query extraction."""
    inputs = [
        "@hai show me large files",
        "@hai: what's my git status?",
        "  @HAI  find *.py  ",
    ]

    for input_text in inputs:
        # Should be detected as hai input
        assert is_hai_input(input_text) is True

        # Should extract query
        query = extract_query(input_text)
        assert query is not None
        assert len(query) > 0

        # Should parse successfully
        parsed = parse_hai_input(input_text)
        assert parsed is not None
        assert parsed == query

        # Query should be valid
        is_valid, error = validate_query(parsed)
        assert is_valid is True
        assert error is None


@pytest.mark.unit
def test_integration_invalid_inputs():
    """Test full workflow with invalid inputs."""
    invalid_inputs = [
        "show me files",  # No prefix
        "@hello show files",  # Wrong prefix
        "@hai",  # Empty query
        "",  # Empty input
    ]

    for input_text in invalid_inputs:
        parsed = parse_hai_input(input_text)
        # Should return None for invalid inputs
        assert parsed is None


@pytest.mark.unit
def test_integration_normalize_then_parse():
    """Test normalization followed by parsing."""
    input_text = "  @hai   show    files  "

    # Normalize first
    normalized = normalize_input(input_text)
    assert normalized == "@hai show files"

    # Then parse
    parsed = parse_hai_input(normalized)
    assert parsed == "show files"
