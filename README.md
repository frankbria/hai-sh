# hai

**A friendly shell assistant powered by LLMs**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/badge/pypi-v0.1.2-blue.svg)](https://pypi.org/project/hai-sh/)
[![Tests](https://img.shields.io/badge/tests-622%20passing-brightgreen.svg)](https://github.com/frankbria/hai-sh)
[![Coverage](https://img.shields.io/badge/coverage-82%25-brightgreen.svg)](https://github.com/frankbria/hai-sh)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`hai` (pronounce like "hi") is a thin, context-aware wrapper around bash that brings natural language command generation directly to your terminal. Stop context-switching to look up git commands, bash syntax, or flags—just ask hai.

## 🎯 Quick Start

```bash
# Install (pipx recommended)
pipx install hai-sh
hai-install-shell

# Use directly
hai "show me files modified in the last 24 hours"

# Or with @hai prefix
@hai commit just README.md to main, I'm on feature-branch

# Or with keyboard shortcut - type your query then press Ctrl+X Ctrl+H
find large files in home directory
# Press Ctrl+X Ctrl+H
```

**Example output (auto-execute with high confidence):**
```
$ find . -type f -mtime -1
./README.md
./src/app.py
./tests/test_app.py

[Explanation: I'll search for files modified in the last 24 hours using find.] (90%)
```

Commands with high confidence (≥85%) execute immediately. The explanation is shown collapsed after execution.

## ✨ Features

### Core Capabilities

- **🎯 Natural Language Interface**: Just describe what you want in plain English
- **💬 Dual Mode Operation**:
  - **Command Mode**: Generate and execute bash commands
  - **Question Mode**: Get answers to your terminal/bash questions without executing anything
- **⚡ Smart Auto-Execute**: High-confidence commands (≥85%) run immediately without confirmation
- **🔄 Dual-Layer Output**: See both the AI's reasoning and the actual command
- **🌍 Context-Aware**: Automatically includes current directory, git state, and environment
- **🔒 Privacy-First**: Supports local Ollama models—no API costs, data stays private
- **⌨️ Multiple Invocation Methods**:
  - Direct command: `hai "query"`
  - @hai prefix: `@hai query`
  - Keyboard shortcut: `Ctrl+X Ctrl+H` (customizable)
- **🎨 Smart Output Formatting**: ANSI colors with auto-detection for pipes and terminals

### LLM Provider Support

- **OpenAI**: GPT-4, GPT-4o, GPT-4o-mini, GPT-3.5-turbo
- **Anthropic**: Claude Opus 4.5, Claude Sonnet 4.5
- **Ollama**: Local models (llama3.2, mistral, codellama, etc.) - **recommended for daily use**
- **Local Models**: Custom GGUF model support

### Shell Integration

- **Bash**: Keyboard shortcuts and @hai prefix detection
- **Zsh**: Full feature parity with bash
- **Auto-completion**: Future roadmap item

### Advanced Features

- **Confidence Scoring**: Visual indicators show AI confidence (0-100%)
- **Multi-step Commands**: Handles complex workflows with `&&` chaining
- **Environment Preservation**: Safe environment variable handling
- **Git Integration**: Context-aware git operations
- **Comprehensive Testing**: 622 tests, 82% coverage

## 🚀 Status

**Current Version:** v0.1.2 (Published on PyPI)

hai follows an agile development approach with frequent version increments.

### What's New (Updated: 2024-12-20)

**v0.1.0 PyPI Release:**
- ✅ Published to PyPI - install with `pipx install hai-sh`
- ✅ 622 tests passing (100% pass rate)
- ✅ Shell integration with Ctrl+X Ctrl+H keyboard shortcut
- ✅ Three LLM providers: OpenAI, Anthropic, Ollama
- ✅ Complete installation guide ([INSTALL.md](./INSTALL.md))
- ✅ Comprehensive configuration guide ([CONFIGURATION.md](./CONFIGURATION.md))
- ✅ 20+ usage examples and tutorial ([USAGE.md](./USAGE.md))
- ✅ Integration test suite with realistic use cases
- ✅ Error messages and help system
- ✅ ANSI color support with TTY detection
- ✅ Dual-layer output formatter

**Core Features (v0.1):**
- ✅ Command execution engine
- ✅ Context gathering (cwd, git, env)
- ✅ LLM providers (OpenAI, Anthropic, Ollama)
- ✅ Shell integration (bash, zsh)
- ✅ Configuration system
- ✅ Output formatting

### Roadmap

- **v0.1** ✅ - Proof of Concept: Basic invocation, LLM providers, dual-layer output
- **v0.2** 🚧 - Enhanced Context: History, session context, hybrid memory model
- **v0.3** ✅ - Smart Execution: Confidence scoring, auto-execute vs. confirm
- **v0.4** 📋 - Permissions Framework: Granular control over command execution
- **v0.5** 📋 - Error Handling: Automatic retry with model upgrade for debugging
- **v1.0** 📋 - Production Ready: Polished, tested, documented, secure

See [ROADMAP.md](./ROADMAP.md) for complete development plan.

## 📦 Installation

### Prerequisites

- **Python**: 3.9 or higher
- **Shell**: Bash 4.0+ or Zsh 5.0+
- **LLM Provider**: OpenAI API key, Anthropic API key, or Ollama (local)

### Quick Install

```bash
# Install via pipx (recommended)
pipx install hai-sh
hai-install-shell  # Install shell integration

# Or via pip
pip install hai-sh

# Verify installation
hai --version
```

### Development Install

```bash
# Clone repository
git clone https://github.com/frankbria/hai-sh.git
cd hai-sh

# Using uv (recommended)
uv venv
source .venv/bin/activate
uv sync

# Run tests
pytest
```

### Shell Integration Setup

**For Bash:**
```bash
# Add to ~/.bashrc
source ~/.hai/bash_integration.sh
```

**For Zsh:**
```bash
# Add to ~/.zshrc
source ~/.hai/zsh_integration.sh
```

**Reload your shell:**
```bash
source ~/.bashrc  # or ~/.zshrc
```

**📖 Full installation guide:** [INSTALL.md](./INSTALL.md)

## 🔧 Configuration

### Quick Setup

On first run, hai creates `~/.hai/config.yaml`:

```yaml
# Default: Use free local Ollama
provider: "ollama"

providers:
  # OpenAI (requires API key)
  openai:
    # Set OPENAI_API_KEY environment variable
    model: "gpt-4o-mini"

  # Anthropic (requires API key)
  anthropic:
    # Set ANTHROPIC_API_KEY environment variable
    model: "claude-sonnet-4-5"

  # Ollama (free, local)
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2"

context:
  include_history: true
  include_git_state: true
  include_env_vars: true

output:
  show_conversation: true
  use_colors: true

execution:
  auto_execute: true           # Auto-run high-confidence commands
  auto_execute_threshold: 85   # Minimum confidence for auto-execute (0-100)
  show_explanation: collapsed  # collapsed, expanded, or hidden
  require_confirmation: false  # Always require confirmation if true
```

### Setting Up Ollama (Recommended)

**Why Ollama?**
- ✅ Free (no API costs)
- ✅ Private (data stays local)
- ✅ Fast (no network latency)
- ✅ Offline capable

**Install Ollama:**
```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Start server
ollama serve

# Pull model
ollama pull llama3.2
```

### Setting Up OpenAI

```bash
# Add to ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="sk-..."

# Update config
provider: "openai"
```

### Execution Behavior

Control how hai executes commands:

```yaml
execution:
  # Enable/disable auto-execution (default: true)
  auto_execute: true

  # Minimum confidence to auto-execute (default: 85)
  auto_execute_threshold: 85

  # How to show explanation: collapsed, expanded, hidden (default: collapsed)
  show_explanation: collapsed

  # Always require confirmation, overrides auto_execute (default: false)
  require_confirmation: false
```

**Example configurations:**

```yaml
# Conservative: Always ask before executing
execution:
  require_confirmation: true
```

```yaml
# Fast: Lower threshold, hide explanations
execution:
  auto_execute_threshold: 70
  show_explanation: hidden
```

```yaml
# Learning: Always show full explanations
execution:
  show_explanation: expanded
```

**📖 Full configuration guide:** [CONFIGURATION.md](./CONFIGURATION.md)

## 📖 Usage

### Invocation Methods

**1. Direct Command (Best for learning)**
```bash
hai "find large files"
hai "show git status"
hai "what's taking up disk space?"
```

**2. @hai Prefix (Best for daily use)**
```bash
@hai list Python files modified today
@hai commit all changes with message 'Update docs'
```

**3. Keyboard Shortcut (Best for speed)**
```bash
# 1. Type your query
show me uncommitted git changes

# 2. Press Ctrl+X Ctrl+H
# 3. hai processes and suggests command
```

### CLI Flags

```bash
# Force auto-execute (skip confirmation)
hai -y "list all files"
hai --yes "show disk usage"

# Force confirmation (even for high-confidence)
hai --confirm "delete temp files"

# Just show suggestion without executing
hai --suggest-only "find large files"

# Disable colors
hai --no-color "show status"

# Debug mode
hai --debug "complex query"
```

### Example Queries

**File Operations:**
```bash
hai "find files larger than 100MB"
hai "show files modified in the last 24 hours"
hai "find all TypeScript files that import React"
```

**Git Workflows:**
```bash
hai "show uncommitted changes"
hai "create branch feature/auth and switch to it"
hai "show me what changed in the last commit"
```

**System Information:**
```bash
hai "what's using the most disk space?"
hai "show CPU and memory usage"
hai "find processes using port 8080"
```

**Development Tasks:**
```bash
hai "install Python dependencies from requirements.txt"
hai "run pytest with coverage"
hai "build Docker image and tag as latest"
```

**Asking Questions (No Command Execution):**
```bash
hai "What's the difference between ls -la and ls -lah?"
hai "How does git rebase work?"
hai "When should I use grep vs awk vs sed?"
hai "Explain what the -R flag does in chmod"
hai "Why would I use git merge instead of git rebase?"
```

**📖 20+ examples and tutorials:** [USAGE.md](./USAGE.md)

## 🎯 Understanding Execution Modes

hai operates in two modes automatically based on confidence:

### Auto-Execute Mode (High Confidence ≥85%)

When hai is confident, commands run immediately:

```bash
$ hai "how many files in this directory"
```
```
$ ls | wc -l
42

[Explanation: I'll count the files in the current directory using ls and wc.] (92%)
```

The command executes first, then the explanation appears collapsed below.

### Confirmation Mode (Lower Confidence <85%)

When confidence is lower, or with `--confirm` flag, hai asks before executing:

```bash
$ hai --confirm "find large files"
```
```
I'll search for large files in your home directory and sort them by size.

Command: find ~ -type f -size +100M -exec du -h {} + | sort -rh | head -20
Confidence: 78%

Execute this command? [y/N/e(dit)]:
```

### Question Mode (Informational Questions)

When you ask a question, hai provides a direct answer without generating a command:

```bash
$ hai "What's the difference between rm -rf and rm -r?"
```

```
Both commands remove directories recursively (-r flag), but there's an
important difference in the -f flag:

- rm -r: Recursive removal, prompts for confirmation on write-protected files
- rm -rf: Recursive removal with -f (force), suppresses all prompts

⚠️ Use rm -rf with extreme caution! It will delete everything without asking.

Confidence: 98% [█████████·]
```

**Benefits:**
- **Speed**: High-confidence commands run immediately without interruption
- **Safety**: Lower-confidence commands require confirmation
- **Learning**: Collapsed explanations available when you need them
- **Control**: Use `-y` to always auto-execute, `--confirm` to always ask
- **Knowledge**: Get answers without execution (question mode)

## 🤝 Contributing

Contributions welcome! This project is in active development.

### Development Setup

```bash
git clone https://github.com/frankbria/hai-sh.git
cd hai-sh
uv venv && source .venv/bin/activate
uv sync
pytest
```

### Running Tests

```bash
# Run all tests (unit + Ollama integration if available)
pytest

# Run with coverage
pytest --cov=hai_sh --cov-report=html

# Run only unit tests (fast, no external dependencies)
pytest -m unit

# Run only integration tests
pytest -m integration
```

#### Provider-Specific Testing

```bash
# Test OpenAI provider (requires API key)
TEST_OPENAI=1 OPENAI_API_KEY=sk-... pytest -m "integration and openai"

# Test Anthropic provider (requires API key)
TEST_ANTHROPIC=1 ANTHROPIC_API_KEY=sk-ant-... pytest -m "integration and anthropic"

# Test Ollama provider (requires Ollama running locally)
pytest -m "integration and ollama"

# Test all providers simultaneously
TEST_OPENAI=1 TEST_ANTHROPIC=1 pytest -m integration
```

**📖 For detailed testing instructions, see [tests/TESTING.md](tests/TESTING.md)**

### Code Quality

```bash
# Format code
black hai_sh/ tests/

# Lint
ruff hai_sh/ tests/
```

### Current Test Status

- **Total Tests**: 600+ (all passing ✅)
- **Coverage**: 92%+
- **Unit Tests**: 560+
- **Integration Tests**: 40+ (provider-specific + cross-provider)
- **Providers Tested**: OpenAI, Anthropic, Ollama

## 🎯 Design Philosophy

1. **Seamless Integration** - Feel like a natural extension of bash
2. **Local-First** - Support local/Ollama models for cost-effective daily use
3. **Safety** - Clear permission boundaries, confidence-based execution
4. **Transparency** - Always show what's happening (thinking + doing)
5. **Agile Evolution** - Ship working increments frequently

## 📚 Documentation

- **[INSTALL.md](./INSTALL.md)** - Complete installation guide (792 lines)
  - Prerequisites and system requirements
  - pip and development installation
  - Shell integration (bash/zsh)
  - First-run configuration
  - Troubleshooting guide

- **[CONFIGURATION.md](./CONFIGURATION.md)** - Configuration reference (1272 lines)
  - All configuration options explained
  - Provider setup (OpenAI, Anthropic, Ollama)
  - Context and output settings
  - 7 example configurations
  - Security best practices

- **[USAGE.md](./USAGE.md)** - Usage guide and tutorial (1298 lines)
  - Getting started tutorial
  - 20+ example queries with output
  - Common workflows
  - Tips and best practices
  - Advanced usage patterns

- **[PRD.md](./PRD.md)** - Product requirements and vision
- **[ROADMAP.md](./ROADMAP.md)** - Development roadmap and milestones

## 🔒 Security & Privacy

### API Key Security

**✅ DO:**
- Store API keys in environment variables
- Use `chmod 600` on config files
- Add config files to `.gitignore`

**❌ DON'T:**
- Commit API keys to git
- Share config files with credentials
- Use API keys in public repositories

### Privacy-First Options

Use **Ollama** for complete privacy:
```yaml
provider: "ollama"  # All data stays on your machine
context:
  include_history: false    # Don't send command history
  include_env_vars: false   # Don't send environment
```

## 🧪 Testing

hai includes comprehensive test coverage:

### Test Categories

- **Unit Tests** (560): Core functionality, edge cases, error handling
- **Integration Tests** (16): End-to-end workflows with realistic use cases
  - Files modified in last 24 hours
  - TypeScript files importing React
  - Disk space analysis
  - Python venv setup
  - Git workflows

### Test Infrastructure

- **Framework**: pytest with pytest-cov
- **Mocking**: MockLLMProvider for consistent testing
- **Coverage**: 92.18% code coverage
- **CI/CD**: Ready (workflows TBD)

## 🐛 Troubleshooting

### Common Issues

**Command not found:**
```bash
# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

**Keyboard shortcut not working:**
```bash
# Check integration
_hai_test_integration

# Reload shell
source ~/.bashrc
```

**Ollama connection refused:**
```bash
# Start Ollama server
ollama serve

# Pull model
ollama pull llama3.2
```

**📖 Full troubleshooting guide:** [INSTALL.md](./INSTALL.md#troubleshooting)

## 📝 License

This project is licensed under the **GNU Affero General Public License v3.0** - see [LICENSE](./LICENSE) for details.

## 🔗 Links

- **GitHub**: https://github.com/frankbria/hai-sh
- **Issues**: https://github.com/frankbria/hai-sh/issues
- **Discussions**: https://github.com/frankbria/hai-sh/discussions
- **PyPI** (coming soon): https://pypi.org/project/hai-sh/

## 🙏 Inspiration & Credits

- Built with a similar agile approach to [parallel-cc](https://github.com/frankbria/parallel-cc)
- Inspired by the philosophy of making AI accessible and private
- Thanks to the open-source community for tools like Ollama, pytest, and pydantic

## 📊 Project Stats

- **Lines of Code**: ~10,000+
- **Tests**: 576 (100% passing)
- **Coverage**: 92.18%
- **Documentation**: 3,362 lines (INSTALL, CONFIGURATION, USAGE)
- **Python Version**: 3.9+
- **License**: AGPL-3.0

---

**Status**: 🚧 Under Active Development | v0.1 Pre-release

Say "hai" to your new shell assistant! 👋

**Ready to get started?** → [INSTALL.md](./INSTALL.md)
