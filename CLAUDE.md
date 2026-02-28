# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Claude plugin repository providing AI-powered image and video generation using Google's Gemini API. Published as a plugin marketplace with one plugin (`gemini-media`) containing two skills: `generate-image` and `generate-video`.

## Architecture

```
.claude-plugin/marketplace.json    # Marketplace manifest listing plugins
gemini-media/
  .claude-plugin/plugin.json       # Plugin manifest (name, version, keywords)
  skills/
    generate-image/
      SKILL.md                     # Skill prompt (loaded by Claude when skill is invoked)
      scripts/generate_image.py    # Standalone Python script (stdlib only)
      references/                  # API docs and advanced feature guides
    generate-video/
      SKILL.md                     # Skill prompt
      scripts/generate_video.py    # Standalone Python script (stdlib only)
      references/                  # API docs and advanced feature guides
```

Each skill follows the pattern: `SKILL.md` defines how Claude should use the skill, `scripts/` contains the executable, and `references/` provides API documentation the SKILL.md can reference.

## Running the Scripts

Both Python scripts use **only stdlib** (no pip install needed). They require Python 3.7+ and a `GEMINI_API_KEY` environment variable (or `.env` file in the repo root).

```bash
# Image generation
python3 gemini-media/skills/generate-image/scripts/generate_image.py generate --prompt "..."

# Video generation
python3 gemini-media/skills/generate-video/scripts/generate_video.py generate --prompt "..."

# Check video operation status
python3 gemini-media/skills/generate-video/scripts/generate_video.py poll --operation "..."
```

Output goes to `./generated-images/` and `./generated-videos/` (both gitignored).

## Key Design Decisions

- **No external dependencies**: Scripts use only Python stdlib (`urllib`, `json`, `base64`, `argparse`, `pathlib`) for maximum portability.
- **Direct REST API calls**: No Gemini SDK — scripts call the REST API directly for fine-grained control.
- **Exit codes are semantic**: Both scripts use specific exit codes (10=missing key, 11=validation, 20=API 400, 21=auth, 22=rate limit, 23=server error, 24=timeout, 30=no output) so SKILL.md can instruct Claude to retry on codes 22/23.
- **Image sessions**: The image script supports multi-turn editing via JSON session files (`~/.cache/claude-generate-image/.session.json`) that preserve conversation history and thought signatures.
- **Async video generation**: Video generation uses long-running operations with client-side polling; `--no-wait` submits without blocking.
