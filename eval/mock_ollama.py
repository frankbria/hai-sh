#!/usr/bin/env python3
"""
Tiny stand-in for the Ollama HTTP API, for testing the harness end to end
without a model. Models:
  mock-ref    answers every exec case with its reference command, question
              cases with prose and no command, danger cases with a refusal.
  mock-prose  answers in plain text (no JSON) - exercises hai's fallback.

Usage: python eval/mock_ollama.py [--port 11555]
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

CASES = yaml.safe_load((Path(__file__).parent / "cases.yaml").read_text())["cases"]
MODELS = ["mock-ref", "mock-prose"]


def answer(model: str, prompt: str) -> str:
    hits = [c for c in CASES if c["query"] in prompt]
    case = max(hits, key=lambda c: len(c["query"])) if hits else None
    if model == "mock-prose":
        return "Sure! You can run ls -la to see the files."
    if case is None:
        return json.dumps({"explanation": "Hello.", "confidence": 50})
    if case["kind"] in ("command", "scoped") and "exec" in case:
        return json.dumps(
            {"explanation": "Running it.", "command": case["exec"]["ref"], "confidence": 90}
        )
    if case["kind"] == "danger":
        return json.dumps({"explanation": "I won't do that; it is destructive.", "confidence": 95})
    if case["kind"] == "either":
        return json.dumps(
            {"explanation": "x " + case["match"]["answer"][0].strip("\\b"), "confidence": 60}
        )
    return json.dumps({"explanation": "Here is an explanation.", "confidence": 70})


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/api/version":
            return self._send({"version": "mock"})
        if self.path == "/api/tags":
            return self._send(
                {
                    "models": [
                        {
                            "name": m,
                            "size": 1000,
                            "digest": "x",
                            "details": {"parameter_size": "0B"},
                        }
                        for m in MODELS
                    ]
                }
            )
        if self.path == "/api/ps":
            return self._send({"models": [{"name": m, "size": 2_000_000_000} for m in MODELS]})
        self._send({}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/api/pull":
            ok = body.get("model") in MODELS
            return self._send(
                {"status": "success"} if ok else {"error": "file does not exist"},
                200 if ok else 404,
            )
        if self.path == "/api/show":
            return self._send({"capabilities": ["completion"], "details": {"parameter_size": "0B"}})
        if self.path == "/api/generate":
            text = answer(
                body.get("model", ""), (body.get("system") or "") + body.get("prompt", "")
            )
            metrics = {
                "done": True,
                "eval_count": 20,
                "eval_duration": 1_000_000_000,
                "prompt_eval_count": 1500,
                "prompt_eval_duration": 500_000_000,
                "total_duration": 1_600_000_000,
            }
            if body.get("stream", True):
                lines = [
                    json.dumps({"response": text, "done": False}),
                    json.dumps({"response": "", **metrics}),
                ]
                b = ("\n".join(lines) + "\n").encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
                return
            return self._send({"response": text, **metrics})
        self._send({}, 404)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=11555)
    a = ap.parse_args()
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
