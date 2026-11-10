"""Download one public Instagram reel and prepare it for analysis.

Usage: uv run tools/process.py <instagram-link>

Creates library/<date>_<creator>_<code>/ containing video.mp4, info.json,
transcript.txt and frames/. The folder path is the last line printed.
"""

import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "library"
FRAME_COUNT = 12
WHISPER_MODEL = "small"
LINK_PATTERN = re.compile(r"^/(?:[\w.]+/)?(?:reel|reels|p)/([\w-]+)/?$")


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def clean_link(raw):
    """Accept only Instagram reel or post links, and drop tracking parameters."""
    parts = urlsplit(raw.strip())
    if parts.scheme != "https" or parts.netloc not in ("www.instagram.com", "instagram.com"):
        fail("That isn't an Instagram link. Send a link that starts with https://www.instagram.com/")
    match = LINK_PATTERN.match(parts.path)
    if not match:
        fail("That Instagram link isn't a reel or a post.")
    code = match.group(1)
    return f"https://www.instagram.com/reel/{code}/", code


def run(command, what):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-5:])
        fail(f"{what} failed.\n{tail}")
    return result.stdout


def fetch_info(link):
    output = run(
        [sys.executable, "-m", "yt_dlp", "--dump-json", "--no-warnings", "--", link],
        "Reading the reel's details",
    )
    return json.loads(output)


def find_existing(code):
    if not LIBRARY.exists():
        return None
    for folder in LIBRARY.iterdir():
        if folder.is_dir() and folder.name.endswith(f"_{code}") and (folder / "transcript.txt").exists():
            return folder
    return None


def safe_name(text):
    return re.sub(r"[^\w.-]+", "-", text or "unknown").strip("-")[:40] or "unknown"


def download(link, folder, ffmpeg):
    run(
        [
            sys.executable, "-m", "yt_dlp",
            "--no-warnings",
            "--ffmpeg-location", ffmpeg,
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
            "--merge-output-format", "mp4",
            "-o", str(folder / "video.%(ext)s"),
            "--", link,
        ],
        "Downloading the video",
    )
    video = folder / "video.mp4"
    if not video.exists():
        fail("The download finished, but no video file was saved.")
    return video


def transcribe(video, folder):
    from faster_whisper import WhisperModel

    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(video), vad_filter=True)
    lines = []
    for segment in segments:
        minutes, seconds = divmod(int(segment.start), 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {segment.text.strip()}")
    (folder / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def extract_frames(video, folder, ffmpeg, duration):
    frames = folder / "frames"
    frames.mkdir(exist_ok=True)
    rate = FRAME_COUNT / max(duration, 1)
    run(
        [
            ffmpeg, "-y", "-v", "error", "-i", str(video),
            "-vf", f"fps={rate:.5f},scale=720:-2",
            "-frames:v", str(FRAME_COUNT),
            str(frames / "frame_%02d.jpg"),
        ],
        "Pulling frames",
    )


def main():
    if len(sys.argv) != 2:
        fail("Send exactly one Instagram link.")
    link, code = clean_link(sys.argv[1])

    existing = find_existing(code)
    if existing:
        print("Already in your library.")
        print(existing)
        return

    info = fetch_info(link)
    creator = info.get("channel") or info.get("uploader_id") or info.get("uploader")
    date = datetime.date.today().isoformat()
    LIBRARY.mkdir(exist_ok=True)
    folder = LIBRARY / f"{date}_{safe_name(creator)}_{code}"
    folder.mkdir(exist_ok=True)

    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        print("Downloading...", flush=True)
        video = download(link, folder, ffmpeg)
        duration = imageio_ffmpeg.count_frames_and_secs(str(video))[1]
        print("Transcribing...", flush=True)
        transcribe(video, folder)
        print("Pulling frames...", flush=True)
        extract_frames(video, folder, ffmpeg, duration)
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise

    details = {
        "url": link,
        "creator": creator,
        "caption": info.get("description") or "",
        "duration_seconds": round(duration),
        "posted": info.get("upload_date"),
        "likes": info.get("like_count"),
        "comments": info.get("comment_count"),
    }
    (folder / "info.json").write_text(json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
    print(folder)


if __name__ == "__main__":
    main()
