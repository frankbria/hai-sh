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
        print -r "$json" | jq -r '.conversation'
        print "<<<SEPARATOR>>>"
        print -r "$json" | jq -r '.command'
        print "<<<SEPARATOR>>>"
        print -r "$json" | jq -r '.confidence'
        return 0
    else
        # Basic fallback parsing (not robust)
        print "Warning: Install python3 or jq for better JSON parsing" >&2
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
        print -P "%{${color}%}${confidence}%%%{${reset}%} [${bar}]"
    else
        print "${confidence}% [${bar}]"
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
    local cyan="%{[96m%}"
    local green="%{[92m%}"
    local bold="%{[1m%}"
    local reset="%{[0m%}"

    if [[ "$use_colors" != "true" ]]; then
        cyan=""
        green=""
        bold=""
        reset=""
    fi

    print ""
    print -P "${cyan}━━━ Conversation ━━━${reset}"
    print "$conversation"
    print ""
    print -P "${bold}Confidence:${reset} $(_hai_format_confidence "$confidence" "$use_colors")"
    print ""

    # Only show execution layer if there's a command (not question mode)
    if [[ -n "$command" ]]; then
        print "═══════════════════"
        print -P "${cyan}━━━ Execution ━━━${reset}"
        print -P "${green}\$ ${command}${reset}"
        print ""
    fi
}

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

    # Remove @hai prefix if present (hai will handle it)
    query="${query#@hai }"
    query="${query#@hai}"

    # Clear the current buffer
    BUFFER=""
    zle redisplay

    # Show processing message for user feedback
    print ""
    print "🤖 hai: Processing '$query'..."
    print ""

    # Call hai with --suggest-only to get JSON response
    local json_response
    if ! json_response=$(hai --suggest-only "$query" 2>&1); then
        print ""
        print "✗ Error calling hai:"
        print "$json_response"
        print ""
        # Restore original buffer
        BUFFER="$current_buffer"
        CURSOR="$saved_cursor"
        zle reset-prompt
        return 1
    fi

    # Parse JSON response
    local parse_output
    if ! parse_output=$(_hai_parse_json "$json_response"); then
        print ""
        print "✗ Error parsing response"
        print "Raw output: $json_response"
        print ""
        # Restore original buffer
        BUFFER="$current_buffer"
        CURSOR="$saved_cursor"
        zle reset-prompt
        return 1
    fi

    # Extract fields (separated by <<<SEPARATOR>>>)
    local conversation
    local command
    local confidence

    # Use awk to split on multi-character delimiter
    conversation=$(print -r "$parse_output" | awk 'BEGIN{RS="<<<SEPARATOR>>>"} NR==1{print}')
    command=$(print -r "$parse_output" | awk 'BEGIN{RS="<<<SEPARATOR>>>"} NR==2{print}')
    confidence=$(print -r "$parse_output" | awk 'BEGIN{RS="<<<SEPARATOR>>>"} NR==3{print}')

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
        BUFFER=""
        zle reset-prompt
        return 0
    fi

    # Put the command on the buffer for user to review and execute
    # User can press Enter to execute, or edit/cancel manually
    BUFFER="$command"
    CURSOR="${#command}"

    print "→ Command ready on prompt. Press Enter to execute, or edit/cancel as needed."
    print ""

    zle reset-prompt

    return 0
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
