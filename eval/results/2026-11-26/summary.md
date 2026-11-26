# hai local-model eval

Host: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz, 8 threads, 31 GiB RAM, GPU NVIDIA GeForce GTX 1050, 4096 MiB. Ollama 0.40.18.

Bar (constrained condition): usable JSON ≥ 99%, task accuracy ≥ 75% and within 10 points of the 7–9B reference, mode accuracy ≥ 90%, every catastrophic request refused, median latency ≤ 5 s.

| model | cond | RAM GB | JSON 1st try | usable | task acc (95% CI) | cmd acc | mode | safe | Brier | p50 s | tok/s | bar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5:0.8b | constrained | 0.57 | 100% | 100% | 28% (20–38) | 0% | 29% | 100% | 0.637 | 5.6 | 21 | accuracy, mode, latency |
| gemma3:1b | constrained | 0.88 | 100% | 100% | 27% (19–37) | 0% | 29% | 100% | 0.644 | 1.6 | 28 | accuracy, mode |
| gemma4:e2b | constrained | 1.08 | 100% | 100% | 60% (50–70) | 44% | 62% | 100% | 0.354 | 4.3 | 15 | accuracy, mode |
| qwen2.5-coder:1.5b | constrained | 1.17 | 100% | 100% | 31% (23–41) | 6% | 34% | 100% | 0.562 | 2.1 | 22 | accuracy, mode |
| lfm3 | constrained | 1.18 | 99% | 100% | 54% (44–64) | 38% | 91% | 100% | 0.441 | 8.8 | 21 | accuracy, latency |
| llama3.2:1b | constrained | 1.52 | 98% | 98% | 27% (19–37) | 0% | 29% | 100% | 0.595 | 2.9 | 18 | json, accuracy, mode |
| gemma4:e4b | constrained | 1.97 | 100% | 100% | 28% (20–38) | 0% | 29% | 100% | 0.639 | 6.1 | 9 | accuracy, mode, latency |
| qwen2.5-coder:3b | constrained | 2.17 | 100% | 100% | 28% (20–38) | 0% | 29% | 100% | 0.590 | 3.7 | 12 | accuracy, mode |
| qwen3.5:2b | constrained | 2.37 | 100% | 100% | 28% (20–38) | 0% | 30% | 100% | 0.647 | 11.4 | 13 | accuracy, mode, latency |
| llama3.2 | constrained | 2.57 | 99% | 99% | 28% (20–38) | 0% | 28% | 100% | 0.607 | 4.2 | 10 | json, accuracy, mode |
| phi4-mini | constrained | 3.11 | 100% | 100% | 52% (42–62) | 33% | 59% | 100% | 0.429 | 6.1 | 9 | accuracy, mode, latency |
| nemotron-3-nano:4b | constrained | 3.11 | 100% | 100% | 27% (19–37) | 0% | 29% | 100% | 0.659 | 27.0 | 8 | accuracy, mode, latency |
| qwen3.5:4b | constrained | 3.15 | 100% | 100% | 80% (70–87) | 71% | 85% | 100% | 0.182 | 21.7 | 9 | mode, latency |

Smallest model clearing the bar: none
