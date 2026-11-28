"""
A small fake Ollama server for tests of model detection, pulling and the
missing-model flow. Runs in a thread on a free port.

It answers /api/version, /api/tags, /api/pull (streamed progress, like the
real one) and /api/generate (404 "model not found" for anything not installed).
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional, Set


class FakeOllama:
    def __init__(
        self, installed: Optional[Dict[str, int]] = None, pullable: Optional[Set[str]] = None
    ):
        # name as Ollama reports it (with tag) -> size in bytes
        self.installed: Dict[str, int] = dict(installed or {})
        # names /api/pull will accept; pulling adds them to installed
        self.pullable: Set[str] = set(pullable or ())
        self.pull_requests = []
        self.generate_requests = []
        self.answer = {"explanation": "Lists the files.", "command": "ls", "confidence": 90}
        self.fail_pull_midway = False
        self._server: Optional[ThreadingHTTPServer] = None

    @staticmethod
    def full(name: str) -> str:
        last = name.rsplit("/", 1)[-1]
        return name if (":" in last or name.startswith("hf.co/")) else f"{name}:latest"

    @property
    def url(self) -> str:
        assert self._server is not None
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def start(self) -> FakeOllama:
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, obj, code=200):
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _stream(self, events):
                body = ("\n".join(json.dumps(e) for e in events) + "\n").encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/api/version":
                    return self._send({"version": "0.0.0-fake"})
                if self.path == "/api/tags":
                    return self._send(
                        {
                            "models": [
                                {"name": n, "size": s, "details": {"parameter_size": "1B"}}
                                for n, s in fake.installed.items()
                            ]
                        }
                    )
                self._send({"error": "404 page not found"}, 404)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                if self.path == "/api/pull":
                    name = fake.full(body.get("model", ""))
                    fake.pull_requests.append(name)
                    if name not in {fake.full(p) for p in fake.pullable}:
                        return self._send(
                            {"error": "pull model manifest: file does not exist"}, 500
                        )
                    events = [
                        {"status": "pulling manifest"},
                        {
                            "status": "pulling aaa",
                            "digest": "sha256:aaa",
                            "total": 1000,
                            "completed": 0,
                        },
                        {
                            "status": "pulling aaa",
                            "digest": "sha256:aaa",
                            "total": 1000,
                            "completed": 500,
                        },
                    ]
                    if fake.fail_pull_midway:
                        events.append({"error": "connection reset"})
                        return self._stream(events)
                    events += [
                        {
                            "status": "pulling aaa",
                            "digest": "sha256:aaa",
                            "total": 1000,
                            "completed": 1000,
                        },
                        {"status": "verifying sha256 digest"},
                        {"status": "writing manifest"},
                        {"status": "success"},
                    ]
                    fake.installed[name] = 1000
                    return self._stream(events)
                if self.path == "/api/generate":
                    name = fake.full(body.get("model", ""))
                    fake.generate_requests.append(name)
                    if name not in fake.installed:
                        return self._send({"error": f"model '{body.get('model')}' not found"}, 404)
                    text = json.dumps(fake.answer)
                    if body.get("stream", True):
                        return self._stream(
                            [{"response": text, "done": False}, {"response": "", "done": True}]
                        )
                    return self._send({"response": text, "done": True})
                self._send({"error": "404 page not found"}, 404)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
