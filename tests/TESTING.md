# Testing Guide for hai-sh

This guide explains the testing strategy for hai-sh and how to run different types of tests.

## Table of Contents

- [Testing Strategy](#testing-strategy)
- [Running Tests](#running-tests)
- [Provider-Specific Testing](#provider-specific-testing)
- [Cost Management](#cost-management)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Testing Strategy

hai-sh uses a multi-layered testing approach:

### 1. Unit Tests (560+ tests)

Fast, isolated tests for individual components using mocked dependencies.

- **Location**: `tests/unit/`
- **Coverage**: 92%+ branch coverage
- **Speed**: ~10 seconds
- **Dependencies**: None (all mocked)

### 2. Integration Tests - Mocked (16 tests)

End-to-end workflow tests using `MockLLMProvider` for consistency and speed.

- **Location**: `tests/integration/test_realistic_use_cases.py`
- **Purpose**: Fast regression testing of complete workflows
- **Dependencies**: None (mocked LLM provider)

### 3. Integration Tests - Real Providers

Comprehensive tests using actual LLM API calls to validate each provider independently.

- **Location**: `tests/integration/test_integration_*.py`
- **Purpose**: Validate real API behavior, catch integration issues
- **Dependencies**: Running provider services (Ollama/API keys)

#### Provider Test Files

- `test_integration_openai.py` - OpenAI provider tests
- `test_integration_anthropic.py` - Anthropic provider tests
- `test_integration_ollama.py` - Ollama provider tests
- `test_cross_provider.py` - Cross-provider consistency tests

## Running Tests

### Basic Test Commands

```bash
# Run all tests (unit + Ollama integration if available)
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=hai_sh --cov-report=html
```

### Running Tests by Category

```bash
# Run all unit tests
pytest tests/unit/

# Run all integration tests (including mocked)
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_config.py

# Run specific test
pytest tests/unit/test_config.py::test_load_config_success
```

## Provider-Specific Testing

### Testing OpenAI Provider

OpenAI tests require:
1. Valid `OPENAI_API_KEY` environment variable
2. `TEST_OPENAI=1` flag to prevent unexpected API costs

```bash
# Run OpenAI integration tests
TEST_OPENAI=1 OPENAI_API_KEY=sk-... pytest -m "integration and openai"

# Run specific OpenAI test class
TEST_OPENAI=1 OPENAI_API_KEY=sk-... pytest tests/integration/test_integration_openai.py::TestOpenAIBasicGeneration

# Run specific OpenAI test
TEST_OPENAI=1 OPENAI_API_KEY=sk-... pytest tests/integration/test_integration_openai.py::TestOpenAIBasicGeneration::test_basic_command_generation
```

**Default Models Tested:**
- `gpt-4o-mini` (primary, cost-effective)
- `o1-mini` (parameter compatibility testing)

### Testing Anthropic Provider

Anthropic tests require:
1. Valid `ANTHROPIC_API_KEY` environment variable
2. `TEST_ANTHROPIC=1` flag to prevent unexpected API costs

```bash
# Run Anthropic integration tests
TEST_ANTHROPIC=1 ANTHROPIC_API_KEY=sk-ant-... pytest -m "integration and anthropic"

# Run specific Anthropic test class
TEST_ANTHROPIC=1 ANTHROPIC_API_KEY=sk-ant-... pytest tests/integration/test_integration_anthropic.py::TestAnthropicBasicGeneration

# Run specific Anthropic test
TEST_ANTHROPIC=1 ANTHROPIC_API_KEY=sk-ant-... pytest tests/integration/test_integration_anthropic.py::TestAnthropicBasicGeneration::test_basic_command_generation
```

**Default Model Tested:**
- `claude-sonnet-4-5`

### Testing Ollama Provider

Ollama tests run automatically if Ollama is available (no API key required).

```bash
# Start Ollama (if not running)
ollama serve

# Pull required model (if needed)
ollama pull llama3.2

# Run Ollama integration tests
pytest -m "integration and ollama"

# Run specific Ollama test class
pytest tests/integration/test_integration_ollama.py::TestOllamaBasicGeneration

# Run specific Ollama test
pytest tests/integration/test_integration_ollama.py::TestOllamaBasicGeneration::test_basic_command_generation
```

**Default Model Tested:**
- `llama3.2` (8B parameters)

### Testing All Providers

Run tests across all available providers:

```bash
# Test all providers simultaneously
TEST_OPENAI=1 TEST_ANTHROPIC=1 \
OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... \
pytest -m integration

# Test cross-provider consistency (requires 2+ providers)
TEST_OPENAI=1 TEST_ANTHROPIC=1 \
OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... \
pytest tests/integration/test_cross_provider.py
```

## Cost Management

### Understanding API Costs

**OpenAI Provider:**
- `gpt-4o-mini`: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- Each test ~500 tokens total → ~$0.0003 per test
- Full OpenAI test suite (~30 tests) → ~$0.01

**Anthropic Provider:**
- `claude-sonnet-4-5`: ~$3.00 per 1M input tokens, ~$15.00 per 1M output tokens
- Each test ~500 tokens total → ~$0.005 per test
- Full Anthropic test suite (~25 tests) → ~$0.12

**Ollama Provider:**
- Free (runs locally)
- No API costs

### Cost Control Measures

1. **Explicit Opt-In**: API tests require both API key AND `TEST_*=1` flag
2. **Skip on Missing Credentials**: Tests auto-skip if requirements not met
3. **Minimal Test Suite**: Only essential scenarios tested
4. **Local-First**: Ollama tests run by default (free)

### Running Tests Without API Costs

```bash
# Run all tests except API-based ones
pytest -m "not requires_api_key"

# Run only unit tests (no API calls)
pytest -m unit

# Run only Ollama tests (free, local)
pytest -m "integration and ollama"

# Run integration tests with mocked providers (no API calls)
pytest tests/integration/test_realistic_use_cases.py
```

## CI/CD Integration

### Recommended CI/CD Strategy

**Default Pipeline (Every PR/Push):**
```bash
# Fast feedback loop - no API costs
pytest -m unit                           # Unit tests
pytest tests/integration/test_realistic_use_cases.py  # Mocked integration
pytest -m "integration and ollama"       # Ollama tests (if available)
```

**Extended Pipeline (On Main Branch or Manual Trigger):**
```bash
# Full validation with API providers (only when secrets available)
TEST_OPENAI=1 TEST_ANTHROPIC=1 pytest -m integration
```

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12', '3.13']
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest -m unit

  integration-tests-free:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: pytest tests/integration/test_realistic_use_cases.py
      # Ollama tests would require Ollama service setup

  integration-tests-api:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: |
          TEST_OPENAI=1 TEST_ANTHROPIC=1 pytest -m integration
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Troubleshooting

### Common Issues

#### OpenAI Tests Failing

**Problem**: `AuthenticationError: Invalid API key`

**Solution**:
```bash
# Verify API key is set correctly
echo $OPENAI_API_KEY

# Verify TEST_OPENAI flag is set
echo $TEST_OPENAI  # Should output: 1

# Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### Anthropic Tests Failing

**Problem**: `AuthenticationError: Invalid API key`

**Solution**:
```bash
# Verify API key format (should start with sk-ant-)
echo $ANTHROPIC_API_KEY

# Verify TEST_ANTHROPIC flag is set
echo $TEST_ANTHROPIC  # Should output: 1

# Test API key directly
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

#### Ollama Tests Skipped

**Problem**: `Ollama not running on localhost:11434`

**Solution**:
```bash
# Start Ollama service
ollama serve

# Verify Ollama is running
curl http://localhost:11434/api/tags

# Pull required model
ollama pull llama3.2

# Verify model is available
ollama list
```

#### Tests Timing Out

**Problem**: Tests exceed 60-second timeout

**Solution**:
```bash
# Check network connectivity
ping api.openai.com
ping api.anthropic.com

# Try with increased timeout (pytest.ini)
# Or use faster models:
# OpenAI: gpt-4o-mini instead of gpt-4
# Anthropic: claude-haiku instead of claude-sonnet
```

#### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'hai_sh'`

**Solution**:
```bash
# Install package in editable mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"

# Verify installation
python -c "import hai_sh; print(hai_sh.__file__)"
```

#### Coverage Not Generating

**Problem**: Coverage report not created

**Solution**:
```bash
# Ensure pytest-cov is installed
pip install pytest-cov

# Run with explicit coverage options
pytest --cov=hai_sh --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Getting Help

If you encounter issues not covered here:

1. Check existing GitHub issues: https://github.com/frankbria/hai-sh/issues
2. Run tests with verbose output: `pytest -vv`
3. Check test logs in CI/CD pipeline
4. Verify all dependencies are installed: `pip install -e ".[dev]"`

## Test Coverage Matrix

| Test Scenario | OpenAI | Anthropic | Ollama | Priority |
|--------------|--------|-----------|--------|----------|
| Basic Command Generation | ✅ | ✅ | ✅ | High |
| Question Mode | ✅ | ✅ | ✅ | High |
| High Confidence (>70%) | ✅ | ✅ | ✅ | High |
| Low Confidence (<60%) | ✅ | ✅ | ✅ | Medium |
| Invalid API Key | ✅ | ✅ | N/A | High |
| Rate Limiting | ✅ | ✅ | N/A | Medium |
| Connection Error | N/A | N/A | ✅ | High |
| Timeout Handling | ✅ | ✅ | ✅ | Medium |
| Response Parsing | ✅ | ✅ | ✅ | High |
| Context Injection | ✅ | ✅ | ✅ | High |
| Model-Specific Params | ✅ | N/A | N/A | Medium |
| Streaming | N/A | ✅ | ✅ | Low |

## Best Practices

### For Local Development

1. **Start with unit tests**: Fast feedback loop
   ```bash
   pytest -m unit --maxfail=1  # Stop at first failure
   ```

2. **Use Ollama for integration testing**: Free and local
   ```bash
   pytest -m "integration and ollama"
   ```

3. **Only test paid APIs when necessary**: Avoid unnecessary costs
   ```bash
   # Only when you've changed provider code
   TEST_OPENAI=1 pytest -m "integration and openai"
   ```

### For CI/CD

1. **Cache dependencies**: Speed up pipeline
   ```yaml
   - uses: actions/cache@v3
     with:
       path: ~/.cache/pip
       key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
   ```

2. **Run fast tests first**: Fail fast
   ```bash
   pytest -m unit  # ~10 seconds
   pytest -m integration  # Only if unit tests pass
   ```

3. **Use secrets for API keys**: Never commit keys
   ```yaml
   env:
     OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
   ```

## Summary

- **Default**: `pytest` runs unit tests + Ollama integration (fast, free)
- **OpenAI**: `TEST_OPENAI=1 OPENAI_API_KEY=sk-... pytest -m "integration and openai"`
- **Anthropic**: `TEST_ANTHROPIC=1 ANTHROPIC_API_KEY=sk-ant-... pytest -m "integration and anthropic"`
- **All providers**: Combine flags for comprehensive testing
- **Cost-conscious**: Use `pytest -m unit` or `-m "not requires_api_key"`

Happy testing! 🚀
