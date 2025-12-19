# Product Requirements Document: hai

## Overview

A thin, context-aware wrapper around bash that enables natural language command generation and execution via LLM assistance. Users can invoke LLM help inline during normal shell usage for tasks they can't quite remember or want to express naturally.

**Name:** hai (pronounce like "hi" - friendly shell assistant)

**Invocation:** Ctrl+Shift+H or `@hai` prefix

**Inspiration:** Similar agile versioning approach to [parallel-cc](https://github.com/frankbria/parallel-cc)

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Name** | hai | Short, friendly, easy to type. Ctrl+Shift+H matches the name. |
| **Integration** | Standalone Python wrapper | Easier to develop/debug, supports multiple shells (bash/zsh/fish) |
| **Keyboard Shortcut** | Ctrl+Shift+H | No conflicts, aligns with name, Shift modifiers are safer |
| **Memory Model** | Hybrid: per-session + per-directory + persistent preferences | Session context is clean, directory context is useful, preferences persist |
| **Prompt Style** | Minimal/focused | Fast, works with smaller models, less token usage |
| **Error Retries** | 2-3 attempts (v0.5), smart/adaptive (post-1.0) | Balanced between autonomy and not wasting time |
| **Error Model** | Upgrade to stronger model for corrections | Cost-effective: fast/cheap for initial, smart/expensive for debugging |
| **Team Config** | Not now, individual focus | Validate individual use case first, add team features if demand |

## Vision

**Short-term:** Eliminate the context-switch of leaving the terminal to look up git commands, bash syntax, or command flags.

**Long-term:** A sophisticated agent framework that can:
- Execute complex workflows in sandboxed environments
- Manage scheduled tasks via cron integration
- Coordinate multi-step operations across services
- Provide intelligent error recovery and debugging

## Goals & Non-Goals

### Goals
- **Seamless Integration:** Feel like a natural extension of bash, not a separate tool
- **Local-First:** Support local/Ollama models to avoid API costs for simple queries
- **Safety:** Clear permission boundaries preventing accidental destructive operations
- **Transparency:** Always show what's happening (conversation vs execution layers)
- **Agile Evolution:** Ship working increments frequently

### Non-Goals (for v0.1)
- ❌ Sandbox integration (E2B, Daytona, bubblewrap)
- ❌ Dry-run mode
- ❌ Checkpointing/undo
- ❌ Automatic error correction
- ❌ Advanced TUI/fancy UI
- ❌ MCP server integration

## User Stories

### Primary Use Case
> "I'm working on a feature branch and realize I need to commit just one file to main. Instead of mentally translating this to git commands, I hit **Ctrl+Shift+H** and say: 'I know I'm working on a feature branch, but just one document I just created, can you commit that to main by itself?'
>
> The tool either asks for clarification OR (if obvious) executes: `git stash`, `git checkout main`, `git add <file>`, `git commit -m "..."`, `git checkout <feature-branch>`, `git stash pop`"

### Secondary Use Cases
- "Show me files modified in the last 24 hours"
- "Find all TypeScript files that import React"
- "What's taking up the most disk space?"
- "Set up a Python virtual environment and install requirements"

## Requirements by Version

### v0.1 - Proof of Concept (MVP)
**Goal:** Validate core concept is useful

#### Core Functionality
- [ ] **Invocation mechanism:** Ctrl+Shift+H or `@hai` prefix triggers LLM assistance
- [ ] **Single LLM integration:** At least one provider working (OpenAI or Ollama)
- [ ] **Basic execution:** Generated commands run in current shell context
- [ ] **Dual-layer output:**
  - Conversation layer (LLM reasoning/explanation)
  - Execution layer (actual bash commands + output)
  - Distinguish visually (colors, separators, or basic formatting)
- [ ] **Minimal system prompt:** Brief, focused prompt for command generation with JSON response format

#### Configuration
- [ ] Config file (`~/.hai/config.yaml`)
- [ ] Settings:
  - LLM provider selection (openai/anthropic/ollama/local)
  - API keys
  - Default model
  - Base URL for local models

#### Context Awareness
- [ ] Current working directory
- [ ] Git state (current branch, if in repo)
- [ ] Basic environment variables (USER, HOME, SHELL)

#### Safety
- [ ] Simple execution: just run commands and show output
- [ ] No auto-execution safeguards (user controls everything)

#### Success Criteria
- Can invoke from bash prompt
- Can configure ≥2 LLM providers (1 local, 1 remote)
- Output shows both "thinking" and "doing"
- At least 5 realistic use cases work end-to-end

---

### v0.2 - Enhanced Context & Memory
**Goal:** Make LLM more effective with better context

- [ ] Recent command history (last N commands)
- [ ] Current shell session context (exported variables, aliases)
- [ ] File listings for CWD (when relevant)
- [ ] Git status details (dirty files, ahead/behind)
- [ ] **Hybrid memory model:**
  - Per-session conversation context (cleared on new terminal)
  - Per-directory working memory (project-specific context)
  - Persistent preferences (user's command patterns, preferred styles)

---

### v0.3 - Smart Execution
**Goal:** Add intelligence around when to auto-execute vs. confirm

- [ ] **Confidence scoring:** LLM returns confidence level (0-100)
- [ ] **Execution modes:**
  - `auto` (≥90% confidence): Execute immediately
  - `confirm` (70-89%): Show command, ask Y/n
  - `suggest` (<70%): Show alternatives, don't execute
- [ ] **Configurable thresholds** in config file
- [ ] **Command categorization:**
  - Read-only operations (ls, cat, git status) → auto
  - Write operations (git commit, mkdir) → confirm
  - Destructive operations (rm -rf, force push) → always confirm

---

### v0.4 - Permissions Framework
**Goal:** Granular control over what can be executed

- [ ] Permission rules config (`~/.hai/permissions.json`)
- [ ] Allowlist/denylist patterns
- [ ] Per-directory permission overrides
- [ ] Inspired by Claude Code's permission model
- [ ] Examples:
  ```json
  {
    "auto_execute": ["git status", "git log*", "ls*", "cat*"],
    "always_confirm": ["git push*", "rm*", "mv*"],
    "denied": ["rm -rf /*", "sudo rm*"],
    "per_directory": {
      "/home/frankbria/projects/sensitive": {
        "auto_execute": []
      }
    }
  }
  ```

---

### v0.5 - Error Handling
**Goal:** Recover gracefully from failures

- [ ] Automatic error detection
- [ ] LLM analyzes error output
- [ ] Suggests fixes or retries
- [ ] Option to auto-retry with corrected command
- [ ] **2-3 retry attempts** before giving up
- [ ] **Upgrade to stronger model** for error correction (fast model for initial, smart model for debugging)
- [ ] Post-v1.0: Smart/adaptive retry logic based on error type and confidence

---

### v0.6 - Multi-Step Workflows
**Goal:** Handle complex command sequences

- [ ] LLM can return multiple commands
- [ ] Show full workflow before execution
- [ ] Allow user to approve entire sequence
- [ ] Rollback capability if mid-sequence failure
- [ ] Checkpoint between steps (optional)

---

### v0.7 - Advanced Output & UX
**Goal:** Polish the user experience

- [ ] Proper TUI framework (e.g., Rich, Textual, or similar)
- [ ] Syntax highlighting for commands
- [ ] Better visual separation of layers
- [ ] Progress indicators for long operations
- [ ] Keyboard shortcuts for common actions
- [ ] Alternative invocation mode (Ctrl+Tab for mode-switch)

---

### v0.8 - Dry-Run & Undo
**Goal:** Safety features for experimentation

- [ ] `--dry-run` flag shows what would happen
- [ ] Checkpoint system saves state before operations
- [ ] `undo` command reverts last operation (where possible)
- [ ] Undo history (last N operations)

---

### v0.9 - Model Intelligence
**Goal:** Optimize model routing

- [ ] Context-aware model selection
  - Simple queries → local/fast models
  - Complex workflows → powerful models
- [ ] Multiple model support per provider
- [ ] Cost tracking for API usage
- [ ] Fallback chains (local → remote if local fails)

---

### v1.0 - Production Ready
**Goal:** Stable, polished, safe for daily use

- [ ] Comprehensive error handling
- [ ] Logging and debugging modes
- [ ] User documentation
- [ ] Installation script
- [ ] Test suite
- [ ] Security audit
- [ ] Performance optimization
- [ ] Telemetry (opt-in) for improvement

---

### Post-1.0 - Advanced Features

#### Sandbox Integration
- [ ] E2B environment support
- [ ] Daytona workspace integration
- [ ] Bubblewrap for native sandboxing
- [ ] Docker container support
- [ ] Environment upload/sync

#### Agent Framework
- [ ] MCP server integration
- [ ] Multi-agent coordination
- [ ] Long-running background tasks
- [ ] Cron job management
- [ ] Webhook/trigger support

#### Advanced Intelligence
- [ ] Learning from user patterns
- [ ] Custom command libraries
- [ ] Smart/adaptive error retry logic
- [ ] Integration with other tools (IDEs, etc.)
- [ ] Team/shared configurations (if demand emerges)

## Technical Architecture

### High-Level Components

```
┌─────────────────────────────────────────────┐
│           Bash/Zsh Shell                    │
│  ┌──────────────────────────────────────┐   │
│  │  Input Interceptor (Ctrl+Shift+H    │   │
│  │  or @hai prefix)                     │   │
│  └────────────┬─────────────────────────┘   │
│               │                             │
└───────────────┼─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│        Context Collector                    │
│  - CWD, Git state, History, Env vars        │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│         LLM Router                          │
│  - Model selection                          │
│  - Provider abstraction (OpenAI/Claude/     │
│    Ollama/Local)                            │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│      Command Generator                      │
│  - Parses LLM response                      │
│  - Extracts commands + confidence           │
│  - Multi-step workflow detection            │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│      Permission Validator                   │
│  - Checks allowlist/denylist                │
│  - Determines execution mode                │
│  - Requests user confirmation if needed     │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│       Command Executor                      │
│  - Runs in current shell context            │
│  - Captures stdout/stderr                   │
│  - Returns results                          │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│       Output Formatter                      │
│  - Dual-layer rendering                     │
│  - Conversation layer (LLM thoughts)        │
│  - Execution layer (commands + output)      │
└─────────────────────────────────────────────┘
```

### Technology Stack (Proposed)

**Core Implementation:**
- **Language:** Python (for rapid development, rich ecosystem)
- **Shell Integration:**
  - Bash: `.bashrc` hook or wrapper script
  - Zsh: `.zshrc` hook + key binding
  - Alternative: Write as bash/zsh plugin

**LLM Integration:**
- OpenAI SDK
- Anthropic SDK
- Ollama REST API
- Local model support (llama.cpp, etc.)

**Configuration:**
- YAML or JSON for user config
- Schema validation (pydantic or similar)

**Output/TUI:**
- v0.1: Simple ANSI colors + separators
- v0.7+: Rich library or Textual framework

**Testing:**
- pytest for unit tests
- Integration tests with real shell invocations
- Mock LLM responses for consistent testing

### Configuration Schema (v0.1)

```yaml
# ~/.hai/config.yaml

provider: "ollama"  # openai | anthropic | ollama | local
model: "llama3.2"

# Provider-specific settings
providers:
  openai:
    api_key: "sk-..."
    model: "gpt-4o-mini"
    base_url: null  # optional override

  anthropic:
    api_key: "sk-ant-..."
    model: "claude-sonnet-4-5"

  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2"

  local:
    model_path: "/path/to/model.gguf"
    context_size: 4096

# Context settings
context:
  include_history: true
  history_length: 10
  include_env_vars: true
  include_git_state: true

# Output settings
output:
  show_conversation: true
  show_reasoning: true
  use_colors: true
```

## Success Metrics

### v0.1 Metrics
- **Functionality:** 5+ realistic use cases work end-to-end
- **Usability:** Can be invoked in <2 seconds
- **Configuration:** Setup takes <5 minutes

### v1.0 Metrics
- **Reliability:** 95%+ success rate on common tasks
- **Safety:** Zero accidental destructive operations in testing
- **Performance:** <3 second response time for simple queries (local model)
- **Adoption:** Daily use by developer (dogfooding)

### Long-term Metrics
- **Efficiency:** 50%+ reduction in "leaving terminal to look up commands"
- **Complexity:** Can handle 80% of multi-step workflows
- **Cost:** <$5/month in API costs with hybrid local/remote strategy

## Resolved Design Decisions

All key design questions have been resolved (see "Key Decisions" table at top of document). Implementation can proceed with clear direction on:
- ✅ Naming and branding
- ✅ Technical architecture approach
- ✅ User interaction model
- ✅ Memory and context strategy
- ✅ Error handling approach
- ✅ Scope boundaries (individual vs. team)

## Appendix: Example Interactions

### Example 1: Simple Query
```bash
$ @hai show me large files in home directory

[Conversation Layer]
I'll search for large files in your home directory using find and sort by size.

[Execution Layer]
$ find ~ -type f -exec du -h {} + | sort -rh | head -20

[Output...]
```

### Example 2: Multi-step Workflow (v0.3+)
```bash
$ @hai commit just README.md to main, I'm on feature-branch

[Conversation Layer]
I'll stash your current changes, switch to main, commit README.md, and return to your feature branch.

Workflow (4 steps):
1. git stash push -m "temp stash"
2. git checkout main
3. git add README.md && git commit -m "Update README"
4. git checkout feature-branch && git stash pop

Execute this workflow? [Y/n]: y

[Execution Layer]
$ git stash push -m "temp stash"
Saved working directory and index state...

$ git checkout main
Switched to branch 'main'

$ git add README.md && git commit -m "Update README"
[main a3f7c21] Update README
 1 file changed, 5 insertions(+)

$ git checkout feature-branch && git stash pop
Switched to branch 'feature-branch'
On branch feature-branch
Changes not staged for commit...

[Conversation Layer]
✓ Done! README.md committed to main, you're back on feature-branch with your working changes restored.
```

### Example 3: Clarification Needed
```bash
$ @hai delete old logs

[Conversation Layer]
I found multiple log locations. Which would you like to clean up?

Options:
1. /var/log/*.log (requires sudo)
2. ~/.local/logs/*.log (user logs)
3. ./logs/*.log (current directory)

Please specify: 2

[Execution Layer]
$ rm ~/.local/logs/*.log

[Conversation Layer]
✓ Removed 47 log files from ~/.local/logs/
```

---

## Next Steps

1. **Validate PRD:** Review and refine based on feedback
2. **Project Setup:** Create repo, choose name, set up initial structure
3. **v0.1 Development:**
   - Implement basic shell hook
   - Integrate one LLM provider
   - Build dual-layer output
   - Create config system
4. **Dogfooding:** Use it daily, gather learnings
5. **Iterate:** Ship v0.2, v0.3... following agile approach

---

**Document Version:** 1.0
**Last Updated:** 2025-12-19
**Author:** frankbria
**Status:** Ready for Implementation ✅

All key design decisions resolved. Ready to begin v0.1 development.
