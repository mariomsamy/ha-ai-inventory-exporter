#!/usr/bin/env python3

import argparse
import html
import json
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    output_path: Path

    @property
    def status_path(self):
        return self.output_path.parent / "export_status.json"

    def log_message(self, fmt, *args):
        return

    def send_html(self, body: str, status: int = 200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/refresh":
            self.refresh()
            return
        if parsed.path == "/download":
            self.download()
            return
        self.index()

    def refresh(self):
        try:
            result = subprocess.run(
                ["/usr/bin/export_inventory.py", "--output", str(self.output_path)],
                text=True,
                capture_output=True,
                timeout=180,
                check=False,
            )
            status = {
                "ok": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:],
            }
        except Exception as exc:
            status = {
                "ok": False,
                "error": str(exc),
            }
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
        qs = parse_qs(urlparse(self.path).query)
        redirect = qs.get("next", ["/"])[0] or "/"
        self.send_response(303)
        self.send_header("Location", redirect)
        self.end_headers()

    def download(self):
        if not self.output_path.exists():
            self.send_error(404, "Inventory has not been generated yet")
            return
        data = self.output_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Content-Disposition",
            'attachment; filename="home_assistant_full_inventory.json"',
        )
        self.end_headers()
        self.wfile.write(data)

    def index(self):
        generated_at = "Not generated yet"
        stats = {}
        size = "-"
        public_path = "/local/ai/home_assistant_full_inventory.json"
        status = None

        if self.output_path.exists():
            size = f"{self.output_path.stat().st_size / 1024 / 1024:.1f} MB"
            try:
                data = json.loads(self.output_path.read_text(encoding="utf-8"))
                generated_at = data.get("metadata", {}).get("generated_at", generated_at)
                stats = data.get("statistics", {})
            except Exception as exc:
                generated_at = f"Could not read JSON: {exc}"

        if self.status_path.exists():
            try:
                status = json.loads(self.status_path.read_text(encoding="utf-8"))
            except Exception as exc:
                status = {"ok": False, "error": f"Could not read status: {exc}"}

        stat_rows = "".join(
            f"<div><strong>{html.escape(str(k))}</strong><span>{html.escape(str(v))}</span></div>"
            for k, v in stats.items()
        )
        if status is None:
            status_html = "<p>No export status yet. Click <strong>Generate now</strong>.</p>"
        elif status.get("ok"):
            warning = status.get("warning") or ""
            status_html = (
                "<p><strong>Status:</strong> OK</p>"
                f"<p><strong>Mode:</strong> {html.escape(str(status.get('mode', 'unknown')))}</p>"
                f"<p><strong>Warning:</strong> {html.escape(str(warning or 'None'))}</p>"
            )
        else:
            status_html = (
                "<p><strong>Status:</strong> Failed</p>"
                f"<pre>{html.escape(json.dumps(status, indent=2)[-4000:])}</pre>"
            )

        body = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Inventory</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body {{ margin: 0; padding: 24px; background: var(--primary-background-color, #101418); color: var(--primary-text-color, #f4f7fb); }}
    main {{ max-width: 860px; margin: 0 auto; display: grid; gap: 16px; }}
    .hero {{ display: grid; gap: 8px; }}
    h1 {{ margin: 0; font-size: 28px; }}
    p {{ margin: 0; color: var(--secondary-text-color, #aab4c0); line-height: 1.5; }}
    .card {{ border: 1px solid rgba(140, 150, 170, .28); border-radius: 8px; padding: 16px; background: rgba(255,255,255,.04); }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    a.button {{ text-decoration: none; color: white; background: #2563eb; border-radius: 6px; padding: 10px 14px; font-weight: 650; }}
    a.secondary {{ background: rgba(148,163,184,.18); }}
    code {{ overflow-wrap: anywhere; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; }}
    .stats div {{ border: 1px solid rgba(140, 150, 170, .2); border-radius: 6px; padding: 10px; display: grid; gap: 3px; }}
    .stats span {{ color: var(--secondary-text-color, #aab4c0); }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; color: #fecaca; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>AI Inventory</h1>
      <p>Automatic Home Assistant inventory export for AI-assisted automations, dashboards, and reviews.</p>
    </section>
    <section class="card">
      <p><strong>Last generated:</strong> {html.escape(generated_at)}</p>
      <p><strong>Size:</strong> {html.escape(size)}</p>
      <p><strong>Output:</strong> <code>{html.escape(str(self.output_path))}</code></p>
      <p><strong>Public URL:</strong> <code>{html.escape(public_path)}</code></p>
    </section>
    <section class="card">
      <h2>Export status</h2>
      {status_html}
    </section>
    <section class="actions">
      <a class="button" href="./refresh">Generate now</a>
      <a class="button secondary" href="./download">Download JSON</a>
      <a class="button secondary" href="{html.escape(public_path)}">Open public JSON</a>
    </section>
    <section class="card">
      <h2>Statistics</h2>
      <div class="stats">{stat_rows or "<p>No statistics yet.</p>"}</div>
    </section>
  </main>
</body>
</html>"""
        self.send_html(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()

    Handler.output_path = Path(args.output)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
