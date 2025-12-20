#!/usr/bin/env zsh
# hai-sh zsh integration
#
# This script provides keyboard shortcut integration for hai-sh in zsh.
#
# Installation:
#   Add the following line to your ~/.zshrc:
#   source ~/.hai/zsh_integration.sh
#
# Usage:
#   - Type your command or @hai query
#   - Press Ctrl+X Ctrl+H (or your custom binding)
#   - hai will generate and suggest a command
#
# Customization:
#   Set HAI_KEY_BINDING before sourcing to customize the key binding:
#   export HAI_KEY_BINDING="^H"     # Use Ctrl+H
#   export HAI_KEY_BINDING="^[h"    # Use Alt+H (Escape-h)

# Default key binding: Ctrl+X Ctrl+H
# This is chosen for portability across different terminals
: "${HAI_KEY_BINDING:=^X^H}"

# Check if hai command is available (skip in testing mode)
if [[ -z "$HAI_TESTING" ]] && ! command -v hai &> /dev/null; then
    print "Warning: 'hai' command not found. Install hai-sh first." >&2
    return 1 2>/dev/null || exit 1
fi

# ZLE widget to trigger hai-sh
_hai_trigger_widget() {
    local current_buffer="$BUFFER"
    local current_cursor="$CURSOR"

    # Save cursor position
    local saved_cursor="$current_cursor"

    # If the buffer is empty, show help
    if [[ -z "$current_buffer" ]]; then
        print ""
        print "hai-sh: Type a command description or @hai query, then press the shortcut again."
        print "Examples:"
        print "  @hai show me large files"
        print "  @hai what's my git status?"
        print "  find large files  (will be processed by hai)"
        zle reset-prompt
        return 0
    fi

    # Prepare the query
    local query="$current_buffer"

    # If the buffer doesn't start with @hai, prepend it
    if [[ ! "$query" =~ ^[[:space:]]*@hai ]]; then
        query="@hai $query"
    fi

    # Clear the current buffer
    BUFFER=""
    zle redisplay

    # Echo what we're processing (for user feedback)
    print ""
    print "🤖 hai: Processing: $query"
    print ""

    # Call hai with the query and capture the result
    # Note: This is a simplified version. In a full implementation,
    # hai would return the command and ask for confirmation.
    local result
    if result=$(hai "$query" 2>&1); then
        # If successful, put the result on the command line
        BUFFER="$result"
        CURSOR="${#result}"

        # Show the result
        print "✓ Suggested command: $result"
        print ""
    else
        # If failed, restore the original buffer
        BUFFER="$current_buffer"
        CURSOR="$saved_cursor"

        print "✗ Error: $result"
        print ""
    fi

    # Reset the prompt to show the new buffer
    zle reset-prompt
}

# Function to display current key binding
_hai_show_binding() {
    local binding_desc
    case "$HAI_KEY_BINDING" in
        "^X^H")
            binding_desc="Ctrl+X Ctrl+H"
            ;;
        "^H")
            binding_desc="Ctrl+H"
            ;;
        "^[h")
            binding_desc="Alt+H"
            ;;
        *)
            binding_desc="$HAI_KEY_BINDING"
            ;;
    esac

    print "hai-sh keyboard shortcut: $binding_desc"
}

# Function to test if hai integration is working
_hai_test_integration() {
    print "Testing hai-sh zsh integration..."
    print ""

    # Check if hai is available
    if command -v hai &> /dev/null; then
        print "✓ hai command found: $(which hai)"
    else
        print "✗ hai command not found"
        return 1
    fi

    # Check if the widget is defined
    if zle -l | grep -q "_hai_trigger_widget"; then
        print "✓ _hai_trigger_widget is defined"
    else
        print "✗ _hai_trigger_widget not defined"
        return 1
    fi

    # Check if the widget is bound
    if bindkey | grep -q "_hai_trigger_widget"; then
        print "✓ Widget is bound to key"
    else
        print "✗ Widget is not bound to any key"
        return 1
    fi

    # Show the current binding
    print "✓ Key binding: $(_hai_show_binding)"

    print ""
    print "Integration test passed!"
    print ""
    print "Usage:"
    print "  1. Type a command description or @hai query"
    print "  2. Press $(_hai_show_binding)"
    print "  3. hai will suggest a command"
    print ""

    return 0
}

# Function to install integration to ~/.zshrc
_hai_install_integration() {
    local zshrc="$HOME/.zshrc"
    local integration_line="source ~/.hai/zsh_integration.sh"

    # Check if already installed
    if grep -q "hai/zsh_integration.sh" "$zshrc" 2>/dev/null; then
        print "hai-sh integration already installed in $zshrc"
        return 0
    fi

    # Create backup
    if [[ -f "$zshrc" ]]; then
        cp "$zshrc" "${zshrc}.backup.$(date +%Y%m%d_%H%M%S)"
        print "Created backup: ${zshrc}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # Add integration
    print "" >> "$zshrc"
    print "# hai-sh integration" >> "$zshrc"
    print "$integration_line" >> "$zshrc"

    print "✓ hai-sh integration added to $zshrc"
    print ""
    print "To activate, run: source $zshrc"
    print "Or start a new terminal session."
}

# Function to uninstall integration from ~/.zshrc
_hai_uninstall_integration() {
    local zshrc="$HOME/.zshrc"

    if [[ ! -f "$zshrc" ]]; then
        print "No $zshrc file found"
        return 0
    fi

    # Check if installed
    if ! grep -q "hai/zsh_integration.sh" "$zshrc"; then
        print "hai-sh integration not found in $zshrc"
        return 0
    fi

    # Create backup
    cp "$zshrc" "${zshrc}.backup.$(date +%Y%m%d_%H%M%S)"
    print "Created backup: ${zshrc}.backup.$(date +%Y%m%d_%H%M%S)"

    # Remove integration lines
    sed -i.tmp '/# hai-sh integration/d' "$zshrc"
    sed -i.tmp '/hai\/zsh_integration.sh/d' "$zshrc"
    rm -f "${zshrc}.tmp"

    print "✓ hai-sh integration removed from $zshrc"
    print ""
    print "To deactivate, restart your terminal or run: source $zshrc"
}

# Register the widget with ZLE
zle -N _hai_trigger_widget

# Bind the key to the widget
bindkey "$HAI_KEY_BINDING" _hai_trigger_widget

# Optionally show the binding on first load (can be disabled by setting HAI_QUIET=1)
if [[ -z "$HAI_QUIET" ]]; then
    print "hai-sh loaded. Press $(_hai_show_binding) to activate."
fi
