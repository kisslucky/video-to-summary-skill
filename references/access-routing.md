# Access Routing

Choose the lightest acquisition path that can still reach transcript-grade content.

## Route Matrix

| Situation | Preferred path | Why |
| --- | --- | --- |
| public Bilibili / public media page | direct `processor.py "<url>"` | fastest path |
| YouTube or page blocked by anti-bot | `processor.py "<url>" --cookies-from-browser chrome` | reuse browser login/cookies |
| signed media URL that needs page headers | `processor.py "<media-url>" --referer "<page-url>"` | preserve access context |
| captions already visible on page | `web-access` to collect captions, then `processor.py --transcript-file ...` | skip fragile download |
| browser-exported audio or video file | `processor.py --media-file ...` | skip page acquisition entirely |
| short-video app / heavy JS player | `web-access` CDP mode first | interaction is the real source of truth |

## Platform Hints

- `bilibili.com/video/`: try direct first
- `youtube.com/watch` / `youtu.be`: cookies may be required
- `douyin.com` / `v.douyin.com`: expect browser interaction or caption extraction
- pages with login walls or modal overlays: use `web-access` instead of retrying `yt-dlp`
