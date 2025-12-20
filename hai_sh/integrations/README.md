# hai-sh Shell Integrations

This directory contains shell integration scripts that provide keyboard shortcuts and enhanced functionality for hai-sh.

## Bash Integration

The bash integration provides a keyboard shortcut to trigger hai-sh directly from your bash command line.

### Quick Start

1. **Install hai-sh** (if not already installed):
   ```bash
   pip install hai-sh
   ```

2. **Set up the integration**:
   ```bash
   # Option 1: Automatic installation
   source ~/.hai/bash_integration.sh
   _hai_install_integration

   # Option 2: Manual installation
   echo 'source ~/.hai/bash_integration.sh' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Use the shortcut**:
   - Type a command description: `show me large files`
   - Press **Ctrl+X Ctrl+H**
   - hai will generate a command for you!

### Key Binding

**Default**: `Ctrl+X Ctrl+H`

The default binding is chosen for maximum compatibility across different terminals and doesn't conflict with common bash shortcuts.

### Customizing the Key Binding

You can customize the key binding by setting the `HAI_KEY_BINDING` environment variable before sourcing the integration script:

```bash
# In your ~/.bashrc, BEFORE sourcing the integration:

# Use Ctrl+H (may conflict with backspace in some terminals)
export HAI_KEY_BINDING="\C-h"

# Use Alt+H (Escape then H)
export HAI_KEY_BINDING="\eh"

# Use Ctrl+X H (Ctrl+X followed by H)
export HAI_KEY_BINDING="\C-xh"

# Then source the integration
source ~/.hai/bash_integration.sh
```

### Common Key Binding Options

| Binding | Environment Variable | Notes |
|---------|---------------------|-------|
| Ctrl+X Ctrl+H | `\C-x\C-h` | Default, most compatible |
| Alt+H | `\eh` | Good alternative, works in most terminals |
| Ctrl+H | `\C-h` | May conflict with backspace |
| Ctrl+Space | `\C-@` | Alternative, may conflict with mark-set |

### Usage

#### Method 1: Type and Trigger
```bash
# Type your query
find large files

# Press Ctrl+X Ctrl+H
# hai suggests: find ~ -type f -size +100M -exec du -h {} + | sort -rh | head -20
```

#### Method 2: Use @hai Prefix
```bash
# Type with @hai prefix
@hai show me my git status

# Press Ctrl+X Ctrl+H
# hai suggests: git status
```

#### Method 3: Empty Line Help
```bash
# Press Ctrl+X Ctrl+H on empty line
# Shows help and examples
```

### Features

- **Automatic @hai Prefix**: If your query doesn't start with `@hai`, it will be automatically prepended
- **Readline Integration**: Works seamlessly with bash's readline library
- **Current Line Capture**: Processes whatever you've typed so far
- **Error Handling**: Shows errors and preserves your original input
- **Help on Empty Line**: Press the shortcut on an empty line for quick help

### Helper Functions

The integration provides several helper functions:

```bash
# Test if the integration is working
_hai_test_integration

# Show the current key binding
_hai_show_binding

# Install integration to ~/.bashrc (with backup)
_hai_install_integration

# Remove integration from ~/.bashrc (with backup)
_hai_uninstall_integration
```

### Quiet Mode

To suppress the "hai-sh loaded" message on shell startup:

```bash
# In your ~/.bashrc, BEFORE sourcing:
export HAI_QUIET=1
source ~/.hai/bash_integration.sh
```

### Troubleshooting

#### Integration Not Working

1. **Check if hai is installed**:
   ```bash
   which hai
   ```

2. **Test the integration**:
   ```bash
   _hai_test_integration
   ```

3. **Verify the function is defined**:
   ```bash
   declare -f _hai_trigger
   ```

4. **Check the key binding**:
   ```bash
   _hai_show_binding
   bind -P | grep hai
   ```

#### Key Binding Conflicts

If your chosen key binding conflicts with another bash function:

1. List all current bindings:
   ```bash
   bind -P
   ```

2. Choose a different key binding:
   ```bash
   export HAI_KEY_BINDING="\eh"  # Use Alt+H instead
   ```

3. Reload your shell:
   ```bash
   source ~/.bashrc
   ```

#### Terminal-Specific Issues

Some terminals may handle special key combinations differently:

- **iTerm2/Terminal.app (macOS)**: May need to enable "Use Option as Meta key" in preferences
- **GNOME Terminal**: Works with default settings
- **Windows Terminal/WSL**: Works with default settings
- **tmux/screen**: May require additional configuration for some key combinations

### Examples

```bash
# Example 1: Find files
Type: find python files modified today
Press: Ctrl+X Ctrl+H
Result: find . -name "*.py" -mtime -1 -type f

# Example 2: Git operations
Type: @hai what changed in the last commit?
Press: Ctrl+X Ctrl+H
Result: git show HEAD

# Example 3: System info
Type: show disk usage
Press: Ctrl+X Ctrl+H
Result: df -h

# Example 4: Process management
Type: @hai find processes using port 3000
Press: Ctrl+X Ctrl+H
Result: lsof -i :3000
```

### Uninstallation

To remove the bash integration:

```bash
# Automatic removal
_hai_uninstall_integration

# Manual removal
# Edit ~/.bashrc and remove the line:
# source ~/.hai/bash_integration.sh
```

### Advanced Configuration

#### Custom Post-Processing

You can add custom post-processing by defining a function before sourcing the integration:

```bash
# In ~/.bashrc before sourcing integration
_hai_postprocess() {
    local command="$1"
    # Add custom logic here
    echo "$command"
}
export -f _hai_postprocess
```

#### Integration with Other Tools

The bash integration can work alongside other command-line tools:

```bash
# Use with fzf for command history
# Use with zoxide for directory jumping
# Use with starship for enhanced prompts
```

---

## Zsh Integration

The zsh integration provides a keyboard shortcut to trigger hai-sh directly from your zsh command line, with full support for oh-my-zsh and other zsh frameworks.

### Quick Start

1. **Install hai-sh** (if not already installed):
   ```zsh
   pip install hai-sh
   ```

2. **Set up the integration**:
   ```zsh
   # Option 1: Automatic installation
   source ~/.hai/zsh_integration.sh
   _hai_install_integration

   # Option 2: Manual installation
   echo 'source ~/.hai/zsh_integration.sh' >> ~/.zshrc
   source ~/.zshrc
   ```

3. **Use the shortcut**:
   - Type a command description: `show me large files`
   - Press **Ctrl+X Ctrl+H**
   - hai will generate a command for you!

### Key Binding

**Default**: `Ctrl+X Ctrl+H`

The default binding is chosen for maximum compatibility across different terminals and zsh configurations (including oh-my-zsh).

### Customizing the Key Binding

You can customize the key binding by setting the `HAI_KEY_BINDING` environment variable before sourcing the integration script:

```zsh
# In your ~/.zshrc, BEFORE sourcing the integration:

# Use Ctrl+H (may conflict with backspace in some terminals)
export HAI_KEY_BINDING="^H"

# Use Alt+H (Escape-h)
export HAI_KEY_BINDING="^[h"

# Use Ctrl+Space
export HAI_KEY_BINDING="^@"

# Then source the integration
source ~/.hai/zsh_integration.sh
```

### ZLE Widget System

The zsh integration uses ZLE (Zsh Line Editor) widgets:

- **Widget**: `_hai_trigger_widget` - The core ZLE widget
- **Buffer Access**: Uses `$BUFFER` and `$CURSOR` variables
- **Registration**: `zle -N _hai_trigger_widget`
- **Binding**: `bindkey "$HAI_KEY_BINDING" _hai_trigger_widget`

### Common Key Binding Options

| Binding | Environment Variable | Notes |
|---------|---------------------|-------|
| Ctrl+X Ctrl+H | `^X^H` | Default, most compatible |
| Alt+H | `^[h` | Good alternative (Escape-h) |
| Ctrl+H | `^H` | May conflict with backspace |
| Ctrl+Space | `^@` | Alternative option |

### Usage

#### Method 1: Type and Trigger
```zsh
# Type your query
find large files

# Press Ctrl+X Ctrl+H
# hai suggests: find ~ -type f -size +100M -exec du -h {} + | sort -rh | head -20
```

#### Method 2: Use @hai Prefix
```zsh
# Type with @hai prefix
@hai show me my git status

# Press Ctrl+X Ctrl+H
# hai suggests: git status
```

#### Method 3: Empty Line Help
```zsh
# Press Ctrl+X Ctrl+H on empty line
# Shows help and examples
```

### Features

- **ZLE Integration**: Works seamlessly with Zsh Line Editor
- **Automatic @hai Prefix**: If your query doesn't start with `@hai`, it will be automatically prepended
- **Buffer Manipulation**: Processes and replaces the current command line buffer
- **Error Handling**: Shows errors and preserves your original input
- **Help on Empty Line**: Press the shortcut on an empty line for quick help
- **oh-my-zsh Compatible**: Works with all oh-my-zsh themes and plugins

### Helper Functions

The integration provides several helper functions:

```zsh
# Test if the integration is working
_hai_test_integration

# Show the current key binding
_hai_show_binding

# Install integration to ~/.zshrc (with backup)
_hai_install_integration

# Remove integration from ~/.zshrc (with backup)
_hai_uninstall_integration
```

### Quiet Mode

To suppress the "hai-sh loaded" message on shell startup:

```zsh
# In your ~/.zshrc, BEFORE sourcing:
export HAI_QUIET=1
source ~/.hai/zsh_integration.sh
```

### oh-my-zsh Integration

The hai-sh integration works perfectly with oh-my-zsh:

```zsh
# In your ~/.zshrc, after oh-my-zsh initialization:

# oh-my-zsh configuration
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git docker kubectl)
source $ZSH/oh-my-zsh.sh

# hai-sh integration (after oh-my-zsh)
source ~/.hai/zsh_integration.sh
```

### Troubleshooting

#### Integration Not Working

1. **Check if hai is installed**:
   ```zsh
   which hai
   ```

2. **Test the integration**:
   ```zsh
   _hai_test_integration
   ```

3. **Verify the widget is registered**:
   ```zsh
   zle -l | grep hai
   ```

4. **Check the key binding**:
   ```zsh
   _hai_show_binding
   bindkey | grep hai
   ```

#### Conflicts with oh-my-zsh Plugins

If you experience conflicts with oh-my-zsh plugins:

1. **Load hai-sh after oh-my-zsh**:
   ```zsh
   source $ZSH/oh-my-zsh.sh  # First
   source ~/.hai/zsh_integration.sh  # After
   ```

2. **Check for key binding conflicts**:
   ```zsh
   bindkey | grep "^X^H"
   ```

3. **Use a different key binding**:
   ```zsh
   export HAI_KEY_BINDING="^[h"  # Use Alt+H instead
   ```

#### Terminal-Specific Issues

Some terminals may handle special key combinations differently:

- **iTerm2/Terminal.app (macOS)**: Works with default settings
- **GNOME Terminal**: Works with default settings
- **Alacritty**: Works with default settings
- **Kitty**: Works with default settings
- **tmux/screen**: May require additional configuration for some key combinations

### Examples

```zsh
# Example 1: Find files
Type: find python files modified today
Press: Ctrl+X Ctrl+H
Result: find . -name "*.py" -mtime -1 -type f

# Example 2: Git operations
Type: @hai what changed in the last commit?
Press: Ctrl+X Ctrl+H
Result: git show HEAD

# Example 3: System info
Type: show disk usage
Press: Ctrl+X Ctrl+H
Result: df -h

# Example 4: Docker commands
Type: @hai list running containers
Press: Ctrl+X Ctrl+H
Result: docker ps
```

### Uninstallation

To remove the zsh integration:

```zsh
# Automatic removal
_hai_uninstall_integration

# Manual removal
# Edit ~/.zshrc and remove the line:
# source ~/.hai/zsh_integration.sh
```

### Advanced Configuration

#### Custom Widget Extensions

You can extend the widget functionality by wrapping it:

```zsh
# In ~/.zshrc after sourcing integration
_hai_trigger_widget_extended() {
    # Custom pre-processing
    # ...

    # Call original widget
    _hai_trigger_widget

    # Custom post-processing
    # ...
}

# Replace the widget
zle -N _hai_trigger_widget_extended
bindkey "$HAI_KEY_BINDING" _hai_trigger_widget_extended
```

#### Integration with Other ZLE Widgets

The hai-sh integration can work alongside other ZLE widgets and plugins:

```zsh
# Use with zsh-autosuggestions
# Use with zsh-syntax-highlighting
# Use with zsh-history-substring-search
# Use with fzf-tab
```

## Future Integrations
- **Fish Integration**: Coming soon
- **PowerShell Integration**: Coming soon

## Contributing

To contribute a new shell integration:

1. Create a new script in this directory: `<shell>_integration.sh`
2. Follow the same structure and helper functions as bash_integration.sh
3. Add documentation to this README
4. Test across different terminals and OS platforms
5. Submit a pull request

## License

Same as hai-sh main project.
