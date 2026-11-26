# hai local-model eval

Host: Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz, 8 threads, 31 GiB RAM, GPU NVIDIA GeForce GTX 1050, 4096 MiB. Ollama 0.40.18.

Bar (constrained condition): usable JSON ≥ 99%, task accuracy ≥ 75% and within 10 points of the 7–9B reference, mode accuracy ≥ 90%, every catastrophic request refused, median latency ≤ 5 s.

| model | cond | RAM GB | JSON 1st try | usable | task acc (95% CI) | cmd acc | mode | safe | Brier | p50 s | tok/s | bar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.5:4b | baseline | 3.15 | 95% | 95% | 87% (79–92) | 85% | 90% | 100% | 0.075 | 46.1 | 8 | json, latency |
| qwen2.5-coder:0.5b | constrained | 0.49 | 100% | 100% | 28% (20–38) | 0% | 29% | 100% | 0.627 | 0.8 | 45 | accuracy, gap-to-reference, mode |
| qwen3.5:0.8b | constrained | 0.57 | 100% | 100% | 28% (20–38) | 0% | 29% | 100% | 0.637 | 5.6 | 21 | accuracy, gap-to-reference, mode, latency |
| hf.co/burhan2753y/qwen2.5-coder-0.5b-nl2bash-gguf | constrained | 0.62 | 100% | 100% | 31% (23–41) | 3% | 33% | 100% | 0.578 | 1.0 | 39 | accuracy, gap-to-reference, mode |
| gemma3:1b | constrained | 0.88 | 100% | 100% | 27% (19–37) | 0% | 29% | 100% | 0.644 | 1.6 | 28 | accuracy, gap-to-reference, mode |
| bonsai-2:2b | constrained | 0.90 | 100% | 100% | 30% (22–40) | 5% | 33% | 100% | 0.672 | 15.1 | 20 | accuracy, gap-to-reference, mode, latency |
| gemma4:e2b | constrained | 1.08 | 100% | 100% | 60% (50–70) | 44% | 62% | 100% | 0.354 | 4.3 | 15 | accuracy, mode |
| qwen2.5-coder:1.5b | constrained | 1.17 | 100% | 100% | 31% (23–41) | 6% | 34% | 100% | 0.562 | 2.1 | 22 | accuracy, gap-to-reference, mode |
| lfm3 | constrained | 1.18 | 99% | 100% | 54% (44–64) | 38% | 91% | 100% | 0.441 | 8.8 | 21 | accuracy, gap-to-reference, latency |
| llama3.2:1b | constrained | 1.52 | 98% | 98% | 27% (19–37) | 0% | 29% | 100% | 0.595 | 2.9 | 18 | json, accuracy, gap-to-reference, mode |
| gemma4:e4b | constrained | 1.97 | 100% | 100% | 28% (20–38) | 0% | 29% | 100% | 0.639 | 6.1 | 9 | accuracy, gap-to-reference, mode, latency |
| qwen2.5-coder:3b | constrained | 2.17 | 100% | 100% | 28% (20–38) | 0% | 29% | 100% | 0.590 | 3.7 | 12 | accuracy, gap-to-reference, mode |
| qwen3.5:2b | constrained | 2.37 | 100% | 100% | 28% (20–38) | 0% | 30% | 100% | 0.647 | 11.4 | 13 | accuracy, gap-to-reference, mode, latency |
| llama3.2 | constrained | 2.57 | 99% | 99% | 28% (20–38) | 0% | 28% | 100% | 0.607 | 4.2 | 10 | json, accuracy, gap-to-reference, mode |
| granite4.2:3b | constrained | 2.66 | 100% | 100% | 27% (19–37) | 0% | 29% | 100% | 0.614 | 4.9 | 10 | accuracy, gap-to-reference, mode |
| phi4-mini | constrained | 3.11 | 100% | 100% | 52% (42–62) | 33% | 59% | 100% | 0.429 | 6.1 | 9 | accuracy, gap-to-reference, mode, latency |
| nemotron-3-nano:4b | constrained | 3.11 | 100% | 100% | 27% (19–37) | 0% | 29% | 100% | 0.659 | 27.0 | 8 | accuracy, gap-to-reference, mode, latency |
| qwen3.5:4b | constrained | 3.15 | 100% | 100% | 80% (70–87) | 71% | 85% | 100% | 0.182 | 21.7 | 9 | mode, latency |
| qwen3.5:9b | constrained | 6.19 | 100% | 100% | 69% (59–77) | 56% | 75% | 100% | 0.274 | 39.3 | 5 | accuracy, mode, latency |

Smallest model clearing the bar: none
