#!/usr/bin/env python3
"""Download a video, transcribe it locally, and write a summary draft."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = Path(
    os.environ.get("VIDEO_TO_SUMMARY_OUTPUT_DIR", str(SCRIPT_DIR / "outputs"))
)
MEDIA_EXTENSIONS = {".mp4", ".m4a", ".mp3", ".webm", ".mkv", ".mov", ".wav"}


class CommandError(RuntimeError):
    """Raised when an external command fails."""


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)


def run_command(command: list[str], description: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    log(description)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandError(f"{description} timed out after {timeout} seconds") from exc
    except FileNotFoundError as exc:
        raise CommandError(f"Missing dependency: {command[0]}") from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise CommandError(f"{description} failed: {stderr[:400]}")
    return completed


def ensure_dependency(command: list[str], label: str) -> None:
    run_command(command, f"Checking dependency: {label}", timeout=30)


def build_download_commands(url: str, video_template: Path, audio_template: Path, browser: str | None) -> list[list[str]]:
    common = ["yt-dlp", "--no-playlist", "--no-warnings"]
    if browser:
        common += ["--cookies-from-browser", browser]

    return [
        common
        + [
            "-f",
            "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "--merge-output-format",
            "mp4",
            "-o",
            str(video_template),
            url,
        ],
        common
        + [
            "-x",
            "--audio-format",
            "m4a",
            "-o",
            str(audio_template),
            url,
        ],
    ]


def find_media_file(job_dir: Path) -> Path:
    candidates = sorted(
        path for path in job_dir.iterdir() if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    )
    for preferred in candidates:
        if preferred.name.startswith("video."):
            return preferred
    for preferred in candidates:
        if preferred.name.startswith("audio."):
            return preferred
    if candidates:
        return candidates[0]
    raise CommandError("No media file was produced by yt-dlp")


def extract_audio(media_path: Path, audio_path: Path) -> Path:
    if media_path == audio_path:
        return media_path

    if media_path.suffix.lower() == ".m4a":
        shutil.copy2(media_path, audio_path)
        return audio_path

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(media_path),
            "-vn",
            "-acodec",
            "aac",
            "-b:a",
            "192k",
            str(audio_path),
        ],
        "Extracting audio with ffmpeg",
        timeout=600,
    )
    return audio_path


def extract_text_from_coli_output(raw_output: str) -> str:
    raw_output = raw_output.strip()
    if not raw_output:
        return ""

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return raw_output

    if isinstance(parsed, dict):
        if isinstance(parsed.get("text"), str):
            return parsed["text"].strip()
        if isinstance(parsed.get("segments"), list):
            texts = [segment.get("text", "").strip() for segment in parsed["segments"] if isinstance(segment, dict)]
            return "\n".join(text for text in texts if text)

    if isinstance(parsed, list):
        texts: list[str] = []
        for item in parsed:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                texts.append(item["text"].strip())
            elif isinstance(item, str):
                texts.append(item.strip())
        return "\n".join(text for text in texts if text)

    return raw_output


def transcribe_audio(audio_path: Path, transcript_path: Path) -> str:
    try:
        completed = run_command(
            ["coli", "asr", str(audio_path), "--json"],
            "Transcribing audio with coli",
            timeout=1800,
        )
        transcript_text = extract_text_from_coli_output(completed.stdout)
    except CommandError:
        completed = run_command(
            ["coli", "asr", str(audio_path)],
            "Retrying transcription with plain output",
            timeout=1800,
        )
        transcript_text = completed.stdout.strip()

    if not transcript_text:
        raise CommandError("No transcript text was returned by coli")

    transcript_path.write_text(transcript_text, encoding="utf-8")
    return transcript_text


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？!?\.])\s+", normalized)
    return [part.strip() for part in parts if part.strip()]


def build_summary_draft(url: str, transcript_text: str, summary_path: Path) -> None:
    sentences = split_sentences(transcript_text)
    highlights: list[str] = []
    seen: set[str] = set()

    for sentence in sentences:
        compact = sentence.strip()
        if len(compact) < 16:
            continue
        if compact in seen:
            continue
        seen.add(compact)
        highlights.append(compact)
        if len(highlights) == 5:
            break

    preview = normalize_text(transcript_text)[:600]
    line_count = len([line for line in transcript_text.splitlines() if line.strip()])

    lines = [
        "# Video Summary Draft",
        "",
        f"Source URL: {url}",
        f"Generated At: {datetime.now(timezone.utc).isoformat()}",
        f"Transcript Characters: {len(transcript_text)}",
        f"Transcript Lines: {line_count}",
        "",
        "## Draft Highlights",
    ]

    if highlights:
        lines.extend(f"- {item}" for item in highlights)
    else:
        lines.append("- No strong sentence boundaries were detected; use the transcript directly.")

    lines.extend(
        [
            "",
            "## Transcript Preview",
            "",
            preview or "(empty transcript preview)",
            "",
            "## Next Step",
            "",
            "- Review `transcript.txt` and rewrite this draft into a user-facing summary if higher quality is needed.",
        ]
    )

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_job_dir(output_root: Path) -> Path:
    job_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    job_dir = output_root / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    return job_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a video, transcribe it, and write a draft summary.")
    parser.add_argument("url", help="Video URL supported by yt-dlp")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory where job folders should be created",
    )
    parser.add_argument(
        "--cookies-from-browser",
        default=None,
        help="Browser name to pass through to yt-dlp for logged-in downloads",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    ensure_dependency(["python", "--version"], "python")
    ensure_dependency(["yt-dlp", "--version"], "yt-dlp")
    ensure_dependency(["ffmpeg", "-version"], "ffmpeg")
    ensure_dependency(["coli", "--help"], "coli")

    job_dir = create_job_dir(output_root)
    video_template = job_dir / "video.%(ext)s"
    audio_template = job_dir / "audio.%(ext)s"
    transcript_path = job_dir / "transcript.txt"
    summary_path = job_dir / "summary.md"
    manifest_path = job_dir / "result.json"

    download_error: CommandError | None = None
    for command in build_download_commands(args.url, video_template, audio_template, args.cookies_from_browser):
        try:
            run_command(command, "Downloading source media", timeout=1800)
            download_error = None
            break
        except CommandError as exc:
            download_error = exc

    if download_error is not None:
        raise download_error

    media_path = find_media_file(job_dir)
    audio_path = extract_audio(media_path, job_dir / "audio.m4a")
    transcript_text = transcribe_audio(audio_path, transcript_path)
    build_summary_draft(args.url, transcript_text, summary_path)

    result = {
        "status": "success",
        "source_url": args.url,
        "job_dir": str(job_dir),
        "video": str(media_path) if media_path.exists() else None,
        "audio": str(audio_path) if audio_path.exists() else None,
        "transcript": str(transcript_path),
        "summary": str(summary_path),
    }
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CommandError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
