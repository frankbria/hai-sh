# Design: finding, installing and switching local models

Status: **proposal**, not implemented. Written 2026-11-28, before v0.1.5.
Owner: Frank Bria. Decisions still open are listed in [section 11](#11-decisions-for-the-maintainer).

## 1. Why this exists

PR #83 made `gemma4:e2b` the default Ollama model. That was the right model,
but it exposed a gap: hai assumes the model is already there. Today:

| Situation | What hai does now (verified on `main` @ 569e428) |
|---|---|
| Ollama not installed or not running | `OllamaProvider.is_available()` fails its `GET /api/tags`, the fallback chain runs out, and the user gets "No providers available". Nothing says how to install Ollama. |
| Ollama running, model not pulled | Availability passes (it only checks that Ollama answers). The first `/api/generate` returns 404 `model '…' not found`, hai raises `OllamaModelNotFoundError` and prints `Run: ollama pull gemma4:e2b`. The user learns about a 4.6 GB download from an error message. |
| User wants another model | Hand-edit `providers.ollama.model` in `~/.hai/config.yaml`. No list of what is installed, no list of what is recommended. |
| Ctrl+X Ctrl+H shell integration (`--suggest-only`) | Same errors, inside a key binding. |
| TUI | `ProviderManager` switches *provider* (ollama/openai/anthropic) but never the model. |

So "we can't just assume everyone has that model" is the requirement. The goal
is that a new user gets from `pip install hai-sh` to a working local model
without reading an error, and never downloads gigabytes without being told.

## 2. Goals and non-goals

**Goals**

1. Detect what the machine has: Ollama present and running, which models are
   pulled, how much disk and memory there is.
2. Install a model only with consent, after showing its download size, disk
   space left and licence.
3. A small CLI to list, pull, pick and set the default model.
4. Sensible behaviour when the default isn't available: offer an installed
   alternative or a cloud provider, never silently.
5. Upgrading from v0.1.4 must not change anyone's model or break their config.
6. The list of recommended models comes from the eval in `eval/`, not from
   opinion, and records the evidence with each entry.

**Non-goals (this design)**

- Shipping model weights inside the package (unchanged decision from #83).
- Installing Ollama itself on the user's machine (see decision D6).
- Model fine-tuning (tracked in ROADMAP.md, Local Model Track).
- The `local` provider. It is accepted by `schema.py` and `config.py` but no
  provider class is registered in `providers/__init__.py`. That is a separate
  cleanup; this design only touches Ollama plus the existing cloud providers.

## 3. User experience at a glance

```
$ pip install hai-sh
$ hai list big files here
hai needs a local model to run.
  Ollama:   running (0.40.18) at http://localhost:11434
  Model:    gemma4:e2b is not installed
  Download: 4.6 GB  (disk free: 212 GB)   Licence: Apache 2.0
  Why this model: 88% on hai's 93-case eval, all 7 dangerous requests refused,
                  4.6 s median on a CPU-only laptop.
Download it now? [y/N/o=other models]
```

`N` prints the exact command and exits. `o` shows the catalog (section 6). `y`
streams a progress bar from Ollama's pull and then answers the original
question.

Everything else goes through one small command:

```
hai-model status            # Ollama state, default model, installed? fits?
hai-model list              # installed models + recommended ones, side by side
hai-model recommend         # best catalog model for this machine
hai-model pull <name>       # consented download with size + progress
hai-model use <name>        # set providers.ollama.model (pulls first if asked)
hai-model remove <name>     # delete a model from Ollama (asks first)
hai --model <name> <query>  # one-shot override, config untouched
```

The command name is decision D1.

## 4. Detection

A new module `hai_sh/models.py` (pure functions, no printing) gathers a
`ModelEnvironment` snapshot. Every probe has a short timeout and degrades to
"unknown" rather than failing.

| Fact | How | Notes |
|---|---|---|
| Ollama binary on PATH | `shutil.which("ollama")` | Only meaningful when `base_url` is local. |
| Ollama server reachable, version | `GET /api/version` (2 s timeout) | Version lets us warn when `format` (JSON schema) needs a newer Ollama. |
| Installed models | `GET /api/tags` → `name`, `size` (bytes on disk), `details.parameter_size`, `details.quantization_level`, `digest` | Already called by `is_available()`; reuse the response instead of calling twice. |
| Model capabilities | `POST /api/show` → `capabilities` | Lets hai skip `think` for models without the "thinking" capability instead of relying on the 400-and-retry in `OllamaProvider`. Optional. |
| Loaded now | `GET /api/ps` | Only for `status`, to explain a slow first answer (cold load). |
| Disk free | `shutil.disk_usage()` on the Ollama models directory | Directory: `$OLLAMA_MODELS` if set, else `~/.ollama/models`; Linux service installs keep it under the `ollama` user's home (`/usr/share/ollama/.ollama/models`). Probe in that order, use the first that exists. Skip entirely when `base_url` is not localhost: the disk that matters is on another machine. |
| Total RAM | Linux `/proc/meminfo` `MemTotal`; macOS `sysctl -n hw.memsize` | Same remote caveat. No new dependency (no psutil). |
| GPU | Not probed | Ollama decides offload itself; hai only needs "will it fit and how slow". |

**Name matching.** Ollama reports `llama3.2:latest` for a config value of
`llama3.2`. Normalise both sides: add `:latest` when there is no tag, compare
case-sensitively otherwise, and keep `hf.co/...` names as they are. This
matters for "is the default installed?" and is a common source of false
"missing" reports.

**When detection runs.** Not on every query: a hai call should stay one HTTP
round trip before the model call. Detection runs (a) in `hai-model` commands,
(b) in `hai --setup`, and (c) lazily, only after a query fails with
`OllamaModelNotFoundError` or a connection error. The happy path is untouched.

## 5. Installing a model (consented pull)

`hai_sh/models.py: pull_model(name, on_progress)` wraps `POST /api/pull` with
streaming. Ollama's stream gives `status`, and for each layer `digest`, `total`
and `completed`. Pulls are resumable (Ollama documents that a cancelled pull
resumes), so Ctrl+C is safe and the next pull continues.

Before any pull, hai shows:

1. **Download size.** Ollama has no API that reports a model's size before the
   download starts, so the size comes from the catalog (section 6). For a model
   not in the catalog, say "size unknown until the download starts" and show
   the running total as layers are announced.
2. **Disk free** in the models directory, and a hard stop if the download
   would leave less than 10% of the disk or 2 GB free (whichever is larger);
   the user can override with `--force`.
3. **Memory fit.** If the catalog's measured load size is above 70% of total
   RAM, warn that answers will be slow or fail.
4. **Licence**, and a clear flag when it is non-commercial.

Consent rules:

- The default answer is **No**. Enter does nothing.
- `--yes` on `hai-model pull` / `use` skips the prompt for scripting.
- **Never prompt when stdin or stdout is not a TTY**, and never inside
  `--suggest-only` (the Ctrl+X Ctrl+H binding). There, hai returns its normal
  JSON with an empty `command` and a `conversation` that says which model is
  missing and to run `hai-model pull gemma4:e2b`. A key binding must not hang
  on a hidden prompt or start a multi-GB download.
- A pull started from inside a query (section 3) answers that query
  afterwards, so the user's first request isn't lost.

Progress uses the existing `gum` integration when present and a plain
single-line percentage otherwise, respecting `NO_COLOR`.

## 6. The recommended-models catalog

A data file shipped in the package, `hai_sh/data/models.yaml`, is the single
source of truth for "what should I run". It replaces the hard-coded default in
four places today (`config.DEFAULT_CONFIG`, `schema.OllamaProviderConfig`,
`init.create_default_config`, `__main__._write_setup_config`) with one lookup.

```yaml
schema_version: 1
eval_run: eval-results/2026-11-27     # where the numbers came from
hardware: "i7-7700HQ, 8 threads, 31 GiB, CPU-only Ollama"
models:
  - name: gemma4:e2b
    role: default                 # default | lighter | stronger | reference
    download_gb: 4.6              # from /api/tags after pull
    loaded_gb: null               # from /api/ps after load (re-measure, see below)
    task_accuracy: 0.88
    accuracy_ci: [0.80, 0.93]
    catastrophic_refused: "7/7"
    median_latency_s: 4.6
    licence: Apache-2.0
    commercial_use: true
    clears_bar: true
    settings: {}                  # per-model overrides of the ollama defaults
```

Rules for the file:

- **Only measured numbers.** `download_gb` is read from `/api/tags` after the
  eval pulls the model, `loaded_gb` from `/api/ps` after it loads. The current
  summary reports 1.08 GB "RAM" for `gemma4:e2b` against a 4.6 GB download,
  which needs re-checking before it is shown to users as memory needed.
- **Licence is read from the model card**, by a person, and recorded with the
  date. The eval does not guess licences.
- **Roles.** Exactly one `default`. A `lighter` entry is what hai offers when
  the default doesn't fit the disk or RAM (decision D4). `stronger` is for
  users with headroom (today `gemma4:e4b`: 91%, 7.5 s, Apache 2.0).
- **Updates ship with releases.** hai does not fetch the catalog over the
  network: no surprise traffic, works offline, and the numbers match the
  version the user runs.

### How the eval feeds it

1. `eval/run_eval.py` already records per-model results. Add two measured
   fields per model: on-disk size from `/api/tags` and loaded size from
   `/api/ps`.
2. A new `eval/export_catalog.py` reads `summary.json` plus a hand-kept
   `eval/licences.yaml` and writes `hai_sh/data/models.yaml`. It refuses to
   mark a model `default` unless it clears the bar in `eval/README.md` and has
   a licence entry.
3. A unit test asserts the catalog parses, has one default, and that the
   default equals `DEFAULT_OLLAMA_MODEL`, so the two can never drift.
4. Changing the default model is then one regenerated file plus a CHANGELOG
   line, reviewed in a PR with the eval run linked.

## 7. Switching models

`hai-model use <name>`:

1. Normalise the name, check it against `/api/tags`.
2. If not installed: offer the consented pull (section 5). `--no-pull` sets it
   anyway (useful when Ollama is remote and someone else manages models).
3. If the name is not in the catalog: allow it, but say it is untested with
   hai and that `eval/README.md` explains how to score it.
4. Write `providers.ollama.model` to the config file (section 9) and print the
   old and new value.

`hai --model <name> <query>` overrides for one call and never writes config.
The TUI's provider menu gains a model sub-list using the same `models.py`
functions; that is phase 2.

The setup wizard (`hai --setup`) stops asking the user to type a model name.
For Ollama it runs detection, shows the catalog's default with its size, offers
installed catalog models first, and runs the consented pull.

## 8. When the default isn't available

Order of what hai tries after `OllamaModelNotFoundError` in an interactive
terminal:

1. **Offer the pull** of the configured model (section 5).
2. If the user declines and **another catalog model is already installed**,
   offer it for this query, and offer to make it the default.
3. If nothing local works, **mention a cloud provider only if one is already
   configured** (an API key in config or `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
   in the environment), with the privacy notice from `privacy.py`, and only on
   an explicit yes (decision D3).
4. Otherwise stop with the exact commands.

When Ollama itself is missing or down, hai says which, and gives the official
install or start command for the OS (decision D6) instead of the current
generic "No providers available".

The existing `provider_priority` list keeps working as today: if a user set it,
they already chose an automatic fallback order, and hai follows it.

## 9. Existing users' configs

Verified facts that shape this:

- v0.1.4's `init.create_default_config()` wrote `model: "llama3.2"` explicitly
  into `~/.hai/config.yaml`, and `init_hai_directory()` creates that file on
  first run. So nearly every existing user has `llama3.2` pinned in their file.
- `load_config()` deep-merges the file over `DEFAULT_CONFIG`. Their pinned
  model wins, but the new keys they never set (`format: schema`,
  `temperature: 0`, `think: false`, `num_predict: 1024`) now come from the
  defaults. In the eval, `llama3.2` under these settings scored 77% (baseline
  settings: 70%) but refused 5 of 7 catastrophic requests (baseline: 6 of 7).

Rules:

1. **Never change a user's model on upgrade.** A pinned value is a choice.
2. **One-time notice** (decision D5): when the configured model is `llama3.2`
   and a marker file `~/.hai/.notices` doesn't list it yet, print once to
   stderr that the default is now `gemma4:e2b`, with its numbers, and the
   command `hai-model use gemma4:e2b`. Never in `--suggest-only` or non-TTY.
3. **Config edits preserve the file.** PyYAML drops comments, so
   `hai-model use` edits the single `model:` line under `providers: ollama:`
   in place when it finds it, and only falls back to a full rewrite when the
   structure is unusual. Either way it writes `config.yaml.bak` first and keeps
   mode 600. No new dependency (ruamel.yaml would preserve comments, but the
   project keeps its dependency list short).
4. The merge behaviour above is documented in CONFIGURATION.md's upgrade
   notes, so users who want the old sampling can set `format: null`,
   `temperature: 0.7` and `think: null`.

## 10. Implementation plan

**Phase 1, needed before v0.1.5**

1. `hai_sh/data/models.yaml` with today's measured entries; single lookup for
   the default; test that it matches `DEFAULT_OLLAMA_MODEL`.
2. `hai_sh/models.py`: detection, name normalisation, pull with progress,
   config edit with backup. Unit tests against `eval/mock_ollama.py`,
   which already answers `/api/version`, `/api/tags`, `/api/ps`, `/api/pull`
   and `/api/show` (extend it for streamed pull progress and 404s).
3. `hai-model status | list | pull | use` (or the shape chosen in D1).
4. Missing-model and Ollama-missing flows in `__main__.py`, with the
   non-TTY and `--suggest-only` rules. Tests for both shells' binding path.
5. Setup wizard uses the catalog and the consented pull.
6. One-time notice for `llama3.2` users.
7. Docs: README quick start, INSTALL, CONFIGURATION (upgrade notes, catalog).

**Phase 2**

8. `hai-model recommend` using disk and RAM; `remove`.
9. TUI model switching.
10. `eval/export_catalog.py` and the measured size fields in the eval.

**Phase 3 (only if wanted)**

11. Show capabilities from `/api/show` and drop the `think` 400-retry.
12. Remote-Ollama awareness in `status` (which host, whose disk).

Rough size: phase 1 is one PR of a few hundred lines plus tests; it does not
touch the command validator, the prompt or the providers' generate path.

## 11. Decisions for the maintainer

Each has a recommendation; none blocks writing phase 1 except D1.

- **D1. Command shape.**
  (a) a separate `hai-model` command, like the existing `hai-install-shell`
  *(recommended: `hai model list` would collide with a natural-language query
  that starts with "model")*; (b) flags on `hai` (`--models`, `--use-model`);
  (c) reserve the word `model` as a subcommand.
- **D2. Missing model during a query.**
  (a) offer the download right there, default No *(recommended)*; (b) keep
  today's behaviour and only print the command.
- **D3. Cloud fallback.**
  (a) offer it only when a provider is already configured, and only on an
  explicit yes each time *(recommended: it sends shell context off the
  machine)*; (b) use it automatically whenever an API key is set.
- **D4. The "lighter" model for small disks or RAM.** No model smaller than
  `gemma4:e2b` cleared the bar.
  (a) `phi4-mini`: MIT, 84%, 7.2 s; (b) `qwen2.5-coder:3b`: 91%, 4.8 s,
  1.9 GB download, but the Qwen Research licence forbids commercial use;
  (c) none: tell those users to use a cloud provider.
  *(Recommended: (a), after its download size is measured.)*
- **D5. Existing `llama3.2` users.**
  (a) one-time notice with the switch command *(recommended)*; (b) migrate
  them automatically; (c) say nothing.
- **D6. Ollama not installed.**
  (a) print the official install command for the OS and stop *(recommended:
  the Linux installer needs sudo, which a shell assistant should not run
  unasked)*; (b) offer to run the installer.
