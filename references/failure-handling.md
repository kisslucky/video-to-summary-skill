# Failure Handling

## Acquisition Failures

| Symptom | Likely cause | Next move |
| --- | --- | --- |
| `yt-dlp` says sign in or bot check | login/cookie restriction | retry with browser cookies or CDP |
| `yt-dlp` returns no media | JS-heavy or protected page | move to `web-access` |
| signed URL fails | missing referer or cookies | rerun with `--referer` and cookie context |

## Browser / CDP Failures

| Symptom | Likely cause | Next move |
| --- | --- | --- |
| proxy not connected | Chrome/CDP state broken | use `browser-troubleshooting` |
| page never loads | network or anti-bot wall | switch network path or capture only visible information |
| DOM changes break clicks | unstable selector path | inspect the page again instead of blind retries |

## Output Quality Failures

| Symptom | Likely cause | Next move |
| --- | --- | --- |
| transcript is weak | bad audio or wrong input asset | fix acquisition first |
| summary draft is shallow | script only produced a draft | rewrite the final summary in-agent |
| no audio available | captions-only or frame-only source | disclose limitation and use captions / frame notes |
