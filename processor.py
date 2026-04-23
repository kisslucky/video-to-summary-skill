#!/usr/bin/env python3
"""Acquire video content from multiple entry points and produce transcript artifacts."""

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
    """Raised when an external command fails or required input is missing."""


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


def create_job_dir(output_root: Path) -> Path:
    job_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    job_dir = output_root / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    return job_dir


def copy_into_job(src_path: Path, dest_path: Path) -> Path:
    if src_path.resolve() == dest_path.resolve():
        return dest_path
    shutil.copy2(src_path, dest_path)
    return dest_path


def build_download_commands(
    source_url: str,
    video_template: Path,
    audio_template: Path,
    browser: str | None,
    cookies_file: str | None,
    referer: str | None,
) -> list[list[str]]:
    common = ["yt-dlp", "--no-playlist", "--no-warnings"]
    if browser:
        common += ["--cookies-from-browser", browser]
    if cookies_file:
        common += ["--cookies", cookies_file]
    if referer:
        common += ["--add-header", f"Referer:{referer}"]

    return [
        common
        + [
            "-f",
            "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "--merge-output-format",
            "mp4",
            "-o",
            str(video_template),
            source_url,
        ],
        common
        + [
            "-x",
            "--audio-format",
            "m4a",
            "-o",
            str(audio_template),
            source_url,
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
    raise CommandError("No media file was produced")


def extract_audio(media_path: Path, audio_path: Path) -> Path:
    if media_path == audio_path:
        return media_path

    if media_path.suffix.lower() == ".m4a":
        copy_into_job(media_path, audio_path)
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


def build_summary_draft(page_url: str | None, title: str | None, transcript_text: str, summary_path: Path) -> None:
    sentences = split_sentences(transcript_text)
    highlights: list[str] = []
    seen: set[str] = set()

    for sentence in sentences:
        if len(sentence) < 16:
            continue
        if sentence in seen:
            continue
        seen.add(sentence)
        highlights.append(sentence)
        if len(highlights) == 5:
            break

    preview = normalize_text(transcript_text)[:800]
    lines = [
        "# Video Summary Draft",
        "",
    ]

    if title:
        lines.append(f"Title: {title}")
    if page_url:
        lines.append(f"Page URL: {page_url}")
    lines.extend(
        [
            f"Generated At: {datetime.now(timezone.utc).isoformat()}",
            f"Transcript Characters: {len(transcript_text)}",
            "",
            "## Draft Highlights",
        ]
    )

    if highlights:
        lines.extend(f"- {item}" for item in highlights)
    else:
        lines.append("- No strong sentence boundaries were detected; review the transcript directly.")

    lines.extend(
        [
            "",
            "## Transcript Preview",
            "",
            preview or "(empty transcript preview)",
            "",
            "## Next Step",
            "",
            "- Refine this draft in-agent if the user needs a polished deliverable.",
            "- If the source came from CDP or page captions, keep that provenance in the final answer.",
        ]
    )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a video URL, media file, or transcript file into transcript artifacts."
    )
    parser.add_argument("source", nargs="?", help="Source URL or signed media URL")
    parser.add_argument("--media-file", help="Local media file exported from browser/CDP or another workflow")
    parser.add_argument("--transcript-file", help="Local transcript or captions file extracted from the page")
    parser.add_argument("--page-url", help="Original page URL for provenance and summary metadata")
    parser.add_argument("--title", help="Video title or label to include in the draft summary")
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
    parser.add_argument("--cookies-file", default=None, help="Cookie file path for yt-dlp")
    parser.add_argument("--referer", default=None, help="Referer header for signed or page-bound media URLs")
    return parser.parse_args()


def resolve_mode(args: argparse.Namespace) -> str:
    if args.transcript_file:
        return "transcript-file"
    if args.media_file:
        return "media-file"
    if args.source:
        source_path = Path(args.source)
        if source_path.exists():
            args.media_file = str(source_path)
            return "media-file"
        return "url"
    raise CommandError("Provide one of: source URL, --media-file, or --transcript-file")


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    job_dir = create_job_dir(output_root)

    mode = resolve_mode(args)
    page_url = args.page_url or (args.source if mode == "url" else None)
    title = args.title

    transcript_path = job_dir / "transcript.txt"
    summary_path = job_dir / "summary.md"
    manifest_path = job_dir / "result.json"
    media_result: Path | None = None
    audio_path: Path | None = None

    if mode == "transcript-file":
        source_path = Path(args.transcript_file).resolve()
        if not source_path.exists():
            raise CommandError(f"Transcript file does not exist: {source_path}")
        transcript_path = copy_into_job(source_path, transcript_path)
        transcript_text = transcript_path.read_text(encoding="utf-8", errors="replace")
    else:
        ensure_dependency(["python", "--version"], "python")
        ensure_dependency(["ffmpeg", "-version"], "ffmpeg")
        ensure_dependency(["coli", "--help"], "coli")

        if mode == "media-file":
            source_path = Path(args.media_file).resolve()
            if not source_path.exists():
                raise CommandError(f"Media file does not exist: {source_path}")
            destination = job_dir / f"input{source_path.suffix.lower()}"
            media_result = copy_into_job(source_path, destination)
        else:
            ensure_dependency(["yt-dlp", "--version"], "yt-dlp")
            download_error: CommandError | None = None
            for command in build_download_commands(
                args.source,
                job_dir / "video.%(ext)s",
                job_dir / "audio.%(ext)s",
                args.cookies_from_browser,
                args.cookies_file,
                args.referer,
            ):
                try:
                    run_command(command, "Downloading source media", timeout=1800)
                    download_error = None
                    break
                except CommandError as exc:
                    download_error = exc
            if download_error is not None:
                raise download_error
            media_result = find_media_file(job_dir)

        if media_result is None:
            raise CommandError("No media input was resolved")

        audio_path = extract_audio(media_result, job_dir / "audio.m4a")
        transcript_text = transcribe_audio(audio_path, transcript_path)

    build_summary_draft(page_url, title, transcript_text, summary_path)

    result = {
        "status": "success",
        "mode": mode,
        "page_url": page_url,
        "title": title,
        "job_dir": str(job_dir),
        "media": str(media_result) if media_result else None,
        "audio": str(audio_path) if audio_path else None,
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
