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

# Helper function to parse JSON response from hai --suggest-only
_hai_parse_json() {
    local json="$1"

    # Try to use python3 for JSON parsing (most reliable)
    if command -v python3 &> /dev/null; then
        python3 -c "
import json, sys
try:
    data = json.loads('''$json''')
    print(data.get('conversation', ''))
    print('<<<SEPARATOR>>>')
    print(data.get('command', ''))
    print('<<<SEPARATOR>>>')
    print(data.get('confidence', 0))
except:
    sys.exit(1)
"
        return $?
    # Fallback to jq if available
    elif command -v jq &> /dev/null; then
        echo "$json" | jq -r '.conversation'
        echo "<<<SEPARATOR>>>"
        echo "$json" | jq -r '.command'
        echo "<<<SEPARATOR>>>"
        echo "$json" | jq -r '.confidence'
        return 0
    else
        # Basic fallback parsing (not robust)
        echo "Warning: Install python3 or jq for better JSON parsing" >&2
        return 1
    fi
}

# Helper function to format confidence bar
_hai_format_confidence() {
    local confidence="$1"
    local use_colors="${2:-true}"

    # Calculate bar (10 blocks total)
    local filled=$((confidence / 10))
    local empty=$((10 - filled))

    local bar=""
    for ((i=0; i<filled; i++)); do
        bar+="█"
    done
    for ((i=0; i<empty; i++)); do
        bar+="·"
    done

    # Color code based on confidence
    if [[ "$use_colors" == "true" ]] && [[ -z "$NO_COLOR" ]]; then
        local color=""
        if ((confidence >= 80)); then
            color="\033[92m"  # Green
        elif ((confidence >= 60)); then
            color="\033[93m"  # Yellow
        else
            color="\033[91m"  # Red
        fi
        local reset="\033[0m"
        echo -e "${color}${confidence}%${reset} [${bar}]"
    else
        echo "${confidence}% [${bar}]"
    fi
}

# Helper function to display dual-layer output
_hai_display_dual_layer() {
    local conversation="$1"
    local command="$2"
    local confidence="$3"
    local use_colors="true"

    # Check if colors should be disabled
    if [[ -n "$NO_COLOR" ]]; then
        use_colors="false"
    fi

    # ANSI color codes
    local cyan="\033[96m"
    local green="\033[92m"
    local bold="\033[1m"
    local reset="\033[0m"

    if [[ "$use_colors" != "true" ]]; then
        cyan=""
        green=""
        bold=""
        reset=""
    fi

    echo ""
    echo -e "${cyan}━━━ Conversation ━━━${reset}"
    echo "$conversation"
    echo ""
    echo -e "${bold}Confidence:${reset} $(_hai_format_confidence "$confidence" "$use_colors")"
    echo ""

    # Only show execution layer if there's a command (not question mode)
    if [[ -n "$command" ]]; then
        echo "═══════════════════"
        echo -e "${cyan}━━━ Execution ━━━${reset}"
        echo -e "${green}\$ ${command}${reset}"
        echo ""
    fi
}

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

    # Remove @hai prefix if present (hai will handle it)
    query="${query#@hai }"
    query="${query#@hai}"

    # Clear the current line
    READLINE_LINE=""
    READLINE_POINT=0

    # Show processing message for user feedback
    echo ""
    echo "🤖 hai: Processing '$query'..."
    echo ""

    # Call hai with --suggest-only to get JSON response
    local json_response
    if ! json_response=$(hai --suggest-only "$query" 2>&1); then
        echo ""
        echo "✗ Error calling hai:"
        echo "$json_response"
        echo ""
        # Restore original line
        READLINE_LINE="$current_line"
        READLINE_POINT="$saved_cursor"
        return 1
    fi

    # Parse JSON response
    local parse_output
    if ! parse_output=$(_hai_parse_json "$json_response"); then
        echo ""
        echo "✗ Error parsing response"
        echo "Raw output: $json_response"
        echo ""
        # Restore original line
        READLINE_LINE="$current_line"
        READLINE_POINT="$saved_cursor"
        return 1
    fi

    # Extract fields (separated by <<<SEPARATOR>>>)
    local conversation
    local command
    local confidence

    # Use awk to split on multi-character delimiter
    conversation=$(echo "$parse_output" | awk 'BEGIN{RS="<<<SEPARATOR>>>"} NR==1{print}')
    command=$(echo "$parse_output" | awk 'BEGIN{RS="<<<SEPARATOR>>>"} NR==2{print}')
    confidence=$(echo "$parse_output" | awk 'BEGIN{RS="<<<SEPARATOR>>>"} NR==3{print}')

    # Clean up leading/trailing whitespace
    # Remove leading whitespace
    conversation="${conversation#"${conversation%%[![:space:]]*}"}"
    command="${command#"${command%%[![:space:]]*}"}"
    confidence="${confidence#"${confidence%%[![:space:]]*}"}"
    # Remove trailing whitespace
    conversation="${conversation%"${conversation##*[![:space:]]}"}"
    command="${command%"${command##*[![:space:]]}"}"
    confidence="${confidence%"${confidence##*[![:space:]]}"}"

    # Display dual-layer output
    _hai_display_dual_layer "$conversation" "$command" "$confidence"

    # If no command (question mode), just return
    if [[ -z "$command" ]]; then
        READLINE_LINE=""
        READLINE_POINT=0
        return 0
    fi

    # Put the command on the readline buffer for user to review and execute
    # User can press Enter to execute, or edit/cancel manually
    READLINE_LINE="$command"
    READLINE_POINT="${#command}"

    echo "→ Command ready on prompt. Press Enter to execute, or edit/cancel as needed."
    echo ""

    return 0
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
