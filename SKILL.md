---
name: video-to-summary
description: Acquire video content through direct download or interactive browser access, then turn it into transcript-backed notes and summary artifacts. Use when the user gives a video or short-video URL and needs a transcript, captions, or a summary from platforms that may require login, cookies, CDP, or browser interaction.
license: MIT
metadata:
  openclaw:
    emoji: "🎬"
    category: "media"
    tags: ["video", "transcription", "summary", "cdp", "web-access"]
  hermes:
    tags: ["media", "video", "transcription", "summary", "browser", "research"]
    requires_toolsets: [terminal, web]
---

# Video to Summary

Turn a video page, media file, or transcript source into transcript-backed notes, even when the source is JS-heavy, login-gated, or interaction-heavy.

## Runtime Notes

- OpenClaw users should route through `web-access` when direct download is weak, blocked, or login-gated.
- Hermes users can apply the same workflow by mapping `web-access` to browser tools plus `web_search` / `web_extract`.
- `browser-troubleshooting` is the fallback when CDP or browser connectivity is the blocker, not the video source itself.

## Core Rules

1. Choose the minimum access tier that can obtain transcript-grade content.
2. If the source is short-video, JS-heavy, anti-bot, or login-gated, escalate to browser interaction early instead of retrying `yt-dlp` blindly.
3. Prefer captions or transcript text over OCR or screenshots whenever the page exposes them.
4. Use frame sampling only when audio or captions cannot be retrieved.
5. Separate acquisition failure, transcription failure, and summarization failure in both debugging and reporting.

## Access Tiers

| Tier | Use when | Primary path | Fallback |
| --- | --- | --- | --- |
| `T0` direct | public page or direct media URL works | `processor.py "<url>"` | `T1` |
| `T1` authenticated download | cookies, referer, or signed media URL needed | `processor.py "<url>" --cookies-from-browser chrome --referer "<page-url>"` | `T2` |
| `T2` interactive browser | JS-heavy page, short-video app, login wall, anti-bot, or hidden captions | `web-access` + CDP to retrieve page transcript, media URL, or browser-exported assets | `T3` |
| `T3` browser recovery | CDP, proxy, or browser state itself is broken | `browser-troubleshooting` or `agent-browser-core` | ask for user intervention |

## Skill Routing

Use the minimum toolchain that can complete the job:

| Need | Route |
| --- | --- |
| public Bilibili / normal media page | local `processor.py` |
| page requires cookies or signed headers | local `processor.py` with `--cookies-from-browser`, `--cookies-file`, or `--referer` |
| captions already visible on the page | `web-access` to collect captions, then `processor.py --transcript-file ...` |
| media already exported or captured locally | `processor.py --media-file ...` |
| page needs clicks, scrolling, login, or CDP evaluation | `web-access` |
| browser/CDP is broken | `browser-troubleshooting` |
| long, multi-step browser automation with repeated DOM actions | `agent-browser-core` or `web-access` CDP mode |

## Preflight

Before the main run, confirm:

1. whether the user wants transcript only, draft summary, or a polished final brief
2. whether the source is public, cross-border, login-gated, or anti-bot
3. whether captions may already exist on the page
4. whether local artifacts should be kept
5. which language the summary should be written in

## Default Workflow

### 1. Classify the source

- Direct/public page: start with `T0`
- Cookie-gated or signed URL: start with `T1`
- Short-video platform, JS-heavy player, or login wall: start with `T2`

### 2. Acquire the content

Examples:

```bash
python processor.py "<video-url>"
python processor.py "<video-url>" --cookies-from-browser chrome
python processor.py "<signed-media-url>" --referer "<page-url>" --title "<video-title>"
python processor.py --media-file "C:/path/to/audio.m4a" --page-url "<page-url>" --title "<video-title>"
python processor.py --transcript-file "C:/path/to/captions.txt" --page-url "<page-url>" --title "<video-title>"
```

### 3. Use browser interaction when needed

- Use `web-access` CDP mode to open the page in a logged-in browser
- click, scroll, expand captions, or seek video as needed
- extract transcript text, title, or media URL
- feed the extracted asset back into `processor.py`

### 4. Normalize and summarize

- inspect `transcript.txt`
- use the generated `summary.md` only as a draft
- rewrite or refine the final deliverable in-agent if the user needs quality output

## Output Contract

Each successful run writes a job directory containing:

- `audio.m4a` when audio is available
- `transcript.txt`
- `summary.md`
- `result.json`
- optional copied or downloaded media file

## Failure Handling

- `yt-dlp` bot / sign-in error:
  - move to `T1` or `T2`
  - use browser cookies or CDP browser state
- JS-heavy page with hidden captions:
  - use `web-access` to expand or extract them
- DRM or inaccessible media:
  - fall back to visible captions, frame sampling, or user-supplied transcript
  - clearly state the limitation
- CDP proxy or browser failure:
  - route to `browser-troubleshooting`

## References

Read these only when needed:

- `references/access-routing.md`
  Use when deciding between direct download, cookies, transcript import, or CDP.
- `references/cdp-patterns.md`
  Use when the source requires clicks, scrolling, caption expansion, or browser-side extraction.
- `references/failure-handling.md`
  Use when acquisition or browser setup keeps failing.
