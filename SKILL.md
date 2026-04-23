---
name: video-to-summary
description: Download a supported video URL, extract audio, transcribe it locally, and produce a draft summary with saved artifacts. Use when the user wants a transcript, notes, or a summary draft from Bilibili, YouTube, or other video URLs that `yt-dlp` can access.
license: MIT
metadata:
  openclaw:
    emoji: "🎬"
    category: "media"
    tags: ["video", "transcription", "summary", "yt-dlp", "ffmpeg"]
  hermes:
    tags: ["media", "video", "transcription", "summary", "research"]
    requires_toolsets: [terminal]
---

# Video to Summary

Turn a video URL into local artifacts: downloaded media, extracted audio, transcript, and a draft summary.

## Runtime Notes

- OpenClaw can use this skill directly as written.
- Hermes can also use this skill because it follows the standard `SKILL.md` layout. If Hermes is not already in the skill directory, call the helper script with `${HERMES_SKILL_DIR}/processor.py`.
- `backend-api.py` is an optional demo wrapper. It is not required for the core skill workflow.

## Core Rules

1. Start with transcript quality, not summary polish. A weak transcript makes the summary unreliable.
2. Check whether the source needs login, cookies, or cross-border access before running long downloads.
3. Keep outputs in a job-specific folder so retries do not overwrite earlier runs.
4. Treat the generated `summary.md` as a draft. Refine it in-agent when the user needs a higher-quality deliverable.
5. If download or transcription fails, report the failing stage and the missing dependency or platform restriction.

## Preflight Check

Confirm all of the following:

- `python --version`
- `yt-dlp --version`
- `ffmpeg -version`
- `coli --help`

If any dependency is missing, install it before continuing.

## Default Workflow

### 1. Inspect the source

- Prefer direct video URLs from Bilibili, YouTube, or other `yt-dlp`-supported sites.
- If the source is cookie-gated, add `--cookies-from-browser chrome` or another supported browser name.
- If the source is outside the current network region, stop and call that out before the run.

### 2. Run the processor

Use the bundled helper:

```bash
python processor.py "<video-url>"
```

For cookie-gated sources:

```bash
python processor.py "<video-url>" --cookies-from-browser chrome
```

### 3. Read the manifest

The script prints JSON with:

- `job_dir`
- `video`
- `audio`
- `transcript`
- `summary`

### 4. Refine the deliverable

- Read `transcript.txt`
- Check whether the draft `summary.md` is good enough
- If needed, replace the draft with a cleaner summary, action items, or structured notes for the user

## Output Contract

Each run writes a job directory containing:

- `video.*` or source media
- `audio.m4a`
- `transcript.txt`
- `summary.md`
- `result.json`

## Failure Handling

- download failure:
  - verify the URL
  - retry with `--cookies-from-browser`
  - call out region or membership restrictions
- transcription failure:
  - verify `coli` is installed and callable
  - confirm audio extraction succeeded first
- low-quality summary:
  - use the transcript as ground truth
  - regenerate the final answer in-agent instead of trusting the draft blindly

## Scope Boundary

- This skill covers local processing and draft summarization.
- It does not bundle a production web service, background queue, or email delivery workflow.
