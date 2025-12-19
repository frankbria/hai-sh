# hai

**A friendly shell assistant powered by LLMs**

`hai` (pronounce like "hi") is a thin, context-aware wrapper around bash that brings natural language command generation directly to your terminal. Stop context-switching to look up git commands, bash syntax, or flags—just ask hai.

## 🎯 Quick Start

```bash
# Hit Ctrl+Shift+H and type naturally
"Show me files modified in the last 24 hours"

# Or use the @hai prefix
$ @hai commit just README.md to main, I'm on feature-branch
```

## ✨ Features

- **Seamless Integration**: Invoke with `Ctrl+Shift+H` or `@hai` prefix
- **Context-Aware**: Knows your CWD, git state, history, and environment
- **Local-First**: Supports Ollama and local models to minimize API costs
- **Dual-Layer Output**: See both LLM reasoning and command execution
- **Smart Execution**: Handles multi-step workflows with confidence-based confirmation
- **Safe by Design**: Permission framework inspired by Claude Code

## 🚀 Status

**Current Version:** Pre-release (v0.1 in development)

hai follows an agile development approach with frequent version increments. See the [PRD](./PRD.md) for the full roadmap.

### Roadmap

- **v0.1** - Proof of Concept: Basic invocation, single LLM provider, dual-layer output
- **v0.2** - Enhanced Context: History, session context, hybrid memory model
- **v0.3** - Smart Execution: Confidence scoring, auto-execute vs. confirm
- **v0.4** - Permissions Framework: Granular control over command execution
- **v0.5** - Error Handling: Automatic retry with model upgrade for debugging
- **v1.0** - Production Ready: Polished, tested, documented, secure

See [PRD.md](./PRD.md) for complete requirements and technical architecture.

## 🛠️ Installation

```bash
# Coming soon - v0.1 in development
pip install hai-cli
```

## 📖 Usage

### Invocation Methods

1. **Keyboard Shortcut** (recommended):
   ```bash
   # Press Ctrl+Shift+H, then type your request
   "Find all TypeScript files that import React"
   ```

2. **Prefix Mode**:
   ```bash
   $ @hai what's taking up the most disk space?
   ```

### Example Interactions

**Simple query:**
```bash
$ @hai show me large files in home directory

[Conversation Layer]
I'll search for large files using find and sort by size.

[Execution Layer]
$ find ~ -type f -exec du -h {} + | sort -rh | head -20
```

**Multi-step workflow:**
```bash
$ @hai commit just README.md to main, I'm on feature-branch

[Conversation Layer]
I'll stash changes, switch to main, commit README.md, and return.

Workflow (4 steps):
1. git stash push -m "temp stash"
2. git checkout main
3. git add README.md && git commit -m "Update README"
4. git checkout feature-branch && git stash pop

Execute? [Y/n]: y

[Execution Layer]
[... commands execute ...]

[Conversation Layer]
✓ Done! Back on feature-branch with working changes restored.
```

## 🔧 Configuration

```yaml
# ~/.hai/config.yaml

provider: "ollama"  # openai | anthropic | ollama | local
model: "llama3.2"

providers:
  openai:
    api_key: "sk-..."
    model: "gpt-4o-mini"

  anthropic:
    api_key: "sk-ant-..."
    model: "claude-sonnet-4-5"

  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2"

context:
  include_history: true
  include_git_state: true
```

## 🎯 Design Philosophy

1. **Seamless Integration** - Feel like a natural extension of bash
2. **Local-First** - Support local/Ollama models for cost-effective daily use
3. **Safety** - Clear permission boundaries, confidence-based execution
4. **Transparency** - Always show what's happening (thinking + doing)
5. **Agile Evolution** - Ship working increments frequently

## 🤝 Contributing

Contributions welcome! This project is in early development. See [PRD.md](./PRD.md) for the vision and roadmap.

## 📝 License

This project is licensed under the GNU Affero General Public License v3.0 - see [LICENSE](./LICENSE) for details.

## 🔗 Links

- [Product Requirements Document](./PRD.md)
- [GitHub Issues](https://github.com/frankbria/hai-cli/issues)
- [Discussions](https://github.com/frankbria/hai-cli/discussions)

## 🙏 Inspiration

Built with a similar agile approach to [parallel-cc](https://github.com/frankbria/parallel-cc) - small version increments, frequent shipping, validate as we go.

---

**Status**: 🚧 Under Active Development | v0.1 Coming Soon

Say "hai" to your new shell assistant! 👋
