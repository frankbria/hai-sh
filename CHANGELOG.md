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
- `hai --model NAME` uses another Ollama model for one question.
- When the configured model isn't installed, `hai` offers to download it in a
  terminal, then another installed model, then a cloud provider you have
  already configured (for that one question, after a privacy note). From the
  Ctrl+X Ctrl+H binding it returns a message with the command to run; in a
  pipe it prints the command and exits 1. It never downloads without a yes.
- When Ollama isn't installed or running, hai prints the official install
  command or `ollama serve`. It never runs them.
- The setup wizard lists the catalog models, installed ones first, and offers
  the download for the one you pick.
- Disk check before a download: refuses one that would leave less than 10% of
  the disk free (capped at 20 GB, never below 2 GB), unless `--force`. Warns
  when a model would use over 70% of RAM.
- CI runs the tests on Linux and macOS, Python 3.9 and 3.13, plus a job with
  the newest dependency versions.

### Fixed

- The Ctrl+X Ctrl+H binding failed on every query when gum isn't installed:
  hai's "hai is thinking..." line was captured along with the JSON, so the
  shell couldn't parse the reply. `--suggest-only` now writes only the JSON.

## v0.1.4 (2026-02-16)

See [README.md](./README.md#whats-new-in-v014-2026-02-16).
