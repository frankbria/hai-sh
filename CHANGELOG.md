# Changelog

All notable changes to hai-sh. Versions follow the `version` in
`pyproject.toml`; the newest is at the top.

## Unreleased

Not yet published to PyPI.

### Upgrade notes (from v0.1.4)

- **Your model setting is kept.** If `providers.ollama.model` is still
  `llama3.2`, the old default, hai shows a one-time note in a terminal:
  llama3.2 scored 77% on hai's eval and refused 5 of 7 dangerous requests,
  against 88% and 7 of 7 for `gemma4:e2b`. To switch:
  `hai-model use gemma4:e2b`. hai never edits your config on its own.
- **Ollama now gets new defaults for settings your config doesn't set**:
  `format: "schema"` (replies always follow hai's JSON shape), `temperature: 0`
  and `think: false`. A v0.1.4 config has none of these lines, so it gets them
  too, whatever model it uses. To keep v0.1.4's behaviour, add under
  `providers.ollama`: `format: null`, `temperature: 0.7`, `think: null`.
- **Run `hai-install-shell` again** (then open a new shell) to get the fixed
  Ctrl+X Ctrl+H binding below. pip doesn't update the copy in `~/.hai/`.
- **New configs default to `gemma4:e2b`** (Apache 2.0, a 4.6 GB download).
  It isn't installed by `pip`; hai offers the download the first time you use
  it, or run `hai-model pull gemma4:e2b`.

### Added

- `hai-model` command: `status`, `list`, `pull` and `use`. It shows the
  download size, free disk space and licence before any download, asks first
  (Enter means No), and needs `--yes` when there is no terminal.
- A catalog of tested models (`hai_sh/data/models.yaml`) with eval scores and
  licences: `gemma4:e2b` (default), `qwen2.5-coder:3b` and `phi4-mini`
  (lighter), `gemma4:e4b` (stronger).
- `models.licence_policy` setting (`any` or `commercial`). With `commercial`,
  hai suggests `phi4-mini` instead of the non-commercial `qwen2.5-coder:3b`.
  The default model is always commercial-safe.
- `hai --model NAME` uses another model for one question (also in `--app-mode`).
- When the configured model isn't installed, `hai` offers to download it in a
  terminal, then another installed model, then a cloud provider you have
  already configured (for that one question, after a privacy note), also
  after "see other models" if you cancel there. From the
  Ctrl+X Ctrl+H binding (`--suggest-only`) it returns the usual JSON with an
  empty `command`, a message with the command to run, and exit status 0
  (v0.1.4 exited 1 with an error); in a pipe it prints the command and exits 1. It never downloads without a yes.
- When Ollama isn't installed or running, hai prints the official install
  command or `ollama serve`. It never runs them.
- The setup wizard lists the catalog models, installed ones first, and offers
  the download for the one you pick. If Ollama isn't running yet you can still
  pick, and hai tells you the command to download it later.
- `hai-model use` keeps a `config.yaml.bak`, keeps comments, and replaces the
  config atomically with mode 600, so a full disk or a Ctrl+C can't leave it
  half written. A symlinked config keeps its link; a symlinked backup is
  replaced, never written through. If the folder doesn't allow that, nothing
  is changed and hai says why.
- With `hai --config FILE`, the commands hai suggests include the same
  `--config FILE`.
- Disk check before a download: refuses one that would leave less than 10% of
  the disk free (capped at 20 GB, never below 2 GB), unless `--force`. It
  checks every place Ollama may keep models and goes by the disk with the
  least room above its own reserve.
  Warns when a model would use over 70% of RAM.
- CI runs the tests on Linux and macOS, Python 3.9 and 3.13, plus a job with
  the newest dependency versions.

### Fixed

- The Ctrl+X Ctrl+H binding failed on every query when gum isn't installed:
  hai's "hai is thinking..." line was captured along with the JSON, so the
  shell couldn't parse the reply. `--suggest-only` now writes only the JSON.
- The same binding failed on macOS's system Python 3.9, where urllib3 prints a
  LibreSSL warning on every start. hai now hides that warning; in
  `--suggest-only` it hides all Python warnings.
- The Ctrl+X Ctrl+H binding failed on any reply containing a double quote,
  such as `grep -rn "TODO" .`: it pasted the JSON into Python source, which
  read JSON's `\"` as a Python escape. It now passes the JSON on stdin.
- `hai setup` writes its config with mode 600 from the start (it may hold API
  keys) instead of tightening the mode after writing.
- `hai-model use` leaves the config alone, with a clear message, when the file
  isn't valid YAML, isn't laid out the way hai expects, is a link to its own
  `.bak`, or was saved by something else while hai was updating it or
  downloading the model. "Make this your default model?" also leaves it alone
  if the config now points at another Ollama. If the config can't be written
  (for example a link into a read-only dotfiles folder) or is refused at the
  last moment, the previous `.bak` is kept.
- The llama3.2 notice's switch command names the `--config` file hai read.
- `hai-model` and hai's Ollama messages no longer print a `user:password@`
  part of the Ollama address.
- `hai-model` stops with "Cannot read config" when `providers.ollama.base_url`
  is set but empty (for example `${OLLAMA_URL}` with the variable unset),
  instead of using the local Ollama.
- A download finishes as soon as Ollama reports success.
- The setup wizard checks the Ollama address the way hai will use it, with
  `${VAR}` expanded, and stops without saving if the address expands to
  nothing.
- An unfinished Ollama address (such as `http://[::1`), a `models:` setting
  that isn't a section, or an empty `providers:` line no longer crashes
  `hai-model`. A malformed cloud provider section is skipped when hai offers
  a cloud fallback, and an absurd model size from Ollama reads as unknown.
- `hai-model` stops with "Cannot read config" when `--config` is a link to a
  file that isn't there (for example on an unmounted drive), instead of
  using the defaults.
- In app mode, `--model` now applies to the provider app mode actually uses.
- `hai-model` stops with "Cannot read config" when the config file exists but
  isn't valid, instead of going on with the defaults (and localhost's Ollama).

## v0.1.4 (2026-02-16)

See [README.md](./README.md#whats-new-in-v014-2026-02-16).
