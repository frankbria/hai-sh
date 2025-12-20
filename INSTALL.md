# hai-sh Installation Guide

Complete guide for installing and setting up hai-sh, your AI-powered terminal assistant.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Install via pipx (Recommended for CLI Tools)](#install-via-pipx-recommended-for-cli-tools)
  - [Install via pip (Alternative Method)](#install-via-pip-alternative-method)
  - [Install for Development](#install-for-development)
- [Shell Integration Setup](#shell-integration-setup)
  - [Bash Setup](#bash-setup)
  - [Zsh Setup](#zsh-setup)
- [First-Run Configuration](#first-run-configuration)
- [Verification Steps](#verification-steps)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

---

## Prerequisites

Before installing hai-sh, ensure your system meets these requirements:

### Required

- **Python**: Version 3.9 or higher
  ```bash
  python3 --version  # Should show 3.9.0 or higher
  ```

- **pip**: Python package installer (usually included with Python)
  ```bash
  pip3 --version
  ```

- **Shell**: Bash 4.0+ or Zsh 5.0+
  ```bash
  bash --version  # or zsh --version
  ```

### Optional

- **LLM Provider Access**: At least one of:
  - **OpenAI API Key** (for GPT models)
  - **Ollama** (for local models - recommended for cost-effective usage)
    ```bash
    # Check if Ollama is installed
    ollama --version
    ```
  - **Anthropic API Key** (for Claude models)

### Operating Systems

- **Linux**: Tested on Ubuntu 20.04+, Debian 11+, Fedora 35+
- **macOS**: Tested on macOS 11+ (Big Sur and later)
- **Windows**: WSL2 (Windows Subsystem for Linux)

---

## Installation Methods

### Install via pipx (Recommended for CLI Tools)

**pipx** is the recommended way to install Python CLI applications. It installs each application in an isolated environment while making the commands globally available.

#### 1. Install pipx (if not already installed)

```bash
# Linux
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# macOS
brew install pipx
pipx ensurepath

# Verify installation
pipx --version
```

#### 2. Install hai-sh via pipx

**Note:** hai-sh is not yet published to PyPI. Until then, use one of these methods:

```bash
# Install from GitHub (recommended for pre-release)
pipx install git+https://github.com/frankbria/hai-sh.git

# Or install from local directory
git clone https://github.com/frankbria/hai-sh.git
cd hai-sh
pipx install .
```

Once published to PyPI, you'll be able to install with:
```bash
pipx install hai-sh  # Available after PyPI publication
```

#### 3. Install Shell Integration

```bash
hai-install-shell
```

This will copy shell integration files to `~/.hai/` and show you the next steps.

#### 4. Add to Shell Configuration

**For Bash:**
```bash
echo 'source ~/.hai/bash_integration.sh' >> ~/.bashrc
source ~/.bashrc
```

**For Zsh:**
```bash
echo 'source ~/.hai/zsh_integration.sh' >> ~/.zshrc
source ~/.zshrc
```

#### 5. Verify Installation

```bash
hai --version
```

**Why pipx?**
- ✅ Isolated environment (no dependency conflicts)
- ✅ Global command availability
- ✅ Easy updates: `pipx upgrade hai-sh`
- ✅ Clean uninstall: `pipx uninstall hai-sh`

---

### Install via pip (Alternative Method)

This method works but may cause dependency conflicts if you have other Python packages installed.

#### 1. Install from PyPI

**Note:** hai-sh is not yet published to PyPI. Until then, use one of these methods:

```bash
# Install from GitHub
pip3 install git+https://github.com/frankbria/hai-sh.git

# Or install from local directory
git clone https://github.com/frankbria/hai-sh.git
cd hai-sh
pip3 install .
```

Once published to PyPI, you'll be able to install with:
```bash
pip3 install hai-sh  # Available after PyPI publication
```

#### 2. Verify Installation

```bash
hai --version
```

You should see output like:
```
hai version 0.0.1
```

#### 3. Check Installation Location

```bash
which hai
```

If the command is not found, you may need to add Python's bin directory to your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Reload shell configuration
source ~/.bashrc  # or source ~/.zshrc
```

---

### Install for Development

For contributors or users who want the latest development version.

#### 1. Clone the Repository

```bash
git clone https://github.com/frankbria/hai-sh.git
cd hai-sh
```

#### 2. Set Up Python Environment

Using `uv` (recommended):

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS

# Install dependencies
uv sync
```

Using standard `venv`:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS

# Install package in editable mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

#### 3. Verify Development Installation

```bash
# Run tests
pytest

# Check coverage
pytest --cov=hai_sh

# Run hai from development environment
hai --version
```

---

## Shell Integration Setup

Shell integration enables the `Ctrl+X Ctrl+H` keyboard shortcut and `@hai` prefix detection.

### Bash Setup

#### Automatic Installation

```bash
# Run the installation helper (installs both bash and zsh)
hai-install-shell

# Then source the integration script
source ~/.hai/bash_integration.sh
```

#### Manual Installation

1. Copy the integration script to your hai directory:
   ```bash
   mkdir -p ~/.hai
   cp $(python3 -c "import hai_sh; import os; print(os.path.dirname(hai_sh.__file__)))/integrations/bash_integration.sh ~/.hai/
   ```

2. Add to your `~/.bashrc`:
   ```bash
   echo 'source ~/.hai/bash_integration.sh' >> ~/.bashrc
   ```

3. Reload your shell:
   ```bash
   source ~/.bashrc
   ```

#### Customize Key Binding

By default, hai uses `Ctrl+X Ctrl+H`. To customize:

```bash
# Add to ~/.bashrc BEFORE sourcing the integration script
export HAI_KEY_BINDING="\C-h"  # Use Ctrl+H
# or
export HAI_KEY_BINDING="\eh"   # Use Alt+H

source ~/.hai/bash_integration.sh
```

#### Test Bash Integration

```bash
# Test that integration is working
_hai_test_integration
```

You should see:
```
✓ hai command found: /path/to/hai
✓ _hai_trigger function defined
✓ Key binding: Ctrl+X Ctrl+H

Integration test passed!
```

---

### Zsh Setup

#### Automatic Installation

```bash
# Run the installation helper (installs both bash and zsh)
hai-install-shell

# Then source the integration script
source ~/.hai/zsh_integration.sh
```

#### Manual Installation

1. Copy the integration script:
   ```bash
   mkdir -p ~/.hai
   cp $(python3 -c "import hai_sh; import os; print(os.path.dirname(hai_sh.__file__))"/integrations/zsh_integration.sh ~/.hai/
   ```

2. Add to your `~/.zshrc`:
   ```bash
   echo 'source ~/.hai/zsh_integration.sh' >> ~/.zshrc
   ```

3. Reload your shell:
   ```bash
   source ~/.zshrc
   ```

#### Customize Key Binding

```bash
# Add to ~/.zshrc BEFORE sourcing the integration script
export HAI_KEY_BINDING="^H"  # Use Ctrl+H
# or
export HAI_KEY_BINDING="^[h"  # Use Alt+H

source ~/.hai/zsh_integration.sh
```

#### Test Zsh Integration

```bash
# Test that integration is working
_hai_test_integration
```

---

## First-Run Configuration

On first run, hai will create a configuration directory and prompt for setup.

### Initialize Configuration

```bash
# Run hai for the first time
hai --help
```

This creates:
```
~/.hai/
├── config.yml              # Main configuration file
├── bash_integration.sh     # Bash keyboard shortcut
└── zsh_integration.sh      # Zsh keyboard shortcut
```

### Configure LLM Provider

Edit `~/.hai/config.yml`:

```yaml
# Choose your default provider
provider: "ollama"  # Options: openai, anthropic, ollama, local

# Provider-specific configuration
providers:
  # OpenAI Configuration
  openai:
    api_key: "sk-..."           # Your OpenAI API key
    model: "gpt-4o-mini"        # Model to use

  # Anthropic Configuration
  anthropic:
    api_key: "sk-ant-..."       # Your Anthropic API key
    model: "claude-sonnet-4-5"  # Model to use

  # Ollama Configuration (Local)
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2"           # Model to use
    # Install models: ollama pull llama3.2

# Context Settings
context:
  include_history: true         # Include command history
  include_git_state: true       # Include git repository state
  include_env: true             # Include environment variables
  max_history_lines: 20         # Max history lines to include

# Output Settings
output:
  color: "auto"                 # Options: auto, always, never
  format: "dual-layer"          # Options: dual-layer, conversation-only, execution-only
  max_output_lines: 100         # Truncate long output
```

### Set API Keys (if using OpenAI or Anthropic)

#### Option 1: Environment Variables (Recommended)

```bash
# Add to ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

#### Option 2: Configuration File

Edit `~/.hai/config.yml` and add your API keys directly (less secure):

```yaml
providers:
  openai:
    api_key: "sk-your-key-here"
```

### Set Up Ollama (Recommended for Local Use)

Ollama provides free, local LLM access:

1. **Install Ollama**:
   ```bash
   # Linux
   curl -fsSL https://ollama.com/install.sh | sh

   # macOS
   brew install ollama
   ```

2. **Start Ollama**:
   ```bash
   ollama serve
   ```

3. **Pull a Model**:
   ```bash
   ollama pull llama3.2
   # or
   ollama pull mistral
   ```

4. **Test Ollama**:
   ```bash
   ollama list  # Should show installed models
   ```

5. **Configure hai to use Ollama**:
   ```yaml
   # In ~/.hai/config.yml
   provider: "ollama"

   providers:
     ollama:
       base_url: "http://localhost:11434"
       model: "llama3.2"
   ```

---

## Verification Steps

After installation, verify everything is working:

### 1. Check hai Command

```bash
hai --version
```

Expected output:
```
hai version 0.0.1
```

### 2. Test Help System

```bash
hai --help
```

You should see comprehensive help text with examples.

### 3. Test Basic Query

```bash
hai "show me the current directory"
```

Expected: hai generates a command suggestion.

### 4. Test @hai Prefix

```bash
@hai list files in current directory
```

### 5. Test Keyboard Shortcut

1. Type in your terminal:
   ```
   show me large files
   ```

2. Press `Ctrl+X Ctrl+H` (or your custom binding)

3. hai should process the query and suggest a command

### 6. Verify Configuration

```bash
cat ~/.hai/config.yml
```

Ensure your provider settings are correct.

### 7. Test LLM Connection

```bash
# For OpenAI
hai "test connection"

# For Ollama (ensure ollama serve is running)
ollama list
hai "test connection"
```

### 8. Run Integration Tests (Development Only)

```bash
cd hai-sh
pytest tests/integration/
```

All tests should pass.

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: `hai: command not found`

**Problem**: Python bin directory not in PATH

**Solution**:
```bash
# Find where hai is installed
pip3 show hai-sh | grep Location

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc
```

---

#### Issue: `ModuleNotFoundError: No module named 'hai_sh'`

**Problem**: Package not installed correctly

**Solution**:
```bash
# Reinstall
pip3 uninstall hai-sh
pip3 install hai-sh

# Or for development
cd hai-sh
pip3 install -e .
```

---

#### Issue: Keyboard shortcut not working

**Problem**: Shell integration not loaded

**Solution**:
```bash
# Check if integration is sourced
type _hai_trigger

# If not found, add to shell config
echo 'source ~/.hai/bash_integration.sh' >> ~/.bashrc
source ~/.bashrc

# Test integration
_hai_test_integration
```

---

#### Issue: `Ctrl+H` conflicts with backspace

**Problem**: Terminal emulator captures `Ctrl+H`

**Solution**:
Use a different key binding:
```bash
# Add to ~/.bashrc BEFORE sourcing integration
export HAI_KEY_BINDING="\C-x\C-h"  # Use Ctrl+X Ctrl+H
source ~/.hai/bash_integration.sh
```

---

#### Issue: OpenAI API errors

**Problem**: Invalid or missing API key

**Solution**:
```bash
# Check API key is set
echo $OPENAI_API_KEY

# If not set, add to ~/.bashrc
export OPENAI_API_KEY="sk-..."

# Or add to ~/.hai/config.yml
# providers:
#   openai:
#     api_key: "sk-..."

# Verify connection
hai "test api connection"
```

---

#### Issue: Ollama connection refused

**Problem**: Ollama server not running

**Solution**:
```bash
# Start Ollama server
ollama serve

# In another terminal, test
ollama list

# Pull a model if needed
ollama pull llama3.2

# Test hai with Ollama
hai "test ollama connection"
```

---

#### Issue: `Permission denied` errors

**Problem**: Installation in system directories without sudo

**Solution**:
```bash
# Install to user directory
pip3 install --user hai-sh

# Or use virtual environment
python3 -m venv ~/.hai-venv
source ~/.hai-venv/bin/activate
pip install hai-sh
```

---

#### Issue: Slow response times

**Problem**: Using large models or slow network

**Solution**:
```bash
# Switch to faster model in ~/.hai/config.yml
providers:
  openai:
    model: "gpt-4o-mini"  # Faster than gpt-4

  ollama:
    model: "mistral"  # Smaller than llama3.2

# Or use local Ollama for instant responses
provider: "ollama"
```

---

#### Issue: Configuration file not found

**Problem**: First-run initialization didn't complete

**Solution**:
```bash
# Manually create configuration directory
mkdir -p ~/.hai

# Run hai to trigger initialization
hai --help

# If still not created, copy template
python3 -c "
import hai_sh.init as init
init.init_hai_directory()
"
```

---

#### Issue: Tests failing during development

**Problem**: Missing dependencies or environment issues

**Solution**:
```bash
# Install all dev dependencies
pip install -e ".[dev]"

# Run tests with verbose output
pytest -v

# Check specific test
pytest tests/integration/test_realistic_use_cases.py -v

# Clean and reinstall
pip uninstall hai-sh
pip install -e .
```

---

#### Issue: `No color` environment affecting output

**Problem**: `NO_COLOR` environment variable set

**Solution**:
```bash
# Check if NO_COLOR is set
echo $NO_COLOR

# Unset if you want colors
unset NO_COLOR

# Or force colors in config
# output:
#   color: "always"
```

---

### Getting Help

If you encounter issues not covered here:

1. **Check GitHub Issues**: https://github.com/frankbria/hai-sh/issues
2. **Search Discussions**: https://github.com/frankbria/hai-sh/discussions
3. **Open a New Issue**: Include:
   - hai version (`hai --version`)
   - Python version (`python3 --version`)
   - Shell and version (`bash --version` or `zsh --version`)
   - Operating system
   - Error messages (full output)
   - Configuration file (`~/.hai/config.yml`)

4. **Enable Debug Mode**:
   ```bash
   hai --debug "your query"
   ```
   This provides detailed error information.

---

## Uninstallation

### Remove hai Package

```bash
# If installed via pip
pip3 uninstall hai-sh

# If installed for development
cd hai-sh
pip3 uninstall hai-sh
```

### Remove Shell Integration

#### Bash

```bash
# Use uninstall helper (if available)
_hai_uninstall_integration

# Or manually remove from ~/.bashrc
# Remove these lines:
# # hai-sh integration
# source ~/.hai/bash_integration.sh
```

#### Zsh

```bash
# Use uninstall helper (if available)
_hai_uninstall_integration

# Or manually remove from ~/.zshrc
# Remove these lines:
# # hai-sh integration
# source ~/.hai/zsh_integration.sh
```

### Remove Configuration Files

```bash
# Remove hai directory (THIS DELETES YOUR CONFIGURATION!)
rm -rf ~/.hai

# Or backup before removing
mv ~/.hai ~/.hai.backup.$(date +%Y%m%d)
```

### Verify Removal

```bash
# Should show "command not found"
which hai
hai --version

# Should be removed
ls ~/.hai
```

---

## Next Steps

After successful installation:

1. **Read the Usage Guide**: See [README.md](./README.md) for usage examples
2. **Configure Your Provider**: Set up OpenAI, Anthropic, or Ollama
3. **Try Example Queries**: Test with the examples in the README
4. **Customize Key Bindings**: Adjust keyboard shortcuts to your preference
5. **Join the Community**: Check out [Discussions](https://github.com/frankbria/hai-sh/discussions)

---

**Installation complete!** 🎉

Say "hai" to your new terminal assistant! 👋

For issues or questions, visit: https://github.com/frankbria/hai-sh/issues
