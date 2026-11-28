# hai-sh Configuration Guide

Complete guide for configuring hai-sh to work with your preferred LLM provider and customize its behavior.

## Table of Contents

- [Configuration File Location](#configuration-file-location)
- [Configuration File Format](#configuration-file-format)
- [Core Configuration](#core-configuration)
  - [provider](#provider-required)
  - [provider_priority](#provider_priority-optional)
  - [model](#model-optional)
- [Provider Configuration](#provider-configuration)
  - [OpenAI Setup](#openai-setup)
  - [Anthropic Setup](#anthropic-setup)
  - [Ollama Setup (Local)](#ollama-setup-local)
  - [Local Model Setup](#local-model-setup)
- [Models](#models)
  - [hai-model](#hai-model)
  - [licence_policy](#licence_policy)
  - [Upgrading from v0.1.4](#upgrading-from-v014)
- [Context Settings](#context-settings)
- [Output Settings](#output-settings)
- [Example Configurations](#example-configurations)
  - [Provider Fallback Chain Configuration](#provider-fallback-chain-configuration)
- [Security Best Practices](#security-best-practices)
- [Configuration Validation](#configuration-validation)
- [Troubleshooting](#troubleshooting)

---

## Configuration File Location

### Default Location

hai-sh stores its configuration in your home directory:

```
~/.hai/config.yaml
```

### Directory Structure

When initialized, hai creates the following structure:

```
~/.hai/
├── config.yaml              # Main configuration file
├── bash_integration.sh      # Bash keyboard shortcut
├── zsh_integration.sh       # Zsh keyboard shortcut
├── logs/                    # Log files (future)
└── cache/                   # Cache directory (future)
```

### Custom Configuration Path

You can specify a custom config file path:

```bash
# Using environment variable
export HAI_CONFIG="/path/to/custom/config.yaml"
hai "your query"

# Using command-line flag
hai --config /path/to/custom/config.yaml "your query"
```

### Initialization

The configuration file is automatically created on first run:

```bash
hai --version  # Creates ~/.hai/config.yaml if it doesn't exist
```

---

## Configuration File Format

hai uses YAML format for configuration. The file must be valid YAML and follow the schema below.

### Basic Structure

```yaml
# Core settings
provider: "ollama"           # Which provider to use

# Provider configurations
providers:
  openai: { ... }
  anthropic: { ... }
  ollama: { ... }
  local: { ... }

# Context settings
context:
  include_history: true
  # ... more options

# Output settings
output:
  show_conversation: true
  # ... more options
```

### YAML Syntax Notes

- **Comments**: Lines starting with `#` are comments
- **Strings**: Can be quoted (`"value"`) or unquoted (`value`)
- **Booleans**: `true` or `false` (lowercase)
- **Numbers**: Written without quotes
- **Null values**: Use `null` or leave blank

---

## Core Configuration

### `provider` (required)

Specifies which LLM provider to use by default.

**Type**: `string`
**Valid values**: `"openai"`, `"anthropic"`, `"ollama"`, `"local"`
**Default**: `"ollama"`

```yaml
provider: "ollama"  # Use local Ollama models
```

**Examples**:
```yaml
provider: "openai"      # Use OpenAI GPT models
provider: "anthropic"   # Use Anthropic Claude models
provider: "ollama"      # Use local Ollama models (recommended)
provider: "local"       # Use local model file
```

---

### `provider_priority` (optional)

Ordered list of providers to try for automatic fallback support. When set, overrides the `provider` field. Providers are tried in order until one is available.

**Type**: `list[string]` or `null`
**Valid values**: `["openai", "anthropic", "ollama", "local"]`
**Default**: `null` (uses single `provider` field)

```yaml
# Try Ollama first, fall back to OpenAI, then Anthropic
provider_priority:
  - "ollama"
  - "openai"
  - "anthropic"
```

**How fallback works**:
1. hai tries each provider in order
2. If a provider is unavailable (server down, API key missing, etc.), hai automatically tries the next one
3. A warning message shows which providers failed and why
4. Once a provider succeeds, hai uses it for the request

**Example output when fallback occurs**:
```
Provider 'ollama' unavailable (Cannot connect to Ollama...), trying 'openai'...
Using provider 'openai'
```

**Use cases**:
- **Local-first workflow**: Try free local Ollama, fall back to cloud if unavailable
- **Cost optimization**: Try cheaper providers first
- **Reliability**: Ensure hai works even if one provider is down
- **Rate limit handling**: Automatically switch if one provider is rate-limited

**Examples**:

```yaml
# Local-first: Free when possible
provider_priority:
  - "ollama"      # Try local first (free)
  - "openai"      # Fall back to cloud

# Cost-optimized chain
provider_priority:
  - "ollama"      # Free local
  - "openai"      # Cheaper cloud option
  - "anthropic"   # More expensive backup

# Cloud-only with redundancy
provider_priority:
  - "anthropic"   # Primary cloud provider
  - "openai"      # Backup cloud provider
```

**Backward compatibility**: If `provider_priority` is not set, hai uses the single `provider` field as before. Existing configurations continue to work without modification.

---

## Provider Configuration

Configure multiple providers and switch between them easily.

---

### OpenAI Setup

Configure OpenAI's GPT models.

#### Configuration Options

```yaml
providers:
  openai:
    api_key: "sk-..."              # Your OpenAI API key (optional)
    model: "gpt-4o-mini"           # Model to use
    base_url: null                 # Custom endpoint (optional)
```

#### `api_key` (required for OpenAI)

**Type**: `string` (optional in config if set via environment variable)
**Environment variable**: `OPENAI_API_KEY`

Your OpenAI API key. For security, prefer using environment variables:

```bash
# In ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="sk-..."
```

Or set in config (less secure):

```yaml
providers:
  openai:
    api_key: "sk-proj-..."
```

**Getting an API key**:
1. Visit https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

#### `model`

**Type**: `string`
**Default**: `"gpt-4o-mini"`

OpenAI model to use.

**Supported models**:
- `gpt-5-nano` - GPT-5 series (latest, nano size)
- `gpt-5-mini` - GPT-5 series (mini size)
- `gpt-5` - GPT-5 series (standard)
- `gpt-4.1-nano` - GPT-4.1 series (nano size)
- `gpt-4.1-mini` - GPT-4.1 series (mini size)
- `o1-preview` - OpenAI o1 series (advanced reasoning)
- `o1-mini` - OpenAI o1 series (smaller, faster)
- `gpt-4o` - Latest GPT-4 Omni (most capable, expensive)
- `gpt-4o-mini` - Smaller, faster GPT-4 (recommended)
- `gpt-4-turbo` - GPT-4 Turbo
- `gpt-4` - Standard GPT-4
- `gpt-3.5-turbo` - GPT-3.5 (cheapest)

**Note**: The `max_tokens` configuration parameter is automatically mapped to the
appropriate API parameter (`max_tokens` or `max_completion_tokens`) based on the
model being used. Newer models (o1, gpt-5, gpt-4.1 series) automatically use `max_completion_tokens`.

**Cost considerations**:
- `gpt-4o-mini`: ~$0.15 per 1M input tokens (best value)
- `gpt-3.5-turbo`: ~$0.50 per 1M input tokens
- `gpt-4o`: ~$2.50 per 1M input tokens

```yaml
providers:
  openai:
    model: "gpt-4o-mini"  # Recommended for daily use
```

#### `base_url` (optional)

**Type**: `string` or `null`
**Default**: `null`

Custom API endpoint for OpenAI-compatible services (e.g., Azure OpenAI).

```yaml
providers:
  openai:
    base_url: "https://your-custom-endpoint.com/v1"
```

#### Complete OpenAI Example

```yaml
provider: "openai"

providers:
  openai:
    # api_key: set via OPENAI_API_KEY env var
    model: "gpt-4o-mini"
    base_url: null
```

---

### Anthropic Setup

Configure Anthropic's Claude models.

#### Configuration Options

```yaml
providers:
  anthropic:
    api_key: "sk-ant-..."          # Your Anthropic API key (optional)
    model: "claude-sonnet-4-5"     # Model to use
```

#### `api_key` (required for Anthropic)

**Type**: `string` (optional in config if set via environment variable)
**Environment variable**: `ANTHROPIC_API_KEY`

Your Anthropic API key. Prefer environment variables:

```bash
# In ~/.bashrc or ~/.zshrc
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or set in config:

```yaml
providers:
  anthropic:
    api_key: "sk-ant-api03-..."
```

**Getting an API key**:
1. Visit https://console.anthropic.com/
2. Sign in or create an account
3. Navigate to API Keys
4. Create a new key (starts with `sk-ant-`)

#### `model`

**Type**: `string`
**Default**: `"claude-sonnet-4-5"`

Anthropic model to use.

**Supported models**:
- `claude-opus-4-5` - Most capable (expensive)
- `claude-sonnet-4-5` - Balanced performance (recommended)
- `claude-sonnet-4` - Previous generation
- `claude-3-opus` - Legacy flagship model
- `claude-3-sonnet` - Legacy balanced model

```yaml
providers:
  anthropic:
    model: "claude-sonnet-4-5"  # Recommended
```

#### Complete Anthropic Example

```yaml
provider: "anthropic"

providers:
  anthropic:
    # api_key: set via ANTHROPIC_API_KEY env var
    model: "claude-sonnet-4-5"
```

---

### Ollama Setup (Local)

Configure Ollama for free, local LLM usage (recommended for daily use).

#### Configuration Options

```yaml
providers:
  ollama:
    base_url: "http://localhost:11434"  # Ollama server URL
    model: "gemma4:e2b"                 # Model to use
    format: "schema"                    # Constrain output to hai's JSON reply
    temperature: 0                      # Deterministic answers
    think: false                        # No hidden reasoning (faster)
    options:
      num_predict: 1024                 # Cap on generated tokens
```

These are the defaults. A config that sets only `model` keeps the other
settings, because your file is merged over the defaults.

#### `base_url`

**Type**: `string`
**Default**: `"http://localhost:11434"`

URL of your Ollama server.

**Local installation**:
```yaml
providers:
  ollama:
    base_url: "http://localhost:11434"
```

**Remote installation**:
```yaml
providers:
  ollama:
    base_url: "http://192.168.1.100:11434"  # Another machine
```

**Docker installation**:
```yaml
providers:
  ollama:
    base_url: "http://ollama:11434"  # Docker container
```

#### `model`

**Type**: `string`
**Default**: `"gemma4:e2b"`

Ollama model to use. Must be pulled first (`hai-model pull gemma4:e2b` or
`ollama pull gemma4:e2b`, about a 4.6 GB download). If it isn't, `hai` offers
the download the first time you ask something; see [Models](#models).
`hai --model NAME` uses another model for one question without changing this
setting.

The default was chosen with the eval in [`eval/`](./eval/README.md): 93 real
hai requests, each command run in a sandbox, scored on JSON validity, task
accuracy, answer-vs-command choice, refusal of catastrophic requests and
latency. Results on a CPU-only laptop (i7-7700HQ), with the default settings
above:

| model | task accuracy | catastrophic requests refused | median latency | license |
|---|---|---|---|---|
| `gemma4:e2b` (default) | 88% | 7/7 | 4.6 s | Apache 2.0 |
| `gemma4:e4b` | 91% | 7/7 | 7.5 s | Apache 2.0 |
| `qwen2.5-coder:3b` | 91% | 7/7 | 4.8 s | Qwen Research (non-commercial) |
| `phi4-mini` | 83% | 7/7 | 7.2 s | MIT |
| `llama3.2` (previous default) | 77% | 5/7 | 5.6 s | Llama 3.2 Community |

Any Ollama model works; the eval README explains how to test another one.

**Pulling models**:
```bash
# Pull a model before using it (shows size, free disk and licence, then asks)
hai-model pull gemma4:e2b

# hai's tested models and what you have installed
hai-model list

# Make another model the default
hai-model use phi4-mini
```

#### `format`

**Type**: `"schema"`, `"json"`, a JSON-schema object, or `null`
**Default**: `"schema"`

`"schema"` makes Ollama's decoder follow hai's response schema, so every reply
is valid JSON with an explanation, a command (empty when the request is a
question) and a confidence. `null` turns the constraint off.

#### `temperature`

**Type**: `number` (0 to 2)
**Default**: `0`

#### `think`

**Type**: `boolean` or `null`
**Default**: `false`

Turns off hidden reasoning on models that support it, which is much faster.
Models without that capability get the request again without the flag.

#### `options`

**Type**: mapping of Ollama options
**Default**: `{num_predict: 1024}`

Passed to Ollama as-is (for example `seed`, `num_ctx`, `num_predict`). The
token cap stops a model that falls into a repetition loop.

#### Setting Up Ollama

**Installation**:

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Download from https://ollama.com/download
```

**Start Ollama server**:

```bash
# Run Ollama server
ollama serve

# In another terminal, pull a model
ollama pull gemma4:e2b

# Test it
ollama run gemma4:e2b "Hello!"
```

**Verify Ollama is running**:

```bash
# Check Ollama status
curl http://localhost:11434

# Should return: "Ollama is running"
```

#### Complete Ollama Example

```yaml
provider: "ollama"

providers:
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma4:e2b"
```

**Why Ollama is recommended**:
- ✅ **Free**: No API costs
- ✅ **Private**: Data stays local
- ✅ **Fast**: No network latency
- ✅ **Offline**: Works without internet
- ✅ **Quality**: the default model scores 88% on hai's eval

---

### Local Model Setup

Configure custom local model files.

#### Configuration Options

```yaml
providers:
  local:
    model_path: "/path/to/model.gguf"  # Path to model file
    context_size: 4096                 # Context window size
```

#### `model_path` (required)

**Type**: `string`

Path to your local model file (GGUF format).

```yaml
providers:
  local:
    model_path: "/home/user/models/llama-3.2.gguf"
```

#### `context_size`

**Type**: `integer`
**Default**: `4096`
**Range**: `512` to `128000`

Context window size in tokens.

```yaml
providers:
  local:
    context_size: 8192  # 8k context window
```

#### Complete Local Model Example

```yaml
provider: "local"

providers:
  local:
    model_path: "/home/user/models/llama-3.2-7b-q4.gguf"
    context_size: 4096
```

**Note**: Local model support requires additional dependencies. See [INSTALL.md](./INSTALL.md) for details.

---

## Models

hai ships a small catalog of Ollama models it has been tested with
(`hai_sh/data/models.yaml`): the name, download size, licence and eval scores
of each. hai never bundles a model; Ollama downloads it, and only after you say
yes.

### `hai-model`

```bash
hai-model status          # Ollama version, the configured model, installed or not
hai-model list            # recommended models (filtered by licence_policy) and installed ones
hai-model pull NAME       # download, after showing size, free disk and licence
hai-model use NAME        # set providers.ollama.model, offering the download if needed
```

Options:

- `hai-model --config FILE ...` works on another config file.
- `pull --yes` skips the question (needed when there is no terminal, for
  example in a script). Without a terminal and without `--yes`, nothing is
  downloaded and hai prints the command to run.
- `pull --force` downloads even when the disk check says no.
- `use --no-pull` sets the model without downloading it.

`hai-model use` changes only the `model:` line under `providers.ollama`,
keeping your comments, and saves the previous file as `config.yaml.bak`.

**Disk check**: hai won't start a download that would leave less free space
than 10% of the disk, capped at 20 GB, and never less than 2 GB. It warns when
a model would use more than 70% of your RAM. Both checks apply only when Ollama
runs on this machine.

**When the model is missing**, `hai "<question>"`:

- in a terminal, shows the size, free disk and licence and asks whether to
  download it (Enter means No). If you say no it offers another installed
  model from the catalog, then any cloud provider you have already configured
  (for that one question, with a privacy note).
- from the Ctrl+X Ctrl+H binding (`--suggest-only`), prints its usual JSON
  with an empty command and the `hai-model pull` command to run.
- in a pipe or script, prints the command to run and exits with status 1.

**When Ollama isn't installed or running**, hai prints the official install
command (or `ollama serve`) and never runs it.

### `licence_policy`

```yaml
models:
  licence_policy: "any"   # or "commercial"
```

**Type**: `"any"` or `"commercial"`
**Default**: `"any"`

The default model is always licensed for commercial use. `qwen2.5-coder:3b`
is not (Qwen Research licence, non-commercial use only). With `commercial`,
hai-model list, the setup wizard and the missing-model menu suggest
`phi4-mini` instead. Models you choose yourself are never blocked; hai only
says when one doesn't fit the policy.

### Upgrading from v0.1.4

- Your `model:` setting is kept. If it is still `llama3.2` (the old default),
  hai shows a one-time note in a terminal with the eval numbers and the
  command to switch: `hai-model use gemma4:e2b`. It never changes the file.
- A v0.1.4 config has no `format`, `temperature` or `think` lines, so it now
  gets the new defaults (`"schema"`, `0`, `false`), whatever model you use.
  To get v0.1.4's behaviour back, add under `providers.ollama`:

  ```yaml
      format: null
      temperature: 0.7
      think: null
  ```

---

## Context Settings

Configure what contextual information hai includes when generating commands.

### Configuration Options

```yaml
context:
  include_history: true       # Include command history
  history_length: 10          # Number of recent commands
  include_env_vars: true      # Include environment variables
  include_git_state: true     # Include git repository state
```

---

### `include_history`

**Type**: `boolean`
**Default**: `true`

Include recent command history in the context sent to the LLM.

```yaml
context:
  include_history: true
```

**When enabled**, hai includes your recent commands:
```
Recent commands:
  1. ls -la
  2. cd src/
  3. git status
```

**Use cases**:
- Improves context awareness
- Helps LLM understand what you're doing
- Enables follow-up commands ("do that again")

**Privacy note**: Only the last N commands are included, and sensitive commands can be filtered.

---

### `history_length`

**Type**: `integer`
**Default**: `10`
**Range**: `0` to `100`

Number of recent commands to include in context.

```yaml
context:
  history_length: 20  # Include last 20 commands
```

**Recommendations**:
- `5-10`: Good for quick tasks
- `10-20`: Better context for complex workflows
- `20+`: Maximum context (uses more tokens)

---

### `include_env_vars`

**Type**: `boolean`
**Default**: `true`

Include environment variables in the context.

```yaml
context:
  include_env_vars: true
```

**Included variables** (non-sensitive only):
- `USER`, `HOME`, `SHELL`, `PATH`
- `PWD` (current directory)
- Language settings (`LANG`, `LC_*`)

**Excluded variables** (for security):
- `*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`
- API keys and credentials

**Use cases**:
- Helps LLM understand your environment
- Enables environment-aware commands
- Improves cross-platform compatibility

---

### `include_git_state`

**Type**: `boolean`
**Default**: `true`

Include git repository state if in a git repo.

```yaml
context:
  include_git_state: true
```

**Included information**:
- Current branch name
- Uncommitted changes (yes/no)
- Staged files count
- Unstaged files count
- Ahead/behind remote

**Example context**:
```
Git: feature-branch, 3 uncommitted changes, 2 staged files
```

**Use cases**:
- Git workflow commands
- Branch management
- Understanding project state

---

### Complete Context Example

```yaml
context:
  include_history: true
  history_length: 15
  include_env_vars: true
  include_git_state: true
```

---

## Output Settings

Configure how hai displays results.

### Configuration Options

```yaml
output:
  show_conversation: true     # Show LLM explanation
  show_reasoning: true        # Show reasoning process
  use_colors: true            # Use ANSI colors
```

---

### `show_conversation`

**Type**: `boolean`
**Default**: `true`

Show the LLM's explanation and reasoning.

```yaml
output:
  show_conversation: true
```

**When enabled**:
```
━━━ Conversation ━━━
I'll search for large files using find and sort them by size.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ find ~ -type f -size +100M -exec du -h {} + | sort -rh
```

**When disabled**:
```
$ find ~ -type f -size +100M -exec du -h {} + | sort -rh
```

**Use cases**:
- **Enabled**: Learning, transparency, understanding
- **Disabled**: Speed, scripts, automation

---

### `show_reasoning`

**Type**: `boolean`
**Default**: `true`

Show the LLM's reasoning process (more detailed than conversation).

```yaml
output:
  show_reasoning: true
```

**Future feature**: Will show step-by-step reasoning for complex commands.

---

### `use_colors`

**Type**: `boolean`
**Default**: `true`

Use ANSI colors in output.

```yaml
output:
  use_colors: true
```

**Auto-detection**: Colors are automatically disabled when:
- Output is piped (`hai "query" | less`)
- `NO_COLOR` environment variable is set
- Terminal doesn't support colors

**Force colors**:
```bash
FORCE_COLOR=1 hai "query"
```

**Disable colors**:
```bash
NO_COLOR=1 hai "query"
```

**Use cases**:
- **Enabled**: Interactive terminal use
- **Disabled**: Piping, logging, scripts

---

### Complete Output Example

```yaml
output:
  show_conversation: true
  show_reasoning: true
  use_colors: true
```

---

## Example Configurations

### Minimal Configuration (Ollama Local)

**Best for**: Free, local usage with minimal setup.

```yaml
provider: "ollama"

providers:
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma4:e2b"

context:
  include_history: true
  history_length: 10
  include_env_vars: true
  include_git_state: true

output:
  show_conversation: true
  show_reasoning: true
  use_colors: true
```

**Setup steps**:
1. Install Ollama
2. Run `ollama serve`
3. Run `ollama pull gemma4:e2b`
4. Use hai!

---

### OpenAI Configuration

**Best for**: Maximum quality, willing to pay for API.

```yaml
provider: "openai"

providers:
  openai:
    # Set OPENAI_API_KEY environment variable
    model: "gpt-4o-mini"
    base_url: null

  # Keep Ollama as fallback
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma4:e2b"

context:
  include_history: true
  history_length: 15
  include_env_vars: true
  include_git_state: true

output:
  show_conversation: true
  show_reasoning: true
  use_colors: true
```

**Setup steps**:
1. Get OpenAI API key from https://platform.openai.com/api-keys
2. Add to `~/.bashrc`: `export OPENAI_API_KEY="sk-..."`
3. Use hai!

---

### Anthropic (Claude) Configuration

**Best for**: High-quality responses, latest Claude models.

```yaml
provider: "anthropic"

providers:
  anthropic:
    # Set ANTHROPIC_API_KEY environment variable
    model: "claude-sonnet-4-5"

  # Keep Ollama as fallback
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma4:e2b"

context:
  include_history: true
  history_length: 20
  include_env_vars: true
  include_git_state: true

output:
  show_conversation: true
  show_reasoning: true
  use_colors: true
```

**Setup steps**:
1. Get Anthropic API key from https://console.anthropic.com/
2. Add to `~/.bashrc`: `export ANTHROPIC_API_KEY="sk-ant-..."`
3. Use hai!

---

### Multi-Provider Configuration

**Best for**: Switching between providers as needed.

```yaml
provider: "ollama"  # Default to free local

providers:
  # OpenAI for important tasks
  openai:
    model: "gpt-4o-mini"

  # Anthropic for complex reasoning
  anthropic:
    model: "claude-sonnet-4-5"

  # Ollama for daily use
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma4:e2b"

context:
  include_history: true
  history_length: 15
  include_env_vars: true
  include_git_state: true

output:
  show_conversation: true
  show_reasoning: true
  use_colors: true
```

**Switch providers**:
```bash
# Use default (Ollama)
hai "list files"

# Use OpenAI (future: --provider flag)
# Currently: edit config and change provider value

# Use Anthropic
# Edit config: provider: "anthropic"
```

---

### Provider Fallback Chain Configuration

**Best for**: Automatic failover when primary provider is unavailable.

```yaml
# Use provider_priority for automatic fallback
provider_priority:
  - "ollama"      # Try local first (free, fast)
  - "openai"      # Fall back to OpenAI
  - "anthropic"   # Last resort

providers:
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma4:e2b"

  openai:
    # api_key: set via OPENAI_API_KEY env var
    model: "gpt-4o-mini"

  anthropic:
    # api_key: set via ANTHROPIC_API_KEY env var
    model: "claude-sonnet-4-5"

context:
  include_history: true
  history_length: 10
  include_env_vars: true
  include_git_state: true

output:
  show_conversation: true
  show_reasoning: true
  use_colors: true
```

**How it works**:
1. hai tries Ollama first (local, free)
2. If Ollama is not running, hai automatically tries OpenAI
3. If OpenAI fails (no API key, rate limit), hai tries Anthropic
4. User sees a message indicating which provider is being used

**Example output**:
```
Provider 'ollama' unavailable (Cannot connect to Ollama at http://localhost:11434...), trying 'openai'...
Using provider 'openai'

I'll list the files in the current directory...
```

**Benefits**:
- ✅ Works offline when Ollama is available
- ✅ Automatic fallback to cloud when local is down
- ✅ No manual switching needed
- ✅ Optimizes for cost (local first)

---

### Automation / Script Configuration

**Best for**: Using hai in scripts without output clutter.

```yaml
provider: "ollama"

providers:
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma4:e2b"

context:
  include_history: false      # Don't include history
  history_length: 0
  include_env_vars: false     # Minimal context
  include_git_state: false

output:
  show_conversation: false    # Command only
  show_reasoning: false
  use_colors: false           # No colors for piping
```

**Use in scripts**:
```bash
#!/bin/bash
# Generate command using hai
cmd=$(hai "find large log files")
# Execute it
eval "$cmd"
```

---

### Privacy-Focused Configuration

**Best for**: Maximum privacy, no cloud APIs.

```yaml
provider: "ollama"  # Local only

providers:
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma4:e2b"

context:
  include_history: false      # Don't send history
  history_length: 0
  include_env_vars: false     # Don't send env vars
  include_git_state: false    # Don't send git state

output:
  show_conversation: true
  show_reasoning: true
  use_colors: true
```

**Benefits**:
- All data stays on your machine
- No API keys needed
- No internet required
- Complete privacy

---

## Security Best Practices

### API Key Security

#### ✅ DO: Use Environment Variables

**Best practice** - Store API keys in environment variables:

```bash
# In ~/.bashrc or ~/.zshrc (not in git!)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Why**:
- Not committed to version control
- Easier to rotate keys
- Standard practice
- Separate from code

#### ❌ DON'T: Store Keys in Config Files

**Bad practice** - Avoid storing keys directly in config:

```yaml
# DON'T DO THIS if config is in git
providers:
  openai:
    api_key: "sk-proj-hardcoded-key-here"  # ❌ BAD
```

**Risk**: Keys can be accidentally committed to git and exposed.

#### Environment Variable Setup

```bash
# Add to ~/.bashrc (or ~/.zshrc for Zsh)
export OPENAI_API_KEY="sk-proj-your-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Reload shell
source ~/.bashrc
```

**Verify**:
```bash
echo $OPENAI_API_KEY  # Should show your key
```

---

### Configuration File Permissions

Protect your configuration file:

```bash
# Set restrictive permissions
chmod 600 ~/.hai/config.yaml

# Verify
ls -la ~/.hai/config.yaml
# Should show: -rw------- (owner read/write only)
```

---

### Git Ignore Patterns

If you keep custom configs in git, add to `.gitignore`:

```gitignore
# .gitignore
.hai/config.yaml
*.local.yaml
*secret*
*key*
```

---

### Key Rotation

Regularly rotate API keys:

1. **Generate new key** at provider console
2. **Update environment variable**:
   ```bash
   # In ~/.bashrc
   export OPENAI_API_KEY="sk-new-key-here"
   ```
3. **Reload shell**: `source ~/.bashrc`
4. **Revoke old key** at provider console

---

### Minimal Context Sharing

For privacy, minimize context sent to APIs:

```yaml
context:
  include_history: false      # Don't send command history
  include_env_vars: false     # Don't send environment
  include_git_state: false    # Don't send git state
```

**Use Ollama for sensitive work**:
```yaml
provider: "ollama"  # Everything stays local
```

---

### Multi-User Systems

On shared systems:

```bash
# Ensure ~/.hai is private
chmod 700 ~/.hai

# Verify
ls -lad ~/.hai
# Should show: drwx------ (owner only)
```

---

## Configuration Validation

hai validates your configuration on startup.

### Check Configuration

```bash
# Test configuration is valid
hai --version

# See any warnings
hai --help
```

### Validation Errors

**Missing provider**:
```
Error: Configuration Error
  Provider 'openai' is selected but has no configuration.

Suggestion:
  Run 'hai --help' for configuration information or check ~/.hai/config.yaml
```

**Invalid YAML**:
```
Error: Configuration Error
  Failed to parse config file: invalid YAML syntax

Suggestion:
  Check ~/.hai/config.yaml for syntax errors
```

### Validation Warnings

**Missing API key**:
```
Warning: OpenAI provider selected but 'api_key' not set.
Set OPENAI_API_KEY environment variable or add to config.
```

**Solution**:
```bash
export OPENAI_API_KEY="sk-..."
```

---

## Troubleshooting

### Issue: Configuration not found

**Problem**: `~/.hai/config.yaml` doesn't exist

**Solution**:
```bash
# Run hai to create default config
hai --version

# Or manually create directory
mkdir -p ~/.hai
```

---

### Issue: YAML syntax error

**Problem**: Invalid YAML in config file

**Solution**:
```bash
# Test YAML syntax
python3 -c "import yaml; yaml.safe_load(open('~/.hai/config.yaml'))"

# Common issues:
# - Inconsistent indentation (use spaces, not tabs)
# - Missing quotes around special characters
# - Missing colons after keys
```

---

### Issue: Provider not working

**Problem**: Selected provider fails

**Solution**:

For OpenAI:
```bash
# Check API key is set
echo $OPENAI_API_KEY

# Test API directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

For Ollama:
```bash
# Check Ollama is running
curl http://localhost:11434

# List models
ollama list

# Pull model if missing
ollama pull gemma4:e2b
```

---

### Issue: Configuration changes not applied

**Problem**: Edited config but changes not taking effect

**Solution**:
```bash
# hai reads config on every run, so restart any long-running processes

# For shell integration, reload shell
source ~/.bashrc  # or ~/.zshrc

# Verify config location
hai --help  # Shows config path
```

---

### Issue: Environment variables not working

**Problem**: `OPENAI_API_KEY` not recognized

**Solution**:
```bash
# Check if set
echo $OPENAI_API_KEY

# If not set, add to shell config
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc
source ~/.bashrc

# Verify again
echo $OPENAI_API_KEY
```

---

### Getting Help

For configuration issues:

1. **Validate YAML**: Use online YAML validator
2. **Check logs**: Enable debug mode: `hai --debug "query"`
3. **Reset config**: Backup and recreate:
   ```bash
   mv ~/.hai/config.yaml ~/.hai/config.yaml.backup
   hai --version  # Creates new default config
   ```
4. **GitHub Issues**: https://github.com/frankbria/hai-sh/issues

---

## Next Steps

After configuring hai:

1. **Test your setup**: Run `hai "list files"`
2. **Set up shell integration**: See [INSTALL.md](./INSTALL.md)
3. **Try examples**: See [README.md](./README.md) for usage examples
4. **Customize**: Adjust settings to your preferences
5. **Secure your keys**: Follow security best practices above

---

**Configuration complete!** 🎉

For more information:
- Installation Guide: [INSTALL.md](./INSTALL.md)
- Usage Examples: [README.md](./README.md)
- Issues: https://github.com/frankbria/hai-sh/issues
