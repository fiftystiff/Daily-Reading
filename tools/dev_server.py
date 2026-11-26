"""Development server: test the page in an ordinary browser with the app's real Python code.

    python tools/dev_server.py [port] [bibles folder]   (default port 8766, Daily-Reading_bibles)
    then open  http://localhost:8766/index.html#themes=x

It serves the project folder and answers POST /api/<method> with the same methods the
desktop app offers (app.py's Api). Settings, keys and schedules are kept apart from your
real ones: a throwaway AppData folder, and a fresh copy of Daily-Reading_schedules (so
ticking boxes while testing doesn't change the real files). Put API keys in
tools/.dev-keys.txt (same format as Daily-Reading_keys.txt) to test the online translations.

In the page, run this in the browser console to connect it, as pywebview does in the app:

    const call = n => (...a) => fetch(`/api/${n}`, {method: "POST", body: JSON.stringify(a)}).then(r => r.json());
    window.pywebview = {api: new Proxy({}, {get: (_, n) => call(n)})};
    window.dispatchEvent(new Event("pywebviewready"));
"""
import http.server
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
# Optional second argument: another folder of XML bibles to use (only read)
BIBLES = Path(sys.argv[2]) if len(sys.argv) > 2 else PROJECT / "Daily-Reading_bibles"

work = Path(tempfile.mkdtemp(prefix="daily-reading-dev-"))
os.environ["APPDATA"] = str(work / "appdata")
schedules_copy = work / "Daily-Reading_schedules"
if (PROJECT / "Daily-Reading_schedules").is_dir():
    shutil.copytree(PROJECT / "Daily-Reading_schedules", schedules_copy)
themes_copy = work / "Daily-Reading_themes"
if (PROJECT / "Daily-Reading_themes").is_dir():
    shutil.copytree(PROJECT / "Daily-Reading_themes", themes_copy)
if (TOOLS / ".dev-keys.txt").is_file():
    shutil.copy(TOOLS / ".dev-keys.txt", work / "Daily-Reading_keys.txt")

sys.path.insert(0, str(PROJECT))
os.chdir(PROJECT)
import app  # noqa: E402  (app.Api finds the keys file and schedules folder beside the themes folder)

api = app.Api(str(themes_copy), str(BIBLES))   # the XML bibles (only read)
print(f"Serving {PROJECT} on http://localhost:{PORT}/index.html#themes=x", flush=True)
print(f"Test copies (schedules, themes, settings) in {work}", flush=True)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        name = self.path.rsplit("/", 1)[-1]
        args = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"[]")
        method = getattr(api, name, None)
        if name.startswith("_") or not callable(method):
            result = {"ok": False, "error": f"no such method: {name}"}
        else:
            try:
                result = method(*args)
            except Exception as err:   # report it to the page like pywebview would
                result = {"ok": False, "error": f"{type(err).__name__}: {err}"}
        if name == "report_fums":
            print("FUMS report:", len(args[0]) if args else 0, "token(s)", flush=True)
        body = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")   # always the latest index.html
        super().end_headers()

    def log_message(self, fmt, *a):
        if "POST" in (fmt % a):
            print(fmt % a, flush=True)


http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
