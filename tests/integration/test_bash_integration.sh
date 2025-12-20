#!/usr/bin/env bash
#
# Integration tests for bash_integration.sh
#
# This script tests that the bash integration can be sourced
# and that all required functions are defined.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_assert() {
    local description="$1"
    local condition="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    if eval "$condition"; then
        echo -e "${GREEN}✓${NC} $description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $description"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

echo "Testing bash integration script..."
echo ""

# Find the script path (relative to this test file)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTEGRATION_SCRIPT="$SCRIPT_DIR/../../hai_sh/integrations/bash_integration.sh"

# Test 1: Script file exists
test_assert "Integration script exists" "[[ -f '$INTEGRATION_SCRIPT' ]]"

# Test 2: Script is executable
test_assert "Integration script is executable" "[[ -x '$INTEGRATION_SCRIPT' ]]"

# Test 3: Script has valid bash syntax
if bash -n "$INTEGRATION_SCRIPT" 2>/dev/null; then
    test_assert "Script has valid bash syntax" "true"
else
    test_assert "Script has valid bash syntax" "false"
fi

# Test 4: Script can be sourced without errors
# We need to suppress the hai command check for testing
export HAI_QUIET=1
export HAI_TESTING=1
if source "$INTEGRATION_SCRIPT" 2>/dev/null; then
    test_assert "Script can be sourced" "true"
else
    # Try sourcing again to see the error
    echo -e "${YELLOW}Warning: Script failed to source. Trying again to see error:${NC}"
    source "$INTEGRATION_SCRIPT" || true
    test_assert "Script can be sourced" "false"
fi

# Only run function tests if sourcing succeeded
if [[ $TESTS_FAILED -eq 0 ]]; then
    # Test 5: _hai_trigger function is defined
    test_assert "_hai_trigger function is defined" "declare -f _hai_trigger &>/dev/null"

    # Test 6: _hai_show_binding function is defined
    test_assert "_hai_show_binding function is defined" "declare -f _hai_show_binding &>/dev/null"

    # Test 7: _hai_test_integration function is defined
    test_assert "_hai_test_integration function is defined" "declare -f _hai_test_integration &>/dev/null"

    # Test 8: _hai_install_integration function is defined
    test_assert "_hai_install_integration function is defined" "declare -f _hai_install_integration &>/dev/null"

    # Test 9: _hai_uninstall_integration function is defined
    test_assert "_hai_uninstall_integration function is defined" "declare -f _hai_uninstall_integration &>/dev/null"

    # Test 10: Default key binding is set
    test_assert "HAI_KEY_BINDING is set" "[[ -n '$HAI_KEY_BINDING' ]]"

    # Test 11: _hai_show_binding returns output
    test_assert "_hai_show_binding produces output" "[[ -n \$(_hai_show_binding) ]]"
fi

# Summary
echo ""
echo "================================================"
echo "Test Summary:"
echo "  Total:  $TESTS_RUN"
echo -e "  ${GREEN}Passed: $TESTS_PASSED${NC}"
if [[ $TESTS_FAILED -gt 0 ]]; then
    echo -e "  ${RED}Failed: $TESTS_FAILED${NC}"
else
    echo -e "  ${GREEN}Failed: $TESTS_FAILED${NC}"
fi
echo "================================================"

# Exit with failure if any tests failed
if [[ $TESTS_FAILED -gt 0 ]]; then
    exit 1
else
    echo ""
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
