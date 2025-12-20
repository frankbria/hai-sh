# hai-sh Usage Guide

Practical examples and tutorial for using hai-sh, your AI-powered terminal assistant.

## Table of Contents

- [Getting Started](#getting-started)
- [Invocation Methods](#invocation-methods)
- [Understanding Dual-Layer Output](#understanding-dual-layer-output)
- [Example Categories](#example-categories)
  - [File Operations](#file-operations)
  - [Git Workflows](#git-workflows)
  - [System Information](#system-information)
  - [Process Management](#process-management)
  - [Development Tasks](#development-tasks)
  - [Text Processing](#text-processing)
- [Common Workflows](#common-workflows)
- [Tips and Best Practices](#tips-and-best-practices)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting Queries](#troubleshooting-queries)

---

## Getting Started

### Your First Query

After installing hai-sh (see [INSTALL.md](./INSTALL.md)), try your first query:

```bash
hai "show me the current directory"
```

**What happens:**
1. hai reads your query
2. Gathers context (current directory, git state, environment)
3. Sends to LLM (OpenAI, Anthropic, or Ollama)
4. LLM generates explanation + command
5. hai displays the result in dual-layer format

**Example output:**
```
━━━ Conversation ━━━
I'll show you the current directory using pwd.

Confidence: 95% [█████████·]

═══════════════════
━━━ Execution ━━━
$ pwd
/home/user/projects/hai-sh
```

### 5-Minute Quickstart

1. **Try a simple query:**
   ```bash
   hai "list files in this directory"
   ```

2. **Try with @hai prefix:**
   ```bash
   @hai show me large files
   ```

3. **Use keyboard shortcut:**
   - Type: `find TypeScript files`
   - Press: `Ctrl+X Ctrl+H` (default binding)

4. **Explore your system:**
   ```bash
   hai "what's taking up disk space?"
   ```

5. **Git workflow:**
   ```bash
   hai "show me uncommitted changes"
   ```

**Congratulations!** You're now using AI to help with terminal commands.

---

## Invocation Methods

hai supports three ways to invoke it:

### Method 1: Direct Command (Recommended for Learning)

Use the `hai` command directly:

```bash
hai "your natural language query"
```

**Examples:**
```bash
hai "find large files"
hai "show git status"
hai "list running processes"
```

**Best for:**
- Learning hai
- Testing queries
- Scripts and automation
- One-off commands

---

### Method 2: @hai Prefix (Recommended for Daily Use)

Type `@hai` followed by your query:

```bash
@hai find files modified today
@hai what's my git branch?
@hai show disk usage
```

**How it works:**
- Shell integration detects `@hai` prefix
- Automatically routes to hai
- Natural typing flow

**Setup:** Requires shell integration (see [INSTALL.md](./INSTALL.md))

**Best for:**
- Daily terminal use
- Quick queries
- Natural workflow

---

### Method 3: Keyboard Shortcut (Recommended for Speed)

Type your query, then press the keyboard shortcut:

**Default:** `Ctrl+X Ctrl+H`

**Example workflow:**
```bash
# 1. Type your query (no @hai needed)
find large log files

# 2. Press Ctrl+X Ctrl+H

# 3. hai processes and suggests command
━━━ Conversation ━━━
I'll search for large log files using find.

$ find /var/log -type f -size +10M
```

**Custom key bindings:**
```bash
# In ~/.bashrc or ~/.zshrc
export HAI_KEY_BINDING="\C-h"  # Use Ctrl+H
# or
export HAI_KEY_BINDING="\eh"   # Use Alt+H
```

**Best for:**
- Speed users
- Frequent hai use
- Minimal typing

---

## Understanding Dual-Layer Output

hai uses a unique **dual-layer** output format that shows both the AI's reasoning and the actual command.

### Layer 1: Conversation (AI Reasoning)

```
━━━ Conversation ━━━
I'll search for files modified in the last 24 hours using find with
the -mtime flag.

Confidence: 90% [█████████·]
```

**What it shows:**
- AI's understanding of your query
- Explanation of what it will do
- Confidence score (0-100%)
- Visual confidence bar

**Why it's useful:**
- **Learning**: Understand what commands do
- **Transparency**: See AI's reasoning
- **Trust**: Verify before executing

---

### Layer 2: Execution (Command)

```
═══════════════════
━━━ Execution ━━━
$ find . -type f -mtime -1
./README.md
./src/app.py
./tests/test_app.py
```

**What it shows:**
- The actual bash command
- Command output (if executed)
- Exit status

**Why it's useful:**
- **Copy-paste**: Grab the command
- **Learn**: See the syntax
- **Verify**: Check output

---

### Toggling Layers

You can customize which layers to show:

```yaml
# In ~/.hai/config.yaml
output:
  show_conversation: true   # Show AI reasoning
  show_reasoning: true      # Show detailed reasoning
  use_colors: true          # Use colors
```

**Execution-only mode** (for scripts):
```yaml
output:
  show_conversation: false  # Command only
```

---

## Example Categories

### File Operations

#### Example 1: Find Large Files

**Query:**
```bash
hai "show me files larger than 100MB"
```

**Output:**
```
━━━ Conversation ━━━
I'll search for files larger than 100MB and sort them by size.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ find ~ -type f -size +100M -exec du -h {} + | sort -rh | head -20
1.2G    /home/user/videos/movie.mp4
856M    /home/user/downloads/ubuntu.iso
234M    /home/user/.cache/spotify/Data/1234.cache
```

**Variations:**
```bash
hai "find files larger than 1GB in my home directory"
hai "show me the 10 biggest files"
hai "find large video files"
```

---

#### Example 2: Find Files Modified Recently

**Query:**
```bash
hai "show files modified in the last 24 hours"
```

**Output:**
```
━━━ Conversation ━━━
I'll find all files modified in the last 24 hours using find with -mtime -1.

Confidence: 95% [█████████·]

═══════════════════
━━━ Execution ━━━
$ find . -type f -mtime -1
./README.md
./src/app.py
./tests/test_app.py
```

**Variations:**
```bash
hai "find files modified today"
hai "show files changed in the last hour"
hai "find Python files modified this week"
```

---

#### Example 3: Search File Contents

**Query:**
```bash
hai "find all files containing 'TODO'"
```

**Output:**
```
━━━ Conversation ━━━
I'll search for 'TODO' in all files using grep recursively.

Confidence: 95% [█████████·]

═══════════════════
━━━ Execution ━━█
$ grep -r "TODO" .
./src/app.py:# TODO: Add error handling
./README.md:## TODO
./tests/test_app.py:    # TODO: Add more tests
```

**Variations:**
```bash
hai "find all TypeScript files that import React"
hai "search for 'FIXME' in Python files"
hai "find files containing my email address"
```

---

#### Example 4: Count Files and Directories

**Query:**
```bash
hai "how many files are in this directory?"
```

**Output:**
```
━━━ Conversation ━━━
I'll count all files in the current directory recursively.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ find . -type f | wc -l
247
```

**Variations:**
```bash
hai "count Python files in this project"
hai "how many directories are here?"
hai "count lines of code in JavaScript files"
```

---

#### Example 5: Organize Files

**Query:**
```bash
hai "move all PDF files to a folder called docs"
```

**Output:**
```
━━━ Conversation ━━━
I'll create a 'docs' directory and move all PDF files there.

Confidence: 85% [████████··]

═══════════════════
━━━ Execution ━━━
$ mkdir -p docs && find . -maxdepth 1 -name "*.pdf" -exec mv {} docs/ \;
```

**Variations:**
```bash
hai "organize images by year"
hai "move log files to archive folder"
hai "rename all .txt files to .md"
```

---

### Git Workflows

#### Example 6: Check Git Status

**Query:**
```bash
hai "what's the status of my git repo?"
```

**Output:**
```
━━━ Conversation ━━━
I'll show your git repository status including branch, changes, and staging area.

Confidence: 95% [█████████·]

═══════════════════
━━━ Execution ━━━
$ git status
On branch feature/new-ui
Your branch is ahead of 'origin/feature/new-ui' by 2 commits.

Changes not staged for commit:
  modified:   src/app.py
  modified:   README.md

Untracked files:
  tests/test_new_feature.py
```

**Variations:**
```bash
hai "show me uncommitted changes"
hai "what branch am I on?"
hai "show git log for today"
```

---

#### Example 7: Stage and Commit Files

**Query:**
```bash
hai "commit just the README with message 'Update docs'"
```

**Output:**
```
━━━ Conversation ━━━
I'll stage README.md and create a commit with your message.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ git add README.md && git commit -m "Update docs"
[feature/new-ui a1b2c3d] Update docs
 1 file changed, 10 insertions(+), 2 deletions(-)
```

**Variations:**
```bash
hai "stage all Python files"
hai "commit everything with message 'WIP'"
hai "amend the last commit"
```

---

#### Example 8: Branch Management

**Query:**
```bash
hai "create a new branch called feature/auth and switch to it"
```

**Output:**
```
━━━ Conversation ━━━
I'll create and checkout a new branch named feature/auth.

Confidence: 95% [█████████·]

═══════════════════
━━━ Execution ━━━
$ git checkout -b feature/auth
Switched to a new branch 'feature/auth'
```

**Variations:**
```bash
hai "switch to main branch"
hai "delete the old-feature branch"
hai "show all branches"
hai "merge feature-branch into main"
```

---

#### Example 9: View Changes

**Query:**
```bash
hai "show me what changed in the last commit"
```

**Output:**
```
━━━ Conversation ━━━
I'll show the diff for the most recent commit using git show.

Confidence: 95% [█████████·]

═══════════════════
━━━ Execution ━━━
$ git show HEAD
commit a1b2c3d4e5f6 (HEAD -> main)
Author: User <user@example.com>
Date:   Thu Dec 20 14:30:00 2024 -0800

    Update docs

diff --git a/README.md b/README.md
...
```

**Variations:**
```bash
hai "show diff of unstaged changes"
hai "compare with main branch"
hai "show changes in src/app.py"
```

---

#### Example 10: Git History

**Query:**
```bash
hai "show me commits from the last week"
```

**Output:**
```
━━━ Conversation ━━━
I'll show git commits from the last 7 days with one-line summaries.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ git log --since="1 week ago" --oneline
a1b2c3d Update docs
e5f6g7h Add new feature
i9j0k1l Fix bug in auth
m2n3o4p Refactor database module
```

**Variations:**
```bash
hai "show commits by author John"
hai "show commit history for README.md"
hai "find commits mentioning 'bug fix'"
```

---

### System Information

#### Example 11: Disk Space Usage

**Query:**
```bash
hai "what's taking up the most disk space?"
```

**Output:**
```
━━━ Conversation ━━━
I'll show disk usage sorted by size, displaying the largest directories first.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ du -h -d 1 . | sort -rh | head -20
12G     ./videos
4.2G    ./downloads
1.8G    ./.cache
856M    ./projects
234M    ./documents
```

**Variations:**
```bash
hai "show disk space on all drives"
hai "how much free space do I have?"
hai "find large directories in home folder"
```

---

#### Example 12: System Resources

**Query:**
```bash
hai "show me CPU and memory usage"
```

**Output:**
```
━━━ Conversation ━━━
I'll display current CPU and memory usage using top.

Confidence: 85% [████████··]

═══════════════════
━━━ Execution ━━━
$ top -bn1 | head -20
top - 14:35:21 up 5 days,  3:42,  2 users,  load average: 0.52, 0.58, 0.59
Tasks: 298 total,   1 running, 297 sleeping
%Cpu(s):  5.2 us,  1.8 sy,  0.0 ni, 92.7 id,  0.0 wa
MiB Mem :  15842.2 total,   2156.3 free,   8234.1 used
```

**Variations:**
```bash
hai "show system uptime"
hai "what processes are using most CPU?"
hai "show memory usage by process"
```

---

#### Example 13: Network Information

**Query:**
```bash
hai "show my IP address"
```

**Output:**
```
━━━ Conversation ━━━
I'll display your local IP addresses for all network interfaces.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ ip addr show | grep "inet " | grep -v 127.0.0.1
    inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic eth0
```

**Variations:**
```bash
hai "what's my public IP address?"
hai "show active network connections"
hai "test connection to google.com"
```

---

### Process Management

#### Example 14: List Running Processes

**Query:**
```bash
hai "show me what's running on this system"
```

**Output:**
```
━━━ Conversation ━━━
I'll list all running processes with their CPU and memory usage.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ ps aux --sort=-%cpu | head -20
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
user      1234  8.5  2.3 1234567 98765 ?       Sl   Dec19  12:34 /usr/bin/chrome
user      5678  3.2  1.5 876543  54321 ?       Sl   14:30   0:15 /usr/bin/code
```

**Variations:**
```bash
hai "find processes using port 8080"
hai "show Python processes"
hai "which process is using the most memory?"
```

---

#### Example 15: Kill Processes

**Query:**
```bash
hai "kill all Chrome processes"
```

**Output:**
```
━━━ Conversation ━━━
I'll find and terminate all Chrome processes using pkill.

Confidence: 75% [███████···]
⚠️  Warning: This will forcefully kill processes

═══════════════════
━━━ Execution ━━━
$ pkill -f chrome
```

**Variations:**
```bash
hai "stop the process on port 3000"
hai "restart nginx service"
hai "kill process with PID 1234"
```

---

### Development Tasks

#### Example 16: Install Dependencies

**Query:**
```bash
hai "install Python dependencies from requirements.txt"
```

**Output:**
```
━━━ Conversation ━━━
I'll create a virtual environment and install dependencies from requirements.txt.

Confidence: 85% [████████··]

═══════════════════
━━━ Execution ━━━
$ python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

**Variations:**
```bash
hai "install npm dependencies"
hai "update all pip packages"
hai "install pytest and pytest-cov"
```

---

#### Example 17: Run Tests

**Query:**
```bash
hai "run Python tests with coverage"
```

**Output:**
```
━━━ Conversation ━━━
I'll run pytest with coverage reporting.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ pytest --cov=src --cov-report=term-missing
========================= test session starts =========================
collected 47 items

tests/test_app.py ......................................... [ 83%]
tests/test_utils.py ........                              [100%]

---------- coverage: platform linux, python 3.12.3 -----------
Name              Stmts   Miss  Cover   Missing
-----------------------------------------------
src/app.py          156      8    95%   45-52
```

**Variations:**
```bash
hai "run jest tests"
hai "run tests in watch mode"
hai "run only unit tests"
```

---

#### Example 18: Build and Deploy

**Query:**
```bash
hai "build the Docker image and tag it as latest"
```

**Output:**
```
━━━ Conversation ━━━
I'll build a Docker image from the Dockerfile and tag it as latest.

Confidence: 85% [████████··]

═══════════════════
━━━ Execution ━━━
$ docker build -t myapp:latest .
```

**Variations:**
```bash
hai "run npm build for production"
hai "create a production bundle"
hai "deploy to staging server"
```

---

### Text Processing

#### Example 19: Process Log Files

**Query:**
```bash
hai "show me errors from the last 100 lines of the log"
```

**Output:**
```
━━━ Conversation ━━━
I'll extract the last 100 lines and filter for errors.

Confidence: 90% [█████████·]

═══════════════════
━━━ Execution ━━━
$ tail -100 /var/log/app.log | grep -i error
[ERROR] Failed to connect to database
[ERROR] Timeout waiting for response
```

**Variations:**
```bash
hai "count how many times 'ERROR' appears in the log"
hai "show unique IP addresses from access log"
hai "extract all email addresses from file.txt"
```

---

#### Example 20: Data Transformation

**Query:**
```bash
hai "convert CSV to JSON"
```

**Output:**
```
━━━ Conversation ━━━
I'll use python to convert the CSV file to JSON format.

Confidence: 80% [████████··]

═══════════════════
━━━ Execution ━━━
$ python3 -c "import csv, json, sys; print(json.dumps(list(csv.DictReader(sys.stdin))))" < data.csv
```

**Variations:**
```bash
hai "sort file by second column"
hai "remove duplicate lines from file"
hai "merge multiple JSON files"
```

---

## Common Workflows

### Workflow 1: Daily Development Routine

```bash
# 1. Check project status
hai "show git status and recent commits"

# 2. Update dependencies
hai "pull latest from main and install dependencies"

# 3. Run tests
hai "run tests with coverage"

# 4. Create feature branch
hai "create branch feature/new-widget and switch to it"

# 5. After coding...
hai "stage all changes and commit with message 'Add new widget'"

# 6. Push changes
hai "push current branch to remote"
```

---

### Workflow 2: Debugging Production Issue

```bash
# 1. Check system resources
hai "show CPU and memory usage"

# 2. Find error logs
hai "show errors from last hour in /var/log/app.log"

# 3. Find problem process
hai "which process is using port 8080?"

# 4. Check connections
hai "show active network connections"

# 5. Restart service
hai "restart the application service"
```

---

### Workflow 3: Code Review Preparation

```bash
# 1. Update from main
hai "fetch latest from origin and rebase on main"

# 2. Check what changed
hai "show diff with main branch"

# 3. Run linters
hai "run eslint on all JavaScript files"

# 4. Run tests
hai "run full test suite"

# 5. Create PR
hai "push branch and show me the GitHub PR URL"
```

---

### Workflow 4: Server Maintenance

```bash
# 1. Check disk space
hai "show disk usage on all mounted drives"

# 2. Find large files
hai "find files larger than 1GB in /var"

# 3. Clean old logs
hai "delete log files older than 30 days in /var/log"

# 4. Check running services
hai "show status of all systemd services"

# 5. Update system
hai "update all packages and reboot if needed"
```

---

## Tips and Best Practices

### 1. Be Specific

**❌ Vague:**
```bash
hai "find files"
```

**✅ Specific:**
```bash
hai "find Python files modified in the last week"
```

**Why:** More context = better commands

---

### 2. Include Context in Your Query

**❌ Generic:**
```bash
hai "install dependencies"
```

**✅ Contextual:**
```bash
hai "install dependencies from package.json"
hai "install Python requirements in a virtual environment"
```

**Why:** hai generates language-specific commands

---

### 3. Ask for Explanations

**Query:**
```bash
hai "explain what this command does: find . -name '*.js' -exec grep -l 'import React' {} \;"
```

**Output:**
```
━━━ Conversation ━━━
This command searches for JavaScript files and finds which ones import React:
- find . -name '*.js': Find all .js files
- -exec grep -l 'import React' {} \;: Run grep on each file
- grep -l: Show only filenames (not content)
- 'import React': Search pattern

Confidence: 95% [█████████·]
```

---

### 4. Use Natural Language

hai understands natural queries. You don't need to know bash syntax.

**Natural queries work:**
```bash
hai "show me large files"
hai "what's using all my disk space?"
hai "find TypeScript files that import React"
hai "how many Python files are in this project?"
```

---

### 5. Iterate and Refine

If the first command isn't perfect, refine your query:

```bash
# First attempt
hai "find large files"
$ find ~ -size +100M

# Too broad, refine
hai "find large video files in Downloads"
$ find ~/Downloads -name "*.mp4" -o -name "*.mkv" -size +100M

# Perfect!
```

---

### 6. Learn from the Output

Pay attention to the Conversation layer:

```
━━━ Conversation ━━━
I'll use find with -mtime -1 to get files from the last 24 hours.
The -type f ensures we only get files, not directories.
```

**You learn:**
- `-mtime -1` = last 24 hours
- `-type f` = files only

Next time you might write the command yourself!

---

### 7. Check Confidence Scores

Low confidence? Double-check before executing:

```
Confidence: 45% [████······]  ⚠️ Low confidence - verify command
```

**What to do:**
- Read the command carefully
- Understand what it does
- Test in safe environment first

---

### 8. Use hai for Learning

**Query:**
```bash
hai "teach me how to use grep"
```

**Query:**
```bash
hai "what's the difference between -exec and -execdir in find?"
```

hai is a learning tool!

---

### 9. Combine with Existing Knowledge

You can provide partial commands:

```bash
hai "find . -name '*.py' | <what comes next to count them?>"
```

**Output:**
```
━━━ Conversation ━━━
To count the results, pipe to wc -l

═══════════════════
━━━ Execution ━━━
$ find . -name '*.py' | wc -l
```

---

### 10. Save Useful Commands

When hai generates a great command:

```bash
# Add to your aliases
echo "alias findlarge='find . -type f -size +100M -exec du -h {} + | sort -rh'" >> ~/.bashrc
```

---

## Advanced Usage

### Multi-Step Commands

hai can generate multi-step workflows:

**Query:**
```bash
hai "create a Python project with venv, install pytest, and run tests"
```

**Output:**
```
━━━ Conversation ━━━
I'll create a virtual environment, install pytest, and run tests.

Confidence: 85% [████████··]

═══════════════════
━━━ Execution ━━━
$ python3 -m venv .venv && \
  source .venv/bin/activate && \
  pip install pytest && \
  pytest
```

---

### Conditional Commands

**Query:**
```bash
hai "run tests and if they pass, commit with message 'Tests passing'"
```

**Output:**
```
━━━ Conversation ━━━
I'll run pytest and only commit if tests pass (exit code 0).

Confidence: 80% [████████··]

═══════════════════
━━━ Execution ━━━
$ pytest && git commit -am "Tests passing"
```

---

### Complex Pipelines

**Query:**
```bash
hai "find JavaScript files, count lines in each, sort by size, show top 10"
```

**Output:**
```
━━━ Conversation ━━━
I'll create a pipeline to count lines and sort files by size.

Confidence: 85% [████████··]

═══════════════════
━━━ Execution ━━━
$ find . -name "*.js" -exec wc -l {} + | sort -rn | head -10
```

---

### Using Variables

**Query:**
```bash
hai "for each Python file, show the number of functions defined"
```

**Output:**
```
━━━ Conversation ━━━
I'll count function definitions in each Python file.

Confidence: 80% [████████··]

═══════════════════
━━━ Execution ━━━
$ find . -name "*.py" -exec sh -c 'echo "$1: $(grep -c "^def " "$1")"' _ {} \;
```

---

## Troubleshooting Queries

### If Command Seems Wrong

**Check the confidence score:**
```
Confidence: 35% [███·······]  ⚠️ Very low - command may be incorrect
```

**Rephrase your query:**
```bash
# Vague
hai "do stuff with files"

# Specific
hai "move all PDF files to docs folder"
```

---

### If Output is Too Long

**Add constraints:**
```bash
# Too much output
hai "show all log entries"

# Better
hai "show last 50 lines of error log"
```

---

### If Command Doesn't Execute

**Check you have permissions:**
```bash
hai "check if I have permission to write to /var/log"
```

**Check the command exists:**
```bash
hai "check if docker is installed"
```

---

### If Context is Wrong

hai uses your current directory and git state. Verify:

```bash
pwd  # Check directory
git status  # Check git state
```

Then retry your query.

---

## Next Steps

Now that you understand hai:

1. **Practice:** Try 5-10 queries from this guide
2. **Explore:** Ask hai questions about your own projects
3. **Learn:** Pay attention to the Conversation layer
4. **Configure:** Customize settings in `~/.hai/config.yaml`
5. **Share:** Tell others about useful queries you discover

**Happy hacking with hai!** 🎉

For more information:
- Configuration Guide: [CONFIGURATION.md](./CONFIGURATION.md)
- Installation Guide: [INSTALL.md](./INSTALL.md)
- Issues: https://github.com/frankbria/hai-sh/issues
