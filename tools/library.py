"""Open your reel library in the browser.

Usage: uv run tools/library.py [--no-open]

Runs on this computer only. It reads the library folder on every request, so new
reels appear when the page refreshes.
"""

import json
import re
import socket
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "library"
PAGE = Path(__file__).resolve().parent / "library.html"
PORT = 4173
ADDRESS = f"http://localhost:{PORT}"
ALLOWED_HOSTS = {f"localhost:{PORT}", f"127.0.0.1:{PORT}"}
MEDIA_FILE = re.compile(r"^(video\.mp4|frames/frame_\d+\.jpg)$")
CHUNK = 1024 * 256


def read_text(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_reels():
    reels = []
    if not LIBRARY.exists():
        return reels
    for folder in LIBRARY.iterdir():
        info_file = folder / "info.json"
        if not info_file.exists():
            continue
        info = json.loads(info_file.read_text(encoding="utf-8"))
        frames = sorted(p.name for p in (folder / "frames").glob("frame_*.jpg"))
        reels.append({
            **info,
            "id": folder.name,
            "saved": folder.name[:10],
            "savedAt": info_file.stat().st_mtime,
            "transcript": read_text(folder / "transcript.txt"),
            "analysis": read_text(folder / "analysis.md"),
            "frames": frames,
        })
    reels.sort(key=lambda reel: reel["savedAt"], reverse=True)
    return reels


def parse_range(header, size):
    """Return (start, end) for a single-range request, or None if it can't be served."""
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if not match or (match.group(1) == "" and match.group(2) == ""):
        return None
    if match.group(1) == "":
        length = int(match.group(2))
        return (max(size - length, 0), size - 1) if length else None
    start = int(match.group(1))
    end = min(int(match.group(2)), size - 1) if match.group(2) else size - 1
    return (start, end) if start <= end and start < size else None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_bytes(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def serve_media(self, path):
        parts = path.removeprefix("/media/").split("/", 1)
        if len(parts) != 2 or not MEDIA_FILE.match(parts[1]) or "/" in parts[0] or parts[0] in ("", ".", ".."):
            self.send_error(404)
            return
        file = LIBRARY / parts[0] / parts[1]
        if not file.is_file():
            self.send_error(404)
            return

        size = file.stat().st_size
        start, end = 0, size - 1
        status = 200
        requested = self.headers.get("Range")
        if requested:
            span = parse_range(requested, size)
            if span is None:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            start, end = span
            status = 206

        self.send_response(status)
        self.send_header("Content-Type", "video/mp4" if file.suffix == ".mp4" else "image/jpeg")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()

        try:
            with file.open("rb") as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = stream.read(min(CHUNK, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass  # The player moved to another position and dropped this request.

    def do_GET(self):
        if self.headers.get("Host") not in ALLOWED_HOSTS:
            self.send_error(403)
            return
        path = unquote(urlsplit(self.path).path)
        if path == "/":
            self.send_bytes(PAGE.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/reels":
            self.send_bytes(json.dumps(load_reels()).encode("utf-8"), "application/json")
        elif path.startswith("/media/"):
            self.serve_media(path)
        else:
            self.send_error(404)


def already_running():
    with socket.socket() as probe:
        probe.settimeout(0.3)
        return probe.connect_ex(("127.0.0.1", PORT)) == 0


def main():
    should_open = "--no-open" not in sys.argv
    if already_running():
        print(f"Your library is already running at {ADDRESS}")
        if should_open:
            webbrowser.open(ADDRESS)
        return
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Your library is open at {ADDRESS}", flush=True)
    if should_open:
        webbrowser.open(ADDRESS)
    server.serve_forever()


if __name__ == "__main__":
    main()
