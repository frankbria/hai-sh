#!/usr/bin/env python3
"""
Run hai's real prompt + Ollama provider over the eval cases for each model.

For every (model, condition, case) it records one JSON line in
<out>/raw.jsonl: the raw model text, hai's parse result, timing and Ollama's
token counts. Scoring is a separate step (score.py) so it can be re-run
without calling any model.

Conditions:
  baseline     hai exactly as shipped: OllamaProvider defaults (streaming,
               temperature 0.7, no format constraint).
  constrained  same prompt, plus Ollama `format` = hai's response JSON schema,
               temperature 0, fixed seed, and think=false for models that
               support thinking.

Context: hai's own collect_context() run inside the fixture project with
hai's DEFAULT_CONFIG, except shell history is off (it would leak the host's
history into the prompt and make runs irreproducible) and there is no memory
manager (a fresh install has no memory).

Usage:
  python eval/run_eval.py --out eval-results/2026-11-26 [--models eval/models.txt]
         [--conditions baseline,constrained] [--cases eval/cases.yaml]
         [--base-url http://localhost:11434] [--only F01,F02] [--no-pull]
"""

from __future__ import annotations

import argparse
import copy as _copy
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import requests  # noqa: E402
import yaml  # noqa: E402

import fixture  # noqa: E402
from hai_sh.config import DEFAULT_CONFIG  # noqa: E402
from hai_sh.prompt import (  # noqa: E402
    build_system_prompt,
    collect_context,
    extract_fallback_response,
    parse_response,
    validate_command,
)
from hai_sh.providers.ollama import OllamaProvider  # noqa: E402

CONDITIONS = ("baseline", "constrained")


def load_models(spec: str) -> list[str]:
    p = Path(spec)
    if p.exists():
        return [
            ln.strip()
            for ln in p.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
    return [m.strip() for m in spec.split(",") if m.strip()]


def hai_config() -> dict:
    cfg = _copy.deepcopy(DEFAULT_CONFIG)
    cfg["context"]["include_history"] = False
    return cfg


def hardware() -> dict:
    info = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "nproc": os.cpu_count(),
    }
    for key, cmd in (
        ("cpu", "lscpu | grep -m1 'Model name' | cut -d: -f2"),
        ("mem", "free -g | awk '/Mem:/{print $2\" GiB\"}'"),
        ("gpu", "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null"),
    ):
        try:
            info[key] = subprocess.run(
                ["bash", "-c", cmd], capture_output=True, text=True, timeout=10
            ).stdout.strip()
        except Exception as e:  # pragma: no cover
            info[key] = f"error: {e}"
    return info


class Ollama:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")

    def version(self) -> str:
        return requests.get(f"{self.base}/api/version", timeout=10).json().get("version", "?")

    def tags(self) -> dict[str, dict]:
        data = requests.get(f"{self.base}/api/tags", timeout=30).json()
        return {m["name"]: m for m in data.get("models", [])}

    def pull(self, model: str) -> tuple[bool, str]:
        try:
            r = requests.post(
                f"{self.base}/api/pull", json={"model": model, "stream": False}, timeout=3600
            )
            if r.status_code != 200:
                return False, f"HTTP {r.status_code}: {r.text[:300]}"
            body = r.json()
            if body.get("status") == "success":
                return True, "pulled"
            return False, json.dumps(body)[:300]
        except Exception as e:
            return False, str(e)[:300]

    def show(self, model: str) -> dict:
        r = requests.post(f"{self.base}/api/show", json={"model": model}, timeout=60)
        return r.json() if r.status_code == 200 else {}

    def ps(self) -> list[dict]:
        return requests.get(f"{self.base}/api/ps", timeout=10).json().get("models", [])

    def unload(self, model: str) -> None:
        try:
            requests.post(
                f"{self.base}/api/generate", json={"model": model, "keep_alive": 0}, timeout=60
            )
        except Exception:
            pass


def provider_for(model: str, condition: str, base_url: str, thinking: bool) -> OllamaProvider:
    cfg = {"base_url": base_url, "model": model, "timeout": 900}
    if condition == "constrained":
        cfg.update({"format": "schema", "temperature": 0, "options": {"seed": 0}})
        if thinking:
            cfg["think"] = False
    return OllamaProvider(cfg)


def done_keys(path: Path) -> set[tuple[str, str, str]]:
    keys = set()
    if path.exists():
        for ln in path.read_text().splitlines():
            try:
                r = json.loads(ln)
                keys.add((r["model"], r["condition"], r["case"]))
            except Exception:
                pass
    return keys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--models", default=str(HERE / "models.txt"))
    ap.add_argument("--cases", default=str(HERE / "cases.yaml"))
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--base-url", default="http://localhost:11434")
    ap.add_argument("--only", default="", help="comma-separated case ids")
    ap.add_argument("--no-pull", action="store_true")
    ap.add_argument(
        "--max-p50",
        type=float,
        default=0,
        help="skip the rest of a model/condition when the median latency of its "
        "first --probe cases exceeds this many seconds (0 = never)",
    )
    ap.add_argument("--probe", type=int, default=15)
    ap.add_argument(
        "--no-cutoff-for",
        default="qwen3.5:9b,qwen2.5-coder:7b",
        help="models that always run every case (the reference)",
    )
    args = ap.parse_args()

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "raw.jsonl"
    cases = yaml.safe_load(Path(args.cases).read_text())["cases"]
    if args.only:
        keep = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in keep]
    conditions = [c for c in args.conditions.split(",") if c]
    models = load_models(args.models)

    # Fixture: built once; context is collected from inside it.
    pristine = fixture.build(out / "fixture" / "work")
    cfg = hai_config()
    prompts: dict[str, tuple[dict, str]] = {}
    home = os.getcwd()
    os.chdir(pristine)
    try:
        for c in cases:
            ctx = collect_context(config=cfg, query=c["query"], memory_manager=None)
            prompts[c["id"]] = (ctx, build_system_prompt(ctx))
    finally:
        os.chdir(home)
    (out / "example_system_prompt.txt").write_text(prompts[cases[0]["id"]][1])

    ol = Ollama(args.base_url)
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.setdefault("hardware", hardware())
    meta["ollama_version"] = ol.version()
    meta["fixture"] = str(pristine)
    meta["conditions"] = conditions
    meta.setdefault("models", {})
    preexisting = set(ol.tags())
    meta.setdefault("preexisting_models", sorted(preexisting))

    done = done_keys(raw_path)
    for model in models:
        m = meta["models"].setdefault(model, {})
        if model not in ol.tags() and not args.no_pull:
            t0 = time.time()
            ok, msg = ol.pull(model)
            m.update(pulled=ok, pull_msg=msg, pull_s=round(time.time() - t0, 1))
            print(f"[pull] {model}: {msg}", flush=True)
            if not ok:
                m["available"] = False
                meta_path.write_text(json.dumps(meta, indent=2))
                continue
        tag = ol.tags().get(model) or ol.tags().get(model + ":latest") or {}
        if not tag:
            m["available"] = False
            meta_path.write_text(json.dumps(meta, indent=2))
            continue
        show = ol.show(model)
        caps = show.get("capabilities") or []
        details = show.get("details") or tag.get("details") or {}
        m.update(
            available=True,
            disk_bytes=tag.get("size"),
            digest=tag.get("digest"),
            parameter_size=details.get("parameter_size"),
            quantization=details.get("quantization_level"),
            family=details.get("family"),
            capabilities=caps,
        )
        thinking = "thinking" in caps

        for cond in conditions:
            prov = provider_for(model, cond, args.base_url, thinking)
            # warm-up (loads the model; not timed)
            try:
                warm_ctx, warm_sys = prompts[cases[0]["id"]]
                prov.generate("say hi", warm_ctx, warm_sys)
            except Exception as e:
                m.setdefault("errors", []).append(f"{cond} warm-up: {e}"[:300])
            loaded = [p for p in ol.ps() if p.get("name") in (model, model + ":latest")]
            if loaded:
                m.setdefault("loaded", {})[cond] = {
                    "size": loaded[0].get("size"),
                    "size_vram": loaded[0].get("size_vram"),
                    "context_length": loaded[0].get("context_length"),
                }
            meta_path.write_text(json.dumps(meta, indent=2))

            lats: list[float] = []
            exempt = model in args.no_cutoff_for.split(",")
            for c in cases:
                key = (model, cond, c["id"])
                if key in done:
                    continue
                ctx, sysp = prompts[c["id"]]
                row = {
                    "model": model,
                    "condition": cond,
                    "case": c["id"],
                    "kind": c["kind"],
                    "query": c["query"],
                }
                t0 = time.perf_counter()
                try:
                    text = prov.generate(c["query"], ctx, sysp)
                    row["latency_s"] = round(time.perf_counter() - t0, 3)
                    row["raw"] = text
                    row["metrics"] = dict(prov.last_metrics)
                except Exception as e:
                    row["latency_s"] = round(time.perf_counter() - t0, 3)
                    row["error"] = str(e)[:500]
                    row["raw"] = None
                if row.get("raw") is not None:
                    try:
                        parsed = parse_response(row["raw"])
                        row["parsed"] = parsed
                        row["json_ok"] = True
                    except ValueError as e:
                        row["json_ok"] = False
                        row["parse_error"] = str(e)[:300]
                        fb = extract_fallback_response(row["raw"])
                        row["parsed"] = fb
                        row["fallback"] = fb is not None
                    cmd = (row.get("parsed") or {}).get("command")
                    if cmd:
                        ok, why = validate_command(cmd)
                        row["hai_validator"] = {"ok": ok, "reason": why}
                with raw_path.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
                print(
                    f"[{model} {cond} {c['id']}] {row.get('latency_s')}s "
                    f"json={row.get('json_ok')} cmd={(row.get('parsed') or {}).get('command')!r}"[
                        :200
                    ],
                    flush=True,
                )
                lats.append(row["latency_s"])
                if (
                    args.max_p50
                    and not exempt
                    and len(lats) == args.probe
                    and statistics.median(lats) > args.max_p50
                ):
                    m.setdefault("too_slow", {})[cond] = statistics.median(lats)
                    print(f"[{model} {cond}] too slow, skipping rest", flush=True)
                    break
        ol.unload(model)
        meta_path.write_text(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
