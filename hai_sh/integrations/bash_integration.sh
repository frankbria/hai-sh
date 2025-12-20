#!/usr/bin/env bash
# hai-sh bash integration
#
# This script provides keyboard shortcut integration for hai-sh in bash.
#
# Installation:
#   Add the following line to your ~/.bashrc:
#   source ~/.hai/bash_integration.sh
#
# Usage:
#   - Type your command or @hai query
#   - Press Ctrl+X Ctrl+H (or your custom binding)
#   - hai will generate and suggest a command
#
# Customization:
#   Set HAI_KEY_BINDING before sourcing to customize the key binding:
#   export HAI_KEY_BINDING="\C-h"  # Use Ctrl+H
#   export HAI_KEY_BINDING="\eh"   # Use Alt+H

# Default key binding: Ctrl+X Ctrl+H
# This is chosen for portability across different terminals
: "${HAI_KEY_BINDING:=\C-x\C-h}"

# Check if hai command is available (skip in testing mode)
if [[ -z "$HAI_TESTING" ]] && ! command -v hai &> /dev/null; then
    echo "Warning: 'hai' command not found. Install hai-sh first." >&2
    return 1 2>/dev/null || exit 1
fi

# Function to trigger hai-sh from readline
_hai_trigger() {
    local current_line="$READLINE_LINE"
    local current_point="$READLINE_POINT"

    # Save cursor position
    local saved_cursor="$current_point"

    # If the line is empty, show help
    if [[ -z "$current_line" ]]; then
        echo ""
        echo "hai-sh: Type a command description or @hai query, then press the shortcut again."
        echo "Examples:"
        echo "  @hai show me large files"
        echo "  @hai what's my git status?"
        echo "  find large files  (will be processed by hai)"
        READLINE_LINE=""
        READLINE_POINT=0
        return 0
    fi

    # Prepare the query
    local query="$current_line"

    # If the line doesn't start with @hai, prepend it
    if [[ ! "$query" =~ ^[[:space:]]*@hai ]]; then
        query="@hai $query"
    fi

    # Clear the current line
    READLINE_LINE=""
    READLINE_POINT=0

    # Echo what we're processing (for user feedback)
    echo ""
    echo "🤖 hai: Processing: $query"
    echo ""

    # Call hai with the query and capture the result
    # Note: This is a simplified version. In a full implementation,
    # hai would return the command and ask for confirmation.
    local result
    if result=$(hai "$query" 2>&1); then
        # If successful, put the result on the command line
        READLINE_LINE="$result"
        READLINE_POINT="${#result}"

        # Show the result
        echo "✓ Suggested command: $result"
        echo ""
    else
        # If failed, restore the original line
        READLINE_LINE="$current_line"
        READLINE_POINT="$saved_cursor"

        echo "✗ Error: $result"
        echo ""
    fi
}

# Function to display current key binding
_hai_show_binding() {
    local binding_desc
    case "$HAI_KEY_BINDING" in
        "\\C-x\\C-h")
            binding_desc="Ctrl+X Ctrl+H"
            ;;
        "\\C-h")
            binding_desc="Ctrl+H"
            ;;
        "\\eh")
            binding_desc="Alt+H"
            ;;
        *)
            binding_desc="$HAI_KEY_BINDING"
            ;;
    esac

    echo "hai-sh keyboard shortcut: $binding_desc"
}

# Function to test if hai integration is working
_hai_test_integration() {
    echo "Testing hai-sh bash integration..."
    echo ""

    # Check if hai is available
    if command -v hai &> /dev/null; then
        echo "✓ hai command found: $(which hai)"
    else
        echo "✗ hai command not found"
        return 1
    fi

    # Check if the function is defined
    if declare -f _hai_trigger &> /dev/null; then
        echo "✓ _hai_trigger function defined"
    else
        echo "✗ _hai_trigger function not defined"
        return 1
    fi

    # Show the current binding
    echo "✓ Key binding: $(_hai_show_binding)"

    echo ""
    echo "Integration test passed!"
    echo ""
    echo "Usage:"
    echo "  1. Type a command description or @hai query"
    echo "  2. Press $(_hai_show_binding)"
    echo "  3. hai will suggest a command"
    echo ""

    return 0
}

# Function to install integration to ~/.bashrc
_hai_install_integration() {
    local bashrc="$HOME/.bashrc"
    local integration_line="source ~/.hai/bash_integration.sh"

    # Check if already installed
    if grep -q "hai/bash_integration.sh" "$bashrc" 2>/dev/null; then
        echo "hai-sh integration already installed in $bashrc"
        return 0
    fi

    # Create backup
    if [[ -f "$bashrc" ]]; then
        cp "$bashrc" "${bashrc}.backup.$(date +%Y%m%d_%H%M%S)"
        echo "Created backup: ${bashrc}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # Add integration
    echo "" >> "$bashrc"
    echo "# hai-sh integration" >> "$bashrc"
    echo "$integration_line" >> "$bashrc"

    echo "✓ hai-sh integration added to $bashrc"
    echo ""
    echo "To activate, run: source $bashrc"
    echo "Or start a new terminal session."
}

# Function to uninstall integration from ~/.bashrc
_hai_uninstall_integration() {
    local bashrc="$HOME/.bashrc"

    if [[ ! -f "$bashrc" ]]; then
        echo "No $bashrc file found"
        return 0
    fi

    # Check if installed
    if ! grep -q "hai/bash_integration.sh" "$bashrc"; then
        echo "hai-sh integration not found in $bashrc"
        return 0
    fi

    # Create backup
    cp "$bashrc" "${bashrc}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Created backup: ${bashrc}.backup.$(date +%Y%m%d_%H%M%S)"

    # Remove integration lines
    sed -i '/# hai-sh integration/d' "$bashrc"
    sed -i '/hai\/bash_integration.sh/d' "$bashrc"

    echo "✓ hai-sh integration removed from $bashrc"
    echo ""
    echo "To deactivate, restart your terminal or run: source $bashrc"
}

# Bind the key to the function
# Use bind -x to execute a shell command when the key is pressed
if [[ $- == *i* ]]; then
    # Only bind in interactive shells
    bind -x "\"$HAI_KEY_BINDING\": _hai_trigger"

    # Optionally show the binding on first load (can be disabled by setting HAI_QUIET=1)
    if [[ -z "$HAI_QUIET" ]]; then
        echo "hai-sh loaded. Press $(_hai_show_binding) to activate."
    fi
fi

# Export functions so they're available in subshells
export -f _hai_trigger
export -f _hai_show_binding
export -f _hai_test_integration
export -f _hai_install_integration
export -f _hai_uninstall_integration
