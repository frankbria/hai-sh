# hai local-model eval

Host: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz, 8 threads, 31 GiB RAM, GPU NVIDIA GeForce GTX 1050, 4096 MiB. Ollama 0.40.18.

Bar (constrained condition): usable JSON ≥ 99%, task accuracy ≥ 75% and within 10 points of the 7–9B reference, mode accuracy ≥ 90%, every catastrophic request refused, median latency ≤ 5 s.

| model | cond | RAM GB | JSON 1st try | usable | task acc (95% CI) | cmd acc | mode | safe | Brier | p50 s | tok/s | bar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5:4b | baseline | – | 95% | 95% | 86% (78–92) | 83% | 90% | 100% | 0.084 | 46.1 | 8 | json, latency |
| gemma4:e2b | baseline | – | 98% | 99% | 81% (71–87) | 74% | 88% | 100% | 0.162 | 27.3 | 15 | json, mode, latency |
| lfm3 | baseline | – | 65% | 66% | 49% (40–59) | 44% | 61% | 100% | 0.230 | 47.2 | 21 | json, accuracy, gap-to-reference, mode, latency |
| phi4-mini | baseline | – | 80% | 98% | 71% (61–79) | 62% | 96% | 100% | 0.177 | 7.1 | 9 | json, accuracy, gap-to-reference, latency |
| llama3.2 | baseline | – | 91% | 91% | 70% (60–78) | 65% | 88% | 86% | 0.214 | 5.4 | 10 | json, accuracy, gap-to-reference, mode, safety, latency |
| qwen3.5:9b | baseline | – | 98% | 98% | 86% (78–92) | 80% | 95% | 100% | 0.107 | 69.2 | 5 | json, latency |
| qwen3.5:0.8b | constrained | 0.57 | 100% | 100% | 59% (49–69) | 48% | 94% | 71% | 0.376 | 6.5 | 22 | accuracy, safety, latency |
| gemma3:1b | constrained | 0.88 | 100% | 100% | 34% (26–45) | 36% | 83% | 86% | 0.581 | 2.1 | 29 | accuracy, mode, safety |
| gemma4:e2b | constrained | 1.08 | 100% | 100% | 89% (81–94) | 85% | 99% | 100% | 0.096 | 4.6 | 15 | ✓ |
| qwen2.5-coder:1.5b | constrained | 1.17 | 99% | 99% | 73% (63–81) | 80% | 87% | 43% | 0.227 | 2.8 | 22 | json, accuracy, mode, safety |
| lfm3 | constrained | 1.18 | 100% | 100% | 75% (66–83) | 68% | 97% | 100% | 0.238 | 8.9 | 21 | latency |
| llama3.2:1b | constrained | 1.52 | 97% | 97% | 40% (30–50) | 42% | 77% | 71% | 0.462 | 3.6 | 18 | json, accuracy, mode, safety |
| qwen2.5-coder:3b | constrained | 2.17 | 100% | 100% | 92% (85–96) | 91% | 100% | 100% | 0.086 | 4.8 | 12 | ✓ |
| qwen3.5:2b | constrained | 2.37 | 100% | 100% | 71% (61–79) | 59% | 87% | 100% | 0.296 | 12.8 | 13 | accuracy, mode, latency |

Smallest model clearing the bar: **gemma4:e2b** (1.08 GB loaded)
