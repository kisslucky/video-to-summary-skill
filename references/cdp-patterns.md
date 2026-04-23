# CDP Patterns

Use browser interaction when the page itself is the bottleneck.

## Common CDP Goals

1. Open the page in a logged-in browser context
2. Expand hidden captions or transcript panels
3. Scroll to trigger lazy-loaded metadata
4. Extract title, captions, or media URLs from the DOM
5. Capture key frames only when audio or captions cannot be retrieved

## Recommended Pattern

1. Start `web-access`
2. Open the page in a fresh background tab
3. Inspect the DOM before clicking randomly
4. Expand transcript/caption UI if present
5. Extract text or media URL with `eval`
6. Pass the extracted asset back to `processor.py`

## When to Stop Using CDP

- once you already have transcript text
- once you already have a stable media file or signed media URL
- once the remaining work is local transcription and summarization
