"""Loopback-only demonstration server. No accounts, uploads, telemetry or cloud."""
from __future__ import annotations
import argparse
import hmac
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from engine import DemoError, ROOT, ask, installed_models, load_corpus


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, port: int, enable_ollama: bool = False):
        super().__init__(("127.0.0.1", port), Handler)
        self.token = secrets.token_urlsafe(32)
        self.enable_ollama = enable_ollama
        self.corpus = load_corpus()
        self.inference = threading.BoundedSemaphore(1)
        self.times: list[float] = []
        self.times_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "Skyveiviser/0.3"
    def setup(self):
        super().setup()
        self.connection.settimeout(12)

    def log_message(self, *_):
        pass  # No prompt, IP or request-path log.

    def guard(self, write=False):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host") not in hosts:
            self.respond(403, {"error": "Ugyldig vert."}); return False
        origin = self.headers.get("Origin")
        if origin and origin not in {"http://" + h for h in hosts}:
            self.respond(403, {"error": "Ekstern nettleseropprinnelse er sperret."}); return False
        if write and not hmac.compare_digest(self.headers.get("X-Demo-Token", ""), self.server.token):
            self.respond(403, {"error": "Mangler lokal sesjonsnøkkel. Last siden på nytt."}); return False
        return True

    def respond(self, status, data, mime="application/json; charset=utf-8"):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self.guard(): return
        if self.path == "/api/config":
            self.respond(200, {"token": self.server.token, "ollama_enabled": self.server.enable_ollama,
                "corpus_version": self.server.corpus["version"], "notice": self.server.corpus["notice"]})
        elif self.path == "/api/models":
            if not self.server.enable_ollama:
                self.respond(200, {"models": [], "notice": "Lokal modellkjøring er ikke aktivert."}); return
            try:
                self.respond(200, {"models": installed_models()})
            except DemoError as exc:
                self.respond(503, {"error": str(exc)})
        elif self.path in ("/", "/app.js", "/style.css"):
            name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[self.path]
            mime = {"/": "text/html", "/app.js": "text/javascript", "/style.css": "text/css"}[self.path]
            self.respond(200, (ROOT / "web" / name).read_bytes(), mime + "; charset=utf-8")
        else:
            self.respond(404, {"error": "Finnes ikke."})

    def do_POST(self):
        if not self.guard(write=True): return
        if self.path != "/api/ask":
            self.respond(404, {"error": "Finnes ikke."}); return
        if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            self.respond(415, {"error": "Bare JSON med kjent lengde støttes."}); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 8192: raise ValueError()
        except ValueError:
            self.respond(413, {"error": "Forespørselen er for stor eller mangler lengde."}); return
        with self.server.times_lock:
            now = time.monotonic()
            self.server.times = [x for x in self.server.times if now - x < 60]
            if len(self.server.times) >= 12:
                self.respond(429, {"error": "Demogrense: 12 spørsmål per minutt. Vent litt."}); return
            self.server.times.append(now)
        if not self.server.inference.acquire(blocking=False):
            self.respond(429, {"error": "Én jobb kjører allerede. Prøv igjen når den er ferdig."}); return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) - {"question", "mode", "model"}:
                raise DemoError("Ugyldige forespørselsfelter.")
            mode = payload.get("mode", "sources")
            if mode == "ollama" and not self.server.enable_ollama:
                raise DemoError("Lokal modellkjøring er ikke aktivert. Start med --ollama etter lokalsjekken.")
            result = ask(payload.get("question"), mode, payload.get("model", ""), self.server.corpus)
            self.respond(200, result)
        except (DemoError, ValueError, TypeError, TimeoutError):
            self.respond(422, {"error": "Ingen gyldig leveranse. Kontroller spørsmål, valgt lokal modell og Ollama. Ingen skyreserve brukes. Se veiledningen."})
        finally:
            self.server.inference.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--ollama", action="store_true", help="Tillat lokal modellkjøring etter kontroll av Ollama uten skyfunksjoner.")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Velg en port mellom 1024 og 65535.")
    with DemoServer(args.port, args.ollama) as server:
        print(f"Skyveiviser: http://127.0.0.1:{args.port} — bare lokale forespørsler.")
        print("Modus:", "kildesøk + lokal Ollama" if args.ollama else "kildesøk uten LLM")
        print("Bruk bare åpne testspørsmål. Stopp med Ctrl+C. Ingen spørsmålslogg lagres.")
        try: server.serve_forever()
        except KeyboardInterrupt: pass

if __name__ == "__main__":
    main()
