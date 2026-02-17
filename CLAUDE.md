# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**hai** (pronounce like "hi") is an AI-powered terminal assistant that translates natural language into bash commands. It's a thin, context-aware wrapper around bash providing dual-layer output (conversation + execution) via LLM providers (OpenAI, Anthropic, Ollama).

**Current Status**: v0.1.4 (1147 tests, 85% coverage)

## Development Commands

### Environment Setup
```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate
uv sync
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=hai_sh

# Run specific test categories
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
pytest -m unit              # Using markers
pytest -m integration

# Run specific test file
pytest tests/unit/test_config.py

# Run specific test
pytest tests/unit/test_config.py::test_load_config_success

# Run with debug output
pytest -v -s
```

### Code Quality
```bash
# Format code
black hai_sh/ tests/

# Lint
ruff hai_sh/ tests/

# Check formatting without changes
black --check hai_sh/ tests/
```

### Build & Distribution
```bash
# Build distribution packages
python -m build

# Install locally for testing
pip install -e .

# Upload to PyPI (requires .pypirc)
twine upload dist/*
```

## Architecture

### Component Overview

The codebase follows a modular architecture with clear separation of concerns:

```
hai_sh/
├── __main__.py          # CLI entry point (argparse)
├── app_mode.py          # Application mode detection & routing
├── config.py            # YAML config loading & validation (Pydantic schemas)
├── context.py           # Context gathering (cwd, git state, env vars)
├── executor.py          # Command execution (subprocess, pipelines)
├── formatter.py         # Dual-layer output formatting
├── gum.py               # Gum TUI integration for enhanced terminal UX
├── init.py              # ~/.hai directory initialization
├── input_detector.py    # Input parsing (@hai prefix, query extraction)
├── install_shell.py     # Shell integration installer
├── memory.py            # Three-tier context memory system
├── output.py            # ANSI color handling, TTY detection
├── privacy.py           # Privacy warnings for cloud LLM providers
├── prompt.py            # LLM prompt building & response parsing
├── provider_manager.py  # Provider lifecycle management
├── rate_limit.py        # Token bucket rate limiting
├── redaction.py         # Sensitive data output redaction
├── schema.py            # Pydantic data models
├── theme.py             # Terminal theme & color definitions
├── tui.py               # Textual/Rich TUI application
├── providers/
│   ├── base.py          # BaseLLMProvider abstract class
│   ├── openai.py        # OpenAI provider implementation
│   ├── ollama.py        # Ollama provider implementation
│   └── registry.py      # Provider factory & registration
└── integrations/
    ├── bash_integration.sh    # Bash keyboard shortcut (Ctrl+X Ctrl+H)
    └── zsh_integration.sh     # Zsh keyboard shortcut
```

### Key Architectural Patterns

**1. Provider Pattern (LLM Abstraction)**
- All LLM providers inherit from `BaseLLMProvider` (providers/base.py)
- Registry pattern in `providers/registry.py` for provider discovery
- Add new providers by: (1) subclass BaseLLMProvider, (2) register in registry
- Example: OpenAI and Ollama providers follow identical interface

**2. Context Pipeline**
- Context gathering is modular: cwd → git → env vars
- Each context module exports both raw getters (`get_X_context`) and formatters (`format_X_context`)
- Context is injected into LLM system prompt via `prompt.build_system_prompt()`

**3. Dual-Layer Output**
- **Conversation Layer**: LLM reasoning/explanation (what it's thinking)
- **Execution Layer**: Actual bash commands + output (what it's doing)
- Formatted via `formatter.py` with ANSI color support
- TTY detection in `output.py` auto-disables colors for pipes

**4. Shell Integration Strategy**
- Shell scripts (bash_integration.sh, zsh_integration.sh) installed to ~/.hai/
- Keyboard shortcut (Ctrl+X Ctrl+H) reads current line, sends to `hai`
- @hai prefix detection for inline invocation
- Shell scripts are data files, not code - installed via package_data in pyproject.toml

**5. Configuration System**
- YAML config in ~/.hai/config.yaml
- Pydantic models in `schema.py` for validation
- Environment variable overrides (OPENAI_API_KEY, HAI_CONFIG, NO_COLOR)
- Provider-specific settings nested under `providers:` key

### Data Flow

```
User Input → Input Detector → Context Gatherer → Prompt Builder → LLM Provider
                                                                        ↓
User ← Output Formatter ← Executor ← Response Parser ← LLM Response
```

### Testing Strategy

**Unit Tests (1073 tests)**
- Each module has corresponding test_*.py in tests/unit/
- MockLLMProvider in tests/conftest.py for consistent testing
- Fixtures for config, context, providers in tests/conftest.py

**Integration Tests (74 tests)**
- End-to-end workflows in tests/integration/
- Test realistic use cases: file operations, git workflows, system queries
- Provider-specific tests (OpenAI, Anthropic, Ollama) and cross-provider scenarios
- Use MockLLMProvider to avoid API dependencies

**Coverage Requirements**
- Target: >85% coverage (currently 85%)
- Branch coverage enabled via pytest-cov
- Excluded: __repr__, raise NotImplementedError, TYPE_CHECKING blocks

## Key Implementation Details

### LLM Response Format
LLMs return JSON with:
```json
{
  "conversation": "Explanation of what will happen",
  "command": "actual bash command",
  "confidence": 85
}
```
Parsed by `prompt.parse_response()` with fallback extraction for malformed responses.

### Context Injection
System prompt includes:
- Current directory + file listings
- Git state (branch, dirty files, ahead/behind)
- Safe environment variables (filters out sensitive vars like API keys)
- Shell type (bash/zsh) and version

### Command Execution
- Uses subprocess.run() with configurable timeout
- Supports pipelines (&&, ||, |)
- Interactive mode for commands requiring stdin
- Shell syntax validation before execution

### Shell Integration Files
Located in `hai_sh/integrations/`:
- Installed to ~/.hai/ on first run or via `hai-install-shell`
- User sources these in .bashrc/.zshrc
- Keyboard shortcut is Ctrl+X Ctrl+H (customizable)
- @hai prefix detection for inline invocation

### Provider Registration
Add new providers in three steps:
1. Create subclass in `hai_sh/providers/new_provider.py`
2. Implement `generate()` method
3. Register in `providers/__init__.py` and `registry.py`

## Common Development Workflows

### Adding a New LLM Provider
1. Create `hai_sh/providers/new_provider.py` subclassing `BaseLLMProvider`
2. Implement `generate(prompt: str) -> dict` method
3. Add to `providers/__init__.py` exports
4. Register in `registry.py`
5. Add tests in `tests/unit/providers/test_new_provider.py`
6. Update config schema in `schema.py` if needed

### Modifying Output Format
- Conversation layer: Edit `formatter.format_conversation_layer()`
- Execution layer: Edit `formatter.format_execution_layer()`
- Color definitions: Edit `output.py` color constants
- Respect `NO_COLOR` and `FORCE_COLOR` environment variables

### Adding Context Sources
1. Add getter function in `context.py` (e.g., `get_X_context()`)
2. Add formatter function (e.g., `format_X_context()`)
3. Update `build_system_prompt()` in `prompt.py`
4. Add tests in `tests/unit/test_context.py`

### Updating Configuration Schema
1. Edit Pydantic models in `schema.py`
2. Update default config in `init.py`
3. Add validation in `config.py` if needed
4. Update tests in `tests/unit/test_config.py`
5. Document in CONFIGURATION.md

## Security Architecture (v0.1)

hai-sh implements **defense-in-depth** security with multiple protection layers:

### Command Validation (3 Layers)
1. **Injection Detection** - Blocks 18 injection patterns (`;`, `&&`, `$()`, `wget`, etc.)
2. **Allow-List (Primary)** - Only explicitly approved commands can execute
3. **Blacklist (Defense-in-Depth)** - Dangerous operation detection

### Data Protection
- **Sensitive Variable Filtering** - 40+ patterns (API_KEY, SECRET, TOKEN, AWS_, OPENAI, etc.)
- **Output Redaction** - 15 automatic redaction patterns (API keys, passwords, SSH keys, JWTs, etc.)
- **Privacy Warnings** - Alert users when using cloud LLM providers

### Rate Limiting
- **Token Bucket Algorithm** - 60 calls per 60 seconds (configurable)
- **Exponential Backoff** - Retry delays: 2s, 4s, 8s
- **Per-Provider Limits** - Separate quotas for OpenAI, Anthropic, Ollama

**Security Modules:**
- `hai_sh/rate_limit.py` - Rate limiting
- `hai_sh/redaction.py` - Output redaction
- `hai_sh/privacy.py` - Privacy warnings

## Important Constraints

### DO NOT
- **Add type hints to untested code** - Only add types when adding tests
- **Mock external services in integration tests** - Use real Ollama/mock providers
- **Break the dual-layer output** - Users rely on conversation vs. execution separation
- **Add dependencies without justification** - Keep the dependency tree minimal
- **Change shell integration without testing both bash and zsh**
- **Bypass security validation** - All commands must go through multi-layer validation
- **Disable output redaction** - Always redact sensitive data from command outputs

### DO
- **Write tests first** (TDD approach, target >85% coverage)
- **Preserve ANSI color handling** - Critical for user experience
- **Maintain provider interface compatibility** - BaseLLMProvider is the contract
- **Update documentation** when changing user-facing behavior
- **Test with both OpenAI and Ollama** providers when modifying LLM code
- **Run security validation tests** - Ensure command validation works correctly
- **Consider privacy implications** - Think about what data is sent to LLMs

## Deployment Notes

- Package is distributed via PyPI as `hai-sh`
- Shell integration requires manual sourcing in .bashrc/.zshrc
- Supports Linux and macOS (POSIX shells only)
- Requires Python 3.9+
- No sandbox integration in v0.1 (deferred to post-1.0)

## Related Documentation

- **README.md** - User-facing documentation (installation, usage, examples)
- **INSTALL.md** - Detailed installation guide (792 lines)
- **CONFIGURATION.md** - Configuration reference (1272 lines)
- **USAGE.md** - Usage examples and tutorial (1298 lines)
- **PRD.md** - Product requirements and vision
- **ROADMAP.md** - Development roadmap and future features
