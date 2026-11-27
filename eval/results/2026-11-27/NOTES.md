# Notes on 2026-11-27 (constrained rerun)

Constrained rows: rerun on this host with the fixed schema (faaf32c: "command"
required, empty string = no command). Baseline rows: copied unchanged from
eval-results/2026-11-26 and re-scored here.

## Baseline re-scoring artifact

23 of the copied baseline replies use absolute paths into the 2026-11-26
fixture (`.../20261126-112542-e21f70/eval/results/2026-11-26/fixture/work`).
Re-scored here, the sandbox mounts this run's fixture instead, so 17 replies
that passed on 2026-11-26 now fail only because the path is missing
(lfm3 9, phi4-mini 6, qwen3.5:4b 1, qwen3.5:9b 1). No verdict went fail→pass.
Raw rows were left as they were. The baseline figures in summary.md are therefore
too low for those models; the 2026-11-26 scoring of the same rows is the
correct one:

| model | cond | RAM GB | JSON 1st try | usable | task acc (95% CI) | cmd acc | mode | safe | Brier | p50 s | tok/s | bar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma4:e2b | baseline | 1.08 | 98% | 99% | 81% (71–87) | 74% | 88% | 100% | 0.162 | 27.3 | 15 | json, mode, latency |
| lfm3 | baseline | 1.18 | 65% | 66% | 59% (49–69) | 58% | 61% | 100% | 0.092 | 47.2 | 21 | json, accuracy, gap-to-reference, mode, latency |
| llama3.2 | baseline | 2.57 | 91% | 91% | 70% (60–78) | 65% | 88% | 86% | 0.214 | 5.4 | 10 | json, accuracy, gap-to-reference, mode, safety, latency |
| phi4-mini | baseline | 3.11 | 80% | 98% | 77% (68–85) | 71% | 96% | 100% | 0.124 | 7.1 | 9 | json, latency |
| qwen3.5:4b | baseline | 3.15 | 95% | 95% | 87% (79–92) | 85% | 90% | 100% | 0.075 | 46.1 | 8 | json, latency |
| qwen3.5:9b | baseline | 6.19 | 98% | 98% | 87% (79–92) | 82% | 95% | 100% | 0.097 | 69.2 | 5 | json, latency |

The bar is judged on the constrained condition only. Constrained rows use this
run's fixture path, so they are not affected.
