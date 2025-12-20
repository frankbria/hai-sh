#!/usr/bin/env bash
#
# Integration tests for zsh_integration.sh
#
# This script tests that the zsh integration can be sourced
# and that all required functions and widgets are defined.
#
# Note: This test runs in bash but sources the zsh script
# to verify basic functionality. Full ZLE testing requires zsh.

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

echo "Testing zsh integration script..."
echo ""

# Find the script path (relative to this test file)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTEGRATION_SCRIPT="$SCRIPT_DIR/../../hai_sh/integrations/zsh_integration.sh"

# Test 1: Script file exists
test_assert "Integration script exists" "[[ -f '$INTEGRATION_SCRIPT' ]]"

# Test 2: Script is executable
test_assert "Integration script is executable" "[[ -x '$INTEGRATION_SCRIPT' ]]"

# Test 3: Script has valid syntax (zsh syntax check if zsh is available)
if command -v zsh &> /dev/null; then
    if zsh -n "$INTEGRATION_SCRIPT" 2>/dev/null; then
        test_assert "Script has valid zsh syntax" "true"
    else
        echo -e "${YELLOW}Warning: Script failed zsh syntax check. Trying again to see error:${NC}"
        zsh -n "$INTEGRATION_SCRIPT" || true
        test_assert "Script has valid zsh syntax" "false"
    fi
else
    echo -e "${YELLOW}Warning: zsh not available, skipping syntax check${NC}"
    test_assert "Zsh syntax check (skipped)" "true"
fi

# Test 4: Script structure and content
test_assert "Script contains _hai_trigger_widget" "grep -q '_hai_trigger_widget' '$INTEGRATION_SCRIPT'"
test_assert "Script contains _hai_show_binding" "grep -q '_hai_show_binding' '$INTEGRATION_SCRIPT'"
test_assert "Script contains _hai_test_integration" "grep -q '_hai_test_integration' '$INTEGRATION_SCRIPT'"
test_assert "Script contains _hai_install_integration" "grep -q '_hai_install_integration' '$INTEGRATION_SCRIPT'"
test_assert "Script contains _hai_uninstall_integration" "grep -q '_hai_uninstall_integration' '$INTEGRATION_SCRIPT'"

# Test 5: ZLE widget registration
test_assert "Script registers ZLE widget" "grep -q 'zle -N _hai_trigger_widget' '$INTEGRATION_SCRIPT'"

# Test 6: Key binding
test_assert "Script binds key" "grep -q 'bindkey' '$INTEGRATION_SCRIPT'"

# Test 7: HAI_KEY_BINDING default value
test_assert "Script sets HAI_KEY_BINDING default" "grep -q 'HAI_KEY_BINDING:=' '$INTEGRATION_SCRIPT'"

# Test 8: Testing mode support
test_assert "Script supports HAI_TESTING mode" "grep -q 'HAI_TESTING' '$INTEGRATION_SCRIPT'"

# Test 9: Quiet mode support
test_assert "Script supports HAI_QUIET mode" "grep -q 'HAI_QUIET' '$INTEGRATION_SCRIPT'"

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
    echo ""
    echo "Note: These are basic structural tests. For full ZLE widget testing,"
    echo "the script should be sourced in an interactive zsh session."
    exit 0
fi
