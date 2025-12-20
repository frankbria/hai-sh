# hai - Development Roadmap

**Status**: 🚧 Active Development
**Current Version**: v0.0.1
**Next Version**: v0.1 (Proof of Concept)
**Last Updated**: 2025-12-19

---

## Overview

This roadmap tracks the development of **hai** - a friendly shell assistant that brings natural language command generation to your terminal. The project follows an agile development approach inspired by [parallel-cc](https://github.com/frankbria/parallel-cc), with frequent version increments and validation at each stage.

### Competitive Landscape

Several open-source projects exist in this space:
- [shai](https://github.com/ovh/shai)
- [AITerminal](https://github.com/mirchaemanuel/AITerminal)
- [aiterm](https://github.com/Thakay/aiterm)
- [llmsh](https://github.com/LeslieLeung/llmsh) / [llmsh (alt)](https://github.com/phildougherty/llmsh)
- [ShellMate](https://github.com/AvicennaJr/ShellMate)
- [cmdai](https://github.com/JerryWestrick/cmdai)

These projects validate market demand and provide reference implementations. **hai** differentiates through:
- **Hybrid memory model** (session + directory + persistent preferences)
- **Dual-layer output** (conversation + execution transparency)
- **Smart model routing** (local-first with intelligent model selection)
- **Granular permissions framework** inspired by Claude Code

---

## Development Philosophy

### Core Principles
1. **Ship early, ship often** - Working increments over perfect features
2. **Validate as we go** - Each version must prove value before moving forward
3. **Local-first** - Support Ollama and local models to minimize API costs
4. **Safety-conscious** - Progressive permission model prevents accidents
5. **User-centered** - Solve real pain points, not hypothetical ones

### Success Gates
Each version must meet its success criteria before advancement:
- ✅ Defined functionality working end-to-end
- ✅ Usable in daily workflow (dogfooding required)
- ✅ No regressions from previous versions
- ✅ Documentation updated

---

## Version History

### v0.0.1 - Project Foundation ✅ COMPLETED

**Completion Date**: 2025-12-19
**Goal**: Establish project structure and vision

#### Checklist
- [x] Project repository created
- [x] LICENSE (AGPL v3) established
- [x] README.md with project overview
- [x] PRD.md with complete requirements and architecture
- [x] ROADMAP.md (this document)
- [x] competitors.md with market analysis
- [x] pyproject.toml configured
- [x] Development environment setup (`uv`)
- [x] Git repository initialized

#### Deliverables
- Complete project documentation
- Clear development roadmap
- Package structure defined

**Status**: ✅ All objectives met. Ready for v0.1 development.

---

## Current Development

### v0.1 - Proof of Concept (MVP) 🚧 TO BE WORKED

**Target**: Validate core concept is useful
**Key Question**: Can natural language command generation actually improve terminal workflow?

#### Core Functionality
- [ ] **Invocation mechanism**
  - [ ] Ctrl+Shift+H keyboard shortcut triggers LLM assistance
  - [ ] Alternative: `@hai` prefix detection
  - [ ] Shell integration (bash/zsh compatible)
  - [ ] Input capture and routing

- [ ] **LLM Integration**
  - [ ] Provider abstraction layer (support multiple backends)
  - [ ] OpenAI integration (GPT-4o-mini)
  - [ ] Ollama integration (llama3.2 or similar)
  - [ ] Structured JSON response parsing
  - [ ] Error handling for API failures

- [ ] **Command Execution**
  - [ ] Execute generated commands in current shell context
  - [ ] Capture stdout/stderr output
  - [ ] Preserve environment variables and working directory
  - [ ] Handle command failures gracefully

- [ ] **Dual-Layer Output**
  - [ ] Conversation layer: LLM reasoning and explanations
  - [ ] Execution layer: Actual bash commands + output
  - [ ] Visual distinction (ANSI colors, separators, basic formatting)
  - [ ] Clear separation between "thinking" and "doing"

- [ ] **System Prompt Engineering**
  - [ ] Minimal, focused prompt for command generation
  - [ ] JSON response format specification
  - [ ] Context injection (CWD, git state, env vars)
  - [ ] Command safety guidelines

#### Configuration
- [ ] Config file structure (`~/.hai/config.yaml`)
- [ ] Settings management:
  - [ ] LLM provider selection (openai/anthropic/ollama/local)
  - [ ] API keys (secure storage)
  - [ ] Default model selection
  - [ ] Base URL for local/self-hosted models
- [ ] Config validation and error messages
- [ ] First-run setup wizard (optional)

#### Context Awareness
- [ ] Current working directory detection
- [ ] Git state detection:
  - [ ] Current branch
  - [ ] Repository detection
  - [ ] Clean/dirty status
- [ ] Basic environment variables:
  - [ ] USER
  - [ ] HOME
  - [ ] SHELL
  - [ ] PATH

#### Safety & UX
- [ ] Simple execution model (user controls when commands run)
- [ ] No auto-execution in v0.1 (explicit user confirmation)
- [ ] Clear error messages
- [ ] Helpful usage instructions

#### Testing & Validation
- [ ] Test suite setup (pytest)
- [ ] Mock LLM responses for consistent testing
- [ ] Integration tests with real shell
- [ ] **5+ realistic use cases validated**:
  - [ ] Find files by criteria (date, size, type)
  - [ ] Git workflow operations
  - [ ] Process management queries
  - [ ] File operations with complex flags
  - [ ] System information gathering

#### Documentation
- [ ] Installation instructions
- [ ] Configuration guide
- [ ] Usage examples
- [ ] Troubleshooting guide

#### Success Criteria
- ✅ Can invoke from bash/zsh prompt
- ✅ Can configure ≥2 LLM providers (1 local, 1 remote)
- ✅ Output shows both "thinking" and "doing" layers
- ✅ At least 5 realistic use cases work end-to-end
- ✅ Setup takes <5 minutes
- ✅ Response time <5 seconds for simple queries
- ✅ Daily use by maintainer (dogfooding validation)

---

## Planned Versions

### v0.2 - Enhanced Context & Memory

**Goal**: Make LLM more effective with better context
**Status**: PLANNED

#### Features
- [ ] **Expanded Context Collection**
  - [ ] Recent command history (last N commands from shell history)
  - [ ] Current shell session exported variables
  - [ ] Active shell aliases
  - [ ] File listings for CWD (when relevant to query)
  - [ ] Detailed git status (dirty files, ahead/behind counts, stash list)

- [ ] **Hybrid Memory Model**
  - [ ] **Session memory**: Conversation context (cleared on new terminal)
  - [ ] **Directory memory**: Project-specific context (`.hai/context.json`)
  - [ ] **Persistent preferences**: User command patterns and styles
  - [ ] Memory cleanup and size management

- [ ] **Smart Context Injection**
  - [ ] Relevance detection (don't send unnecessary context)
  - [ ] Token budget management
  - [ ] Context summarization for long histories

#### Technical Enhancements
- [ ] Context caching for performance
- [ ] Async context collection
- [ ] Context storage format and schema

#### Success Criteria
- ✅ LLM generates more accurate commands using history
- ✅ Project-specific patterns recognized and reused
- ✅ User preferences learned and applied
- ✅ No significant performance degradation
- ✅ Context size stays within token limits

---

### v0.3 - Smart Execution

**Goal**: Add intelligence around when to auto-execute vs. confirm
**Status**: PLANNED

#### Features
- [ ] **Confidence Scoring System**
  - [ ] LLM returns confidence level (0-100) with each command
  - [ ] Confidence calibration based on query complexity
  - [ ] Historical accuracy tracking

- [ ] **Execution Modes**
  - [ ] `auto` mode (≥90% confidence): Execute immediately
  - [ ] `confirm` mode (70-89% confidence): Show command, prompt Y/n
  - [ ] `suggest` mode (<70% confidence): Show alternatives, don't execute
  - [ ] Mode override flags (--auto, --confirm, --suggest)

- [ ] **Configurable Thresholds**
  - [ ] User-defined confidence boundaries
  - [ ] Per-directory threshold overrides
  - [ ] Learning from user confirmations/rejections

- [ ] **Command Categorization**
  - [ ] **Read-only operations** (ls, cat, git status, find) → auto
  - [ ] **Write operations** (git commit, mkdir, touch) → confirm
  - [ ] **Destructive operations** (rm -rf, git push --force) → always confirm
  - [ ] Pattern-based categorization rules
  - [ ] User-extensible category definitions

#### UX Enhancements
- [ ] Confirmation prompts with command preview
- [ ] Ability to edit command before execution
- [ ] Quick-confirm shortcuts (Enter = yes)

#### Success Criteria
- ✅ 90%+ of read-only commands auto-execute correctly
- ✅ Zero unintended destructive operations
- ✅ User can customize thresholds to match risk tolerance
- ✅ Confidence scores correlate with actual accuracy

---

### v0.4 - Permissions Framework

**Goal**: Granular control over what can be executed
**Status**: PLANNED

#### Features
- [ ] **Permission Rules Configuration**
  - [ ] Allowlist patterns (commands that can auto-execute)
  - [ ] Denylist patterns (commands that are blocked)
  - [ ] Per-directory permission overrides
  - [ ] Wildcard and regex pattern support

- [ ] **Permission File** (`~/.hai/permissions.json`)
  - [ ] Global rules
  - [ ] Directory-specific rules
  - [ ] Project-level permission files (`.hai/permissions.json`)
  - [ ] Permission inheritance and override logic

- [ ] **Claude Code-Inspired Model**
  - [ ] Similar permission UX to Claude Code
  - [ ] Progressive permission requests
  - [ ] Permission memory (remember user choices)

- [ ] **Safety Features**
  - [ ] Dangerous command detection (sudo rm, curl | bash, etc.)
  - [ ] Confirmation requirements for high-risk operations
  - [ ] Permission violation logging
  - [ ] "Training mode" to build allowlist

#### Example Permission Rules
```json
{
  "auto_execute": [
    "git status",
    "git log*",
    "git diff*",
    "ls*",
    "cat*",
    "find*",
    "grep*"
  ],
  "always_confirm": [
    "git push*",
    "git commit*",
    "rm*",
    "mv*",
    "cp*"
  ],
  "denied": [
    "rm -rf /*",
    "sudo rm*",
    "> /dev/sda*",
    "dd if=*"
  ],
  "per_directory": {
    "/home/frankbria/projects/production": {
      "auto_execute": [],
      "always_confirm": ["*"]
    }
  }
}
```

#### Success Criteria
- ✅ Users can define custom permission boundaries
- ✅ Zero accidental execution of denied commands
- ✅ Per-directory rules work correctly
- ✅ Permission system doesn't create excessive friction
- ✅ Clear feedback when permissions block actions

---

### v0.5 - Error Handling

**Goal**: Recover gracefully from failures
**Status**: PLANNED

#### Features
- [ ] **Automatic Error Detection**
  - [ ] Non-zero exit code detection
  - [ ] stderr pattern recognition
  - [ ] Command-specific error detection

- [ ] **Intelligent Error Analysis**
  - [ ] LLM analyzes error output
  - [ ] Root cause identification
  - [ ] Solution suggestions
  - [ ] Common error pattern database

- [ ] **Retry Logic**
  - [ ] 2-3 automatic retry attempts
  - [ ] Progressive retry strategies
  - [ ] User confirmation for retry attempts
  - [ ] Backoff between retries

- [ ] **Model Upgrade Strategy**
  - [ ] Initial command: Fast/cheap model (e.g., GPT-4o-mini, llama3.2)
  - [ ] Error correction: Stronger model (e.g., GPT-4o, Claude Sonnet)
  - [ ] Cost-effective: Pay for intelligence only when needed
  - [ ] Configurable model tiers

- [ ] **Error Recovery Workflows**
  - [ ] Suggested fix commands
  - [ ] Rollback capabilities (where possible)
  - [ ] Learning from errors (pattern database)

#### Post-v1.0 Enhancement
- [ ] Smart/adaptive retry logic based on error type and confidence
- [ ] Historical error success rate tracking
- [ ] Predictive error prevention

#### Success Criteria
- ✅ 80%+ of common errors automatically resolved
- ✅ Model upgrade reduces error resolution cost
- ✅ Clear communication of error causes
- ✅ User maintains control over retry decisions
- ✅ No infinite retry loops

---

### v0.6 - Multi-Step Workflows

**Goal**: Handle complex command sequences
**Status**: PLANNED

#### Features
- [ ] **Workflow Detection**
  - [ ] LLM identifies multi-step requirements
  - [ ] Command sequence generation
  - [ ] Dependency analysis between steps

- [ ] **Workflow Execution**
  - [ ] Display full workflow before execution
  - [ ] User approval for entire sequence
  - [ ] Step-by-step execution with progress indication
  - [ ] Conditional execution (if step X succeeds, do Y)

- [ ] **Checkpointing**
  - [ ] Save state before each step (optional)
  - [ ] Rollback to checkpoint on failure
  - [ ] Checkpoint cleanup after success

- [ ] **Rollback Capability**
  - [ ] Detect reversible operations
  - [ ] Generate undo commands
  - [ ] Automatic rollback on mid-sequence failure
  - [ ] Manual rollback commands

#### Example Workflows
- Stash changes → switch branch → commit file → return to branch → pop stash
- Create feature branch → make changes → commit → push → create PR
- Backup directory → clean old files → verify space → restore if needed

#### Success Criteria
- ✅ Can execute 5+ step workflows reliably
- ✅ Rollback works for common operation types
- ✅ Clear progress indication during execution
- ✅ Failures don't leave system in broken state
- ✅ User can review entire workflow before execution

---

### v0.7 - Advanced Output & UX

**Goal**: Polish the user experience
**Status**: PLANNED

#### Features
- [ ] **TUI Framework**
  - [ ] Rich library integration or Textual framework
  - [ ] Interactive UI components
  - [ ] Responsive layout

- [ ] **Enhanced Visuals**
  - [ ] Syntax highlighting for bash commands
  - [ ] Color-coded output (success/error/warning)
  - [ ] Better visual separation of conversation/execution layers
  - [ ] Progress indicators for long operations
  - [ ] Spinners and status animations

- [ ] **Keyboard Shortcuts**
  - [ ] Quick approve (Enter)
  - [ ] Edit before execute (E)
  - [ ] Cancel operation (Ctrl+C)
  - [ ] Show history (Up/Down arrows)
  - [ ] Copy command to clipboard (Ctrl+Shift+C)

- [ ] **Alternative Invocation**
  - [ ] Ctrl+Tab mode-switch (enter/exit hai mode)
  - [ ] Persistent assistant mode
  - [ ] Quick-toggle between normal and assisted shell

#### UX Improvements
- [ ] Helpful inline suggestions
- [ ] Command explanation tooltips
- [ ] Smart autocomplete
- [ ] Multi-line input support

#### Success Criteria
- ✅ Output is visually appealing and clear
- ✅ Keyboard shortcuts speed up common operations
- ✅ User can switch modes fluidly
- ✅ No degradation in terminal performance
- ✅ Accessible color schemes (supports terminal themes)

---

### v0.8 - Dry-Run & Undo

**Goal**: Safety features for experimentation
**Status**: PLANNED

#### Features
- [ ] **Dry-Run Mode**
  - [ ] `--dry-run` flag shows what would happen
  - [ ] Simulated execution output
  - [ ] Impact analysis (files affected, permissions needed)
  - [ ] No actual changes made

- [ ] **Checkpoint System**
  - [ ] Save file/directory state before operations
  - [ ] Capture git state snapshots
  - [ ] Minimal storage overhead
  - [ ] Automatic cleanup of old checkpoints

- [ ] **Undo Command**
  - [ ] Revert last operation (where possible)
  - [ ] Restore from checkpoint
  - [ ] Operation-specific undo strategies
  - [ ] Clear communication of undo limitations

- [ ] **Undo History**
  - [ ] Track last N operations (configurable)
  - [ ] Browse undo history
  - [ ] Selective undo (choose which operation to revert)

#### Undo Capabilities
- File operations: Restore from checkpoint
- Git operations: Use git reflog and reset
- Package installations: Track and uninstall
- Config changes: Keep backups

#### Success Criteria
- ✅ Dry-run accurately predicts command effects
- ✅ Undo works for 90%+ of common operations
- ✅ Checkpoint overhead is minimal (<1% storage)
- ✅ Clear feedback on what can/cannot be undone
- ✅ User confidence in experimenting increases

---

### v0.9 - Model Intelligence

**Goal**: Optimize model routing for cost and performance
**Status**: PLANNED

#### Features
- [ ] **Context-Aware Model Selection**
  - [ ] Query complexity analysis
  - [ ] Simple queries → local/fast models
  - [ ] Complex workflows → powerful cloud models
  - [ ] Error correction → stronger models
  - [ ] User preference learning

- [ ] **Multiple Models Per Provider**
  - [ ] Model registry with capabilities
  - [ ] Automatic model selection based on task
  - [ ] Model fallback chains
  - [ ] Performance tracking per model

- [ ] **Cost Tracking**
  - [ ] Token usage monitoring
  - [ ] API cost calculation
  - [ ] Daily/monthly cost reports
  - [ ] Budget alerts and limits

- [ ] **Fallback Chains**
  - [ ] Primary: Local model (free)
  - [ ] Secondary: Cloud small model (cheap)
  - [ ] Tertiary: Cloud large model (expensive)
  - [ ] Automatic fallback on failure or low confidence

#### Model Routing Examples
- "Show me large files" → llama3.2 (local)
- "Git workflow with stash" → GPT-4o-mini (cloud, cheap)
- "Complex error debugging" → Claude Sonnet (cloud, smart)
- "Multi-step deployment" → GPT-4o (cloud, reliable)

#### Success Criteria
- ✅ Monthly API cost <$5 for typical use
- ✅ Local model handles 60%+ of queries
- ✅ Model selection doesn't create noticeable latency
- ✅ Fallback chains prevent total failures
- ✅ Cost tracking helps users stay on budget

---

### v1.0 - Production Ready

**Goal**: Stable, polished, safe for daily use
**Status**: PLANNED

#### Features
- [ ] **Comprehensive Error Handling**
  - [ ] Graceful degradation in all failure modes
  - [ ] Helpful error messages
  - [ ] Recovery suggestions
  - [ ] Error reporting mechanism

- [ ] **Logging & Debugging**
  - [ ] Structured logging framework
  - [ ] Debug mode (`--debug` flag)
  - [ ] Log rotation and cleanup
  - [ ] Privacy-safe logging (no API keys)

- [ ] **Documentation**
  - [ ] Complete user guide
  - [ ] Installation instructions for all platforms
  - [ ] Configuration reference
  - [ ] Troubleshooting guide
  - [ ] FAQ
  - [ ] Video tutorials (optional)

- [ ] **Installation**
  - [ ] PyPI package
  - [ ] One-command installation script
  - [ ] Platform-specific packages (brew, apt, etc.)
  - [ ] Shell integration helpers
  - [ ] Update mechanism

- [ ] **Test Suite**
  - [ ] Unit tests (>85% coverage)
  - [ ] Integration tests (real shell interactions)
  - [ ] Mock LLM responses for consistency
  - [ ] Performance benchmarks
  - [ ] Cross-platform testing (bash, zsh, fish)

- [ ] **Security Audit**
  - [ ] API key storage review
  - [ ] Permission model validation
  - [ ] Command injection prevention
  - [ ] Secure defaults
  - [ ] Third-party security review (optional)

- [ ] **Performance Optimization**
  - [ ] Startup time <100ms
  - [ ] Context collection <50ms
  - [ ] Response rendering <10ms
  - [ ] Memory footprint <50MB
  - [ ] Lazy loading for heavy dependencies

- [ ] **Telemetry (Opt-In)**
  - [ ] Usage statistics (anonymous)
  - [ ] Error reporting
  - [ ] Feature usage tracking
  - [ ] Performance metrics
  - [ ] Clear opt-in/opt-out mechanism

#### Quality Gates
- [ ] Zero critical bugs
- [ ] <5 known minor bugs
- [ ] 95%+ success rate on common tasks
- [ ] All documentation complete
- [ ] Security review passed
- [ ] Performance benchmarks met

#### Success Criteria
- ✅ Daily use by 100+ users (community adoption)
- ✅ <0.1% bug reports per active user
- ✅ 95%+ user satisfaction (via feedback)
- ✅ Stable on major platforms (macOS, Linux, WSL)
- ✅ Clear upgrade path to future versions
- ✅ Comprehensive documentation maintained

---

## Long-Term Vision (Post-1.0)

### Advanced Sandbox Integration

**Goal**: Safe execution environments for untrusted operations

#### Features
- [ ] **E2B Environment Support**
  - [ ] Cloud sandbox integration
  - [ ] Isolated execution environments
  - [ ] Automatic cleanup

- [ ] **Daytona Workspace Integration**
  - [ ] Developer workspace synchronization
  - [ ] Team environment sharing

- [ ] **Bubblewrap Native Sandboxing**
  - [ ] Linux namespace isolation
  - [ ] Local sandboxing without cloud dependencies

- [ ] **Docker Container Support**
  - [ ] Container-based isolation
  - [ ] Image management
  - [ ] Volume mapping

- [ ] **Environment Upload/Sync**
  - [ ] Context synchronization across environments
  - [ ] State transfer between local and sandbox
  - [ ] Configuration replication

---

### Agent Framework

**Goal**: Transform into sophisticated agent platform

#### Features
- [ ] **MCP Server Integration**
  - [ ] Model Context Protocol support
  - [ ] External tool integration
  - [ ] API endpoint management

- [ ] **Multi-Agent Coordination**
  - [ ] Specialized agents for different tasks
  - [ ] Agent-to-agent communication
  - [ ] Collaborative problem solving

- [ ] **Long-Running Background Tasks**
  - [ ] Daemon mode for persistent operations
  - [ ] Background job management
  - [ ] Progress monitoring and notifications

- [ ] **Cron Job Management**
  - [ ] Natural language cron setup
  - [ ] Scheduled task monitoring
  - [ ] Job history and logs

- [ ] **Webhook/Trigger Support**
  - [ ] Event-driven automation
  - [ ] External system integration
  - [ ] Notification channels

---

### Advanced Intelligence

**Goal**: Learning and adaptive system

#### Features
- [ ] **Pattern Learning**
  - [ ] Learn from user command patterns
  - [ ] Predict common workflows
  - [ ] Personalized suggestions

- [ ] **Custom Command Libraries**
  - [ ] User-defined command templates
  - [ ] Shareable command libraries
  - [ ] Community command repository

- [ ] **Smart/Adaptive Error Retry**
  - [ ] Machine learning for error pattern recognition
  - [ ] Adaptive retry strategies
  - [ ] Success rate optimization

- [ ] **IDE Integration**
  - [ ] VS Code extension
  - [ ] JetBrains plugin
  - [ ] Terminal emulator plugins

- [ ] **Team/Shared Configurations**
  - [ ] Team permission templates
  - [ ] Shared command libraries
  - [ ] Organizational best practices
  - [ ] *Only if demand emerges* (individual focus first)

---

## Metrics & Success Tracking

### v0.1 Metrics
- **Functionality**: 5+ realistic use cases work end-to-end
- **Usability**: Can be invoked in <2 seconds
- **Configuration**: Setup takes <5 minutes

### v1.0 Metrics
- **Reliability**: 95%+ success rate on common tasks
- **Safety**: Zero accidental destructive operations in testing
- **Performance**: <3 second response time for simple queries (local model)
- **Adoption**: Daily use by developer (dogfooding)

### Long-Term Metrics
- **Efficiency**: 50%+ reduction in "leaving terminal to look up commands"
- **Complexity**: Can handle 80% of multi-step workflows
- **Cost**: <$5/month in API costs with hybrid local/remote strategy
- **Community**: 1000+ GitHub stars, 100+ active users
- **Reliability**: 99%+ uptime for cloud components

---

## Contributing to the Roadmap

This roadmap is a living document. As development progresses:

1. **Completed features** are checked off and moved to version history
2. **In-progress work** is clearly marked
3. **User feedback** shapes future version priorities
4. **Competitive analysis** may introduce new features
5. **Technical discoveries** may adjust implementation approaches

### Feedback Channels
- **GitHub Issues**: https://github.com/frankbria/hai-cli/issues
- **Discussions**: https://github.com/frankbria/hai-cli/discussions
- **PRs**: Contributions welcome for any version

---

## Version Naming Convention

- **v0.x**: Pre-release, rapid iteration, breaking changes expected
- **v1.0**: First production-ready release, stability commitment
- **v1.x**: Incremental improvements, backward compatible
- **v2.0+**: Major architectural changes, may break compatibility

---

**Next Milestone**: v0.1 - Proof of Concept
**Focus**: Validate that natural language command generation improves terminal workflow
**Timeline**: Agile approach - ship when ready, validate before advancing

---

*Last Updated: 2025-12-19*
*Maintained by: frankbria*
*See [PRD.md](./PRD.md) for detailed technical specifications*
