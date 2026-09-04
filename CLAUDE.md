# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Claude plugin repository published as a marketplace with two plugins:

- `pdca` — two-phase PDCA development: two commands (`/pdca:plan`, `/pdca:execute`) and two skills (`plan`, `execute`) that split work into an interactive planning session and a fresh autonomous session driven by `/goal`, launched as a background process. Pure Markdown, no scripts.
- `gemini-media` — AI-powered image and video generation using Google's Gemini API, containing two skills: `generate-image` and `generate-video`.

## Running the Scripts

Both Python scripts use **only stdlib** (no pip install needed). They require Python 3.7+ and a `GEMINI_API_KEY` environment variable (or `.env` file in the repo root).

Output goes to `./generated-images/` and `./generated-videos/` (both gitignored).

## Key Design Decisions

- **No external dependencies**: Scripts use only Python stdlib (`urllib`, `json`, `base64`, `argparse`, `pathlib`) for maximum portability.
- **Direct REST API calls**: No Gemini SDK — scripts call the REST API directly for fine-grained control.
- **Exit codes are semantic**: Both scripts use specific exit codes (10=missing key, 11=validation, 20=API 400, 21=auth, 22=rate limit, 23=server error, 24=timeout, 30=no output) so SKILL.md can instruct Claude to retry on codes 22/23.
- **Image sessions**: The image script supports multi-turn editing via JSON session files (`~/.cache/claude-generate-image/.session.json`) that preserve conversation history and thought signatures.
- **Async video generation**: Video generation uses long-running operations with client-side polling; `--no-wait` submits without blocking.
