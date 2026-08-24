#!/usr/bin/env python3

import argparse
import html
import json
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


class Handler(BaseHTTPRequestHandler):
    output_path: Path

    @property
    def status_path(self):
        return self.output_path.parent / "export_status.json"

    def log_message(self, fmt, *args):
        return

    @staticmethod
    def display_output_path(path: Path) -> str:
        text = str(path)
        if text.startswith("/homeassistant/"):
            return "/config/" + text.removeprefix("/homeassistant/")
        return text

    def send_html(self, body: str, status: int = 200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload, status: int = 200):
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/api/status", "/status"):
            self.send_json(self.read_summary())
            return
        if parsed.path in ("/api/generate", "/refresh"):
            self.generate()
            return
        if parsed.path in ("/api/download", "/download"):
            self.download()
            return
        if parsed.path in ("/api/inventory", "/inventory"):
            self.inventory()
            return
        self.index()

    def generate(self):
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
        self.send_json(self.read_summary())

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

    def inventory(self):
        if not self.output_path.exists():
            self.send_json({"ok": False, "error": "Inventory has not been generated yet"}, 404)
            return
        try:
            data = json.loads(self.output_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)
            return
        self.send_json({"ok": True, "inventory": data})

    def read_summary(self):
        generated_at = "Not generated yet"
        stats = {}
        size = "-"
        public_path = "/local/ai/home_assistant_full_inventory.json"
        status = None
        preview = None

        if self.output_path.exists():
            size = f"{self.output_path.stat().st_size / 1024 / 1024:.1f} MB"
            try:
                data = json.loads(self.output_path.read_text(encoding="utf-8"))
                generated_at = data.get("metadata", {}).get("generated_at", generated_at)
                stats = data.get("statistics", {})
                preview = {
                    "metadata": data.get("metadata", {}),
                    "statistics": data.get("statistics", {}),
                    "indexes": {
                        key: value
                        for key, value in data.get("indexes", {}).items()
                        if key in ("entities_by_area", "entities_by_domain")
                    },
                }
            except Exception as exc:
                generated_at = f"Could not read JSON: {exc}"

        if self.status_path.exists():
            try:
                status = json.loads(self.status_path.read_text(encoding="utf-8"))
            except Exception as exc:
                status = {"ok": False, "error": f"Could not read status: {exc}"}

        return {
            "ok": bool(status and status.get("ok")),
            "generated_at": generated_at,
            "size": size,
            "stats": stats,
            "status": status,
            "output_path": self.display_output_path(self.output_path),
            "public_path": public_path,
            "preview": preview,
        }

    def index(self):
        summary = self.read_summary()
        generated_at = summary["generated_at"]
        stats = summary["stats"]
        size = summary["size"]
        public_path = summary["public_path"]
        status = summary["status"]

        stat_rows = "".join(
            f"<div class=\"stat\"><span>{html.escape(str(k).replace('_', ' ').title())}: </span><strong>{html.escape(str(v))}</strong></div>"
            for k, v in stats.items()
        )
        if status is None:
            status_html = (
                "<div class=\"status-row\">"
                "<span class=\"status-dot idle\"></span>"
                "<div><strong>Waiting for first export</strong><p>Click Generate now to create the inventory JSON.</p></div>"
                "</div>"
            )
        elif status.get("ok"):
            warning = status.get("warning") or ""
            status_html = (
                "<div class=\"status-row\">"
                "<span class=\"status-dot ok\"></span>"
                "<div>"
                "<strong>Export ready</strong><br>"
                f"<p>Mode: {html.escape(str(status.get('mode', 'unknown')))}</p>"
                f"<p>{html.escape(str(warning or 'No warnings'))}</p>"
                "</div>"
                "</div>"
            )
        else:
            status_html = (
                "<div class=\"status-row\">"
                "<span class=\"status-dot failed\"></span>"
                "<div><strong>Export failed</strong><p>Open the details below or check the add-on log.</p></div>"
                "</div>"
                "<details><summary>Error details</summary>"
                f"<pre>{html.escape(json.dumps(status, indent=2)[-4000:])}</pre>"
                "</details>"
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
      --ai-primary: var(--primary-color, #03a9f4);
      --ai-card: var(--card-background-color, #fff);
      --ai-background: var(--primary-background-color, #fafafa);
      --ai-text: var(--primary-text-color, #212121);
      --ai-secondary: var(--secondary-text-color, #727272);
      --ai-divider: var(--divider-color, rgba(0, 0, 0, .12));
      --ai-radius: var(--ha-card-border-radius, 12px);
      --ai-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0, 0, 0, .16));
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 16px;
      background: var(--ai-background);
      color: var(--ai-text);
      font-size: 14px;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      display: grid;
      gap: 16px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 48px minmax(0, 1fr);
      gap: 12px;
      align-items: center;
      padding: 4px 2px;
    }}
    .hero-icon {{
      width: 48px;
      height: 48px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background: color-mix(in srgb, var(--ai-primary) 16%, transparent);
      color: var(--ai-primary);
      font-size: 26px;
    }}
    h1, h2 {{ margin: 0; font-weight: 500; letter-spacing: 0; }}
    h1 {{ font-size: 24px; line-height: 1.2; }}
    h2 {{ font-size: 20px; line-height: 1.3; padding-bottom: 4px; }}
    p {{ margin: 0; color: var(--ai-secondary); line-height: 1.45; }}
    .layout {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(280px, .75fr); gap: 16px; }}
    .stack {{ display: grid; gap: 16px; }}
    .card {{
      border: 1px solid var(--ai-divider);
      border-radius: var(--ai-radius);
      padding: 16px;
      background: var(--ai-card);
      box-shadow: var(--ai-shadow);
      display: grid;
      gap: 12px;
    }}
    .meta {{ display: grid; gap: 10px; }}
    .meta-row {{ display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: 12px; align-items: start; }}
    .meta-row span {{ color: var(--ai-secondary); }}
    .actions {{ display: grid; gap: 8px; }}
    button, a.button {{
      min-height: 44px;
      display: grid;
      grid-template-columns: 24px minmax(0, 1fr);
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: var(--text-primary-color, #fff);
      background: var(--ai-primary);
      border-radius: 8px;
      padding: 10px 14px;
      font-weight: 500;
      border: 0;
      cursor: pointer;
      width: 100%;
      font: inherit;
      text-align: left;
    }}
    button.secondary, a.secondary {{
      color: var(--ai-text);
      background: color-mix(in srgb, var(--ai-primary) 10%, var(--ai-card));
      border: 1px solid var(--ai-divider);
    }}
    button:disabled {{ opacity: .62; cursor: progress; }}
    code {{
      overflow-wrap: anywhere;
      color: var(--ai-text);
      background: color-mix(in srgb, var(--ai-secondary) 10%, transparent);
      border-radius: 6px;
      padding: 2px 5px;
    }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(132px, 1fr)); gap: 8px; }}
    .stat {{
      border: 1px solid var(--ai-divider);
      border-radius: 8px;
      padding: 12px;
      display: grid;
      gap: 4px;
      background: color-mix(in srgb, var(--ai-primary) 4%, var(--ai-card));
    }}
    .stat span {{ color: var(--ai-secondary); font-size: 12px; }}
    .stat strong {{ font-size: 20px; font-weight: 500; }}
    .status-row {{ display: grid; grid-template-columns: 14px minmax(0, 1fr); gap: 12px; align-items: start; }}
    .status-row strong {{ font-weight: 500; }}
    .status-dot {{ width: 12px; height: 12px; border-radius: 50%; margin-top: 4px; }}
    .status-dot.ok {{ background: var(--success-color, #43a047); }}
    .status-dot.failed {{ background: var(--error-color, #db4437); }}
    .status-dot.idle {{ background: var(--warning-color, #ffa600); }}
    details {{ border-top: 1px solid var(--ai-divider); padding-top: 10px; }}
    summary {{ cursor: pointer; color: var(--ai-primary); }}
    pre {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      color: var(--error-color, #db4437);
      background: color-mix(in srgb, var(--error-color, #db4437) 8%, transparent);
      border-radius: 8px;
      padding: 12px;
    }}
    .preview {{
      max-height: 360px;
      overflow: auto;
      color: var(--ai-text);
      background: color-mix(in srgb, var(--ai-secondary) 8%, var(--ai-card));
      border: 1px solid var(--ai-divider);
    }}
    .toast {{
      min-height: 22px;
      color: var(--ai-secondary);
    }}
    @media (max-width: 760px) {{
      body {{ padding: 12px; }}
      .layout {{ grid-template-columns: 1fr; }}
      .meta-row {{ grid-template-columns: 1fr; gap: 3px; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="hero-icon">⌂</div>
      <div>
        <h1>AI Inventory</h1>
        <p>Automatic Home Assistant inventory export for automations, dashboards, and reviews.</p>
      </div>
    </section>
    <div class="layout">
      <div class="stack">
        <section class="card">
          <h2>Export status</h2>
          <div id="status">{status_html}</div>
        </section>
        <section class="card">
          <h2>Statistics</h2>
          <div class="stats" id="stats">{stat_rows or "<p>No statistics yet.</p>"}</div>
        </section>
        <section class="card">
          <h2>JSON preview</h2>
          <pre class="preview" id="preview">Loading preview...</pre>
        </section>
      </div>
      <div class="stack">
        <section class="card">
          <h2>Inventory file</h2>
          <div class="meta">
            <div class="meta-row"><span>Generated: </span><strong id="generated-at">{html.escape(generated_at)}</strong></div>
            <div class="meta-row"><span>Size: </span><strong id="size">{html.escape(size)}</strong></div>
            <div class="meta-row"><span>Output: </span><code id="output-path">{html.escape(summary["output_path"])}</code></div>
            <div class="meta-row"><span>Public URL: </span><code id="public-path">{html.escape(public_path)}</code></div>
          </div>
        </section>
        <section class="card">
          <h2>Actions</h2>
          <div class="actions">
            <button class="button" id="generate" type="button"><span>↻</span><span>Generate now</span></button>
            <button class="button secondary" id="download" type="button"><span>⇩</span><span>Download JSON</span></button>
            <button class="button secondary" id="view-json" type="button"><span>{{}}</span><span>Show full JSON here</span></button>
          </div>
          <p class="toast" id="toast"></p>
        </section>
      </div>
    </div>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);

    function esc(value) {{
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }}[char]));
    }}

    function statusHtml(status) {{
      if (!status) {{
        return '<div class="status-row"><span class="status-dot idle"></span><div><strong>Waiting for first export</strong><p>Click Generate now to create the inventory JSON.</p></div></div>';
      }}
      if (status.ok) {{
        const warning = status.warning || "No warnings";
        const mode = status.mode || "unknown";
        return `<div class="status-row"><span class="status-dot ok"></span><div><strong>Export ready</strong><br><p>Mode: ${{esc(mode)}}</p><p>${{esc(warning)}}</p></div></div>`;
      }}
      return `<div class="status-row"><span class="status-dot failed"></span><div><strong>Export failed</strong><p>Check the details below or the add-on log.</p></div></div><details><summary>Error details</summary><pre>${{esc(JSON.stringify(status, null, 2).slice(-4000))}}</pre></details>`;
    }}

    function statsHtml(stats) {{
      const entries = Object.entries(stats || {{}});
      if (!entries.length) return "<p>No statistics yet.</p>";
      return entries.map(([key, value]) => `<div class="stat"><span>${{esc(key.replaceAll("_", " ").replace(/\\b\\w/g, c => c.toUpperCase()))}}: </span><strong>${{esc(value)}}</strong></div>`).join("");
    }}

    function render(summary) {{
      $("status").innerHTML = statusHtml(summary.status);
      $("stats").innerHTML = statsHtml(summary.stats);
      $("generated-at").textContent = summary.generated_at || "Not generated yet";
      $("size").textContent = summary.size || "-";
      $("output-path").textContent = summary.output_path || "";
      $("public-path").textContent = summary.public_path || "";
      $("preview").textContent = summary.preview ? JSON.stringify(summary.preview, null, 2) : "No JSON generated yet.";
    }}

    async function loadStatus() {{
      const response = await fetch("./api/status", {{cache: "no-store"}});
      render(await response.json());
    }}

    async function generate() {{
      const button = $("generate");
      button.disabled = true;
      $("toast").textContent = "Generating inventory...";
      try {{
        const response = await fetch("./api/generate", {{cache: "no-store"}});
        const summary = await response.json();
        render(summary);
        $("toast").textContent = summary.ok ? "Inventory generated." : "Generate failed. See status details.";
      }} catch (error) {{
        $("toast").textContent = `Generate failed: ${{error}}`;
      }} finally {{
        button.disabled = false;
      }}
    }}

    async function showFullJson() {{
      $("toast").textContent = "Loading full JSON inside this page...";
      const response = await fetch("./api/inventory", {{cache: "no-store"}});
      const payload = await response.json();
      $("preview").textContent = JSON.stringify(payload.inventory || payload, null, 2);
      $("toast").textContent = response.ok ? "Full JSON loaded below." : "Could not load JSON.";
    }}

    async function downloadJson() {{
      $("toast").textContent = "Preparing download...";
      const response = await fetch("./api/download", {{cache: "no-store"}});
      if (!response.ok) {{
        $("toast").textContent = "Inventory is not ready yet.";
        return;
      }}
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "home_assistant_full_inventory.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      $("toast").textContent = "Download started.";
    }}

    $("generate").addEventListener("click", generate);
    $("download").addEventListener("click", downloadJson);
    $("view-json").addEventListener("click", showFullJson);
    loadStatus().catch((error) => {{
      $("toast").textContent = `Could not load status: ${{error}}`;
    }});
  </script>
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
