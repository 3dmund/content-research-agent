---
name: library
description: Open the user's reel library in their browser. Use when the user asks to see, open or browse their library.
---

Run this in the background so the conversation stays free:

    uv run tools/library.py

Tell the user their library is open at http://localhost:4173. It runs while this Claude Code session is open, and new reels appear when they come back to the tab.
