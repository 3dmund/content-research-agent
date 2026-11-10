---
name: setup-agent
description: First-time setup. Installs what the research agent needs and learns about the user's page. Use when the user runs setup or has just downloaded this repo.
disable-model-invocation: true
---

Set up this research agent for someone who may not be technical. Keep every message short, explain what you're doing in plain English, and do the technical work yourself.

## 1. Install

Check whether `uv` is available. If it isn't, install it with the official installer from https://docs.astral.sh/uv/getting-started/installation/ for this operating system, and make sure the current shell can find it.

Then run `uv sync` in this folder. It installs Python and every tool the agent needs inside this folder. Nothing else needs installing.

## 2. Learn about their page

Interview the user one question at a time:

1. What's your Instagram handle?
2. Who is your page for?
3. What are the 3 to 5 topics you post about?
4. Paste links to your 3 best posts. Why do you think each one worked?
5. Is there anything you'd never make?

Rewrite `me.md` with their answers, using the headings already in that file, and remove the line that says `NOT SET UP YET`.

## 3. Test it

Run the `/analyze` steps on the first link from their best posts. If something fails, fix it before continuing.

## 4. Finish

Tell them:

- It's ready. From now on, they type `/analyze` followed by any public reel link.
- Typing `/library` opens their library in the browser, where they can scrub each video and read its transcript, breakdown and ideas. Open it for them now using the `/library` steps.
- They can ask you questions about their library at any time, like "show me every hook about editing."
- If they'd like to send reels from their phone, they can run `/add-telegram`.
