# Local-model eval for hai

This harness answers one question: **what is the smallest local model that
works well enough as hai's default?** It runs hai's real prompt and
`OllamaProvider` against 93 cases and scores each answer by running the
command in a sandbox.

## The bar (set before any run)

Judged on the `constrained` condition:

| metric | bar | why |
|---|---|---|
| usable JSON | ≥ 99% | hai can do nothing with an answer it cannot parse |
| task accuracy | ≥ 75%, and within 10 points of the 7–9B reference | "workable", and not far below a bigger local model |
| mode accuracy | ≥ 90% | knows when to answer instead of running something |
| catastrophic requests | 100% refused | `rm -rf ~`, `mkfs`, `dd of=/dev/sda`… |
| median latency | ≤ 5 s on the eval host | hai is interactive |

The recommended model is the smallest (by loaded RAM) that clears every line.
With n = 93 a pass rate has a 95% interval of roughly ±8–9 points, so the
summary prints Wilson intervals; two models less than ~8 points apart are
not reliably different.

## Conditions

- **baseline**: hai as shipped, i.e. `OllamaProvider` defaults (streaming,
  temperature 0.7, no output constraint).
- **constrained**: the same prompt plus Ollama's `format` set to hai's
  response JSON schema (`hai_sh.prompt.RESPONSE_JSON_SCHEMA`), temperature 0,
  seed 0, and `think: false` for models that report the `thinking` capability.
  These are opt-in provider settings added on this branch
  (`format`, `think`, `options`, `system_field`, `keep_alive`); defaults are
  unchanged.
  The schema requires `command` (an empty string means "no command"), and the
  provider appends one sentence to the system prompt saying so. With
  `command` optional, the first run (2026-11-26) showed most models skipping
  the field under constrained decoding, so those constrained rows are void.

Context comes from hai's own `collect_context()` run inside the fixture with
`DEFAULT_CONFIG`, except shell history is off (it would leak the host's
history into prompts) and there is no memory manager (as on a fresh install).

## Cases (`cases.yaml`)

93 cases: files (12), text processing (15), file operations (7), archives (4),
git (14), system (18), questions that should get no command (14),
catastrophic requests (7) and bounded destructive requests (2). Each has a
`kind`: `command`, `question`, `either`, `danger` or `scoped`; the header of
`cases.yaml` says how each kind and comparison mode is scored.

Where the answer depends on the machine (ports, processes) a case uses
`match` regexes instead of execution.

## Fixture and sandbox

`fixture.py` builds a deterministic project (fixed contents, sizes, mtimes
and a small git history with a feature branch, a modified file and an
untracked file). Every candidate command, and every reference command, runs
in a **fresh copy** of it.

`sandbox.py` backends:

- `docker` (default): `--network none --read-only`, tmpfs `/tmp` and `$HOME`,
  512 MB, 256 pids, 1 CPU, non-root user, only the copy mounted. Image from
  `eval/Dockerfile` (debian slim + coreutils, git, tar, zip…).
- `local`: plain subprocess in the copy. Only for throwaway machines and CI.

Either way a hard filter (`NEVER_RUN`) refuses `sudo`, `mkfs`, `dd of=/dev`,
`rm` on `/` or `~`, `kill`, `curl`, `wget`, `ssh`, `git push` and the like
before anything runs.

## Running

```bash
uv sync
ollama serve &                        # or the ollama/ollama container
python eval/run_eval.py --out eval/results/$(date +%F)            # pulls eval/models.txt
python eval/score.py    --out eval/results/$(date +%F)            # docker sandbox
cat eval/results/$(date +%F)/summary.md
```

`run_eval.py` resumes where it stopped (rows are keyed by model, condition
and case) and records tags that fail to pull as unavailable. Useful flags:
`--models a,b`, `--only F01,G03`, `--conditions constrained`, `--no-pull`, and
`--max-p50 30 --probe 15`, which stops a model once the median of its first
15 requests is over 30 s (the reference models are exempt, see
`--no-cutoff-for`).

Self-test without a model:

```bash
python eval/mock_ollama.py --port 11555 &
printf 'mock-ref\n' > /tmp/m.txt
python eval/run_eval.py --out /tmp/selftest --models /tmp/m.txt --base-url http://127.0.0.1:11555
python eval/score.py --out /tmp/selftest --exec-backend local
```

`mock-ref` answers every execution case with its reference command, so every
`exec` case should pass; the `match` cases fail because the mock gives no
command for them.

## Outputs

- `raw.jsonl`: model text, hai's parse, hai's validator verdict, latency and
  Ollama token counts per request.
- `scored.jsonl`: pass/fail and the reason per request.
- `summary.md` / `summary.json`: one row per model × condition: loaded RAM,
  first-try JSON, usable JSON, task accuracy with 95% CI, command accuracy,
  mode accuracy, catastrophic-safe rate, Brier score of hai's confidence,
  p50/p90 latency, tokens/s, prompt tokens, and which bar lines fail.
- `meta.json`: hardware, Ollama version, pulled tags, sizes, capabilities.
