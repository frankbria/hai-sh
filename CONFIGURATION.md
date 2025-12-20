# hai-sh Configuration Guide

Complete guide for configuring hai-sh to work with your preferred LLM provider and customize its behavior.

## Table of Contents

- [Configuration File Location](#configuration-file-location)
- [Configuration File Format](#configuration-file-format)
- [Core Configuration](#core-configuration)
- [Provider Configuration](#provider-configuration)
  - [OpenAI Setup](#openai-setup)
  - [Anthropic Setup](#anthropic-setup)
  - [Ollama Setup (Local)](#ollama-setup-local)
  - [Local Model Setup](#local-model-setup)
- [Context Settings](#context-settings)
- [Output Settings](#output-settings)
- [Example Configurations](#example-configurations)
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
model: "llama3.2"           # Default model name

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

### `model` (optional)

Default model name for the selected provider. This is overridden by provider-specific model settings.

**Type**: `string`
**Default**: `"llama3.2"` (for Ollama)

```yaml
model: "llama3.2"
```

**Note**: This setting is optional and mainly used as a fallback. Each provider has its own `model` setting that takes precedence.

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
- `gpt-4o` - Latest GPT-4 Omni (most capable, expensive)
- `gpt-4o-mini` - Smaller, faster GPT-4 (recommended)
- `gpt-4-turbo` - GPT-4 Turbo
- `gpt-4` - Standard GPT-4
- `gpt-3.5-turbo` - GPT-3.5 (cheapest)

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
    model: "llama3.2"                   # Model to use
```

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
**Default**: `"llama3.2"`

Ollama model to use. Must be pulled first.

**Popular models**:
- `llama3.2` - Latest Llama (recommended, ~2GB)
- `llama3.2:70b` - Larger Llama (better quality, ~40GB)
- `mistral` - Mistral 7B (~4GB)
- `codellama` - Code-focused Llama (~4GB)
- `phi3` - Microsoft Phi-3 (very small, ~2GB)
- `gemma` - Google Gemma (~3GB)

**Pulling models**:
```bash
# Pull a model before using it
ollama pull llama3.2
ollama pull mistral
ollama pull codellama

# List installed models
ollama list
```

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
ollama pull llama3.2

# Test it
ollama run llama3.2 "Hello!"
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
    model: "llama3.2"
```

**Why Ollama is recommended**:
- ✅ **Free**: No API costs
- ✅ **Private**: Data stays local
- ✅ **Fast**: No network latency
- ✅ **Offline**: Works without internet
- ✅ **Quality**: Llama 3.2 rivals GPT-3.5

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
    model: "llama3.2"

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
3. Run `ollama pull llama3.2`
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
    model: "llama3.2"

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
    model: "llama3.2"

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
    model: "llama3.2"

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

### Automation / Script Configuration

**Best for**: Using hai in scripts without output clutter.

```yaml
provider: "ollama"

providers:
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2"

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
    model: "llama3.2"

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
ollama pull llama3.2
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
