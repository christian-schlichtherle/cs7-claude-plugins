---
name: generate-image
description: >-
  This skill should be used when the user asks to "generate an image",
  "create an image", "make a picture", "draw something", "edit an image",
  "modify this image", "change the background", "text to image",
  "generate with Gemini", "create a visual", "refine the image",
  "continue editing", "make it more", "add something to this image",
  "make a thumbnail for this video", "poster from this video",
  or needs AI image generation, image editing, multi-turn image
  refinement, or video-to-image generation using the Gemini API
  (Nano Banana).
version: 0.2.0
---

# Generate Image

Wrap the Gemini image generation REST API to produce, edit, and iteratively refine images via a Python script (stdlib only, no pip dependencies). Support text-to-image generation, image editing with reference images, video-to-image, multi-turn conversational editing, Google Search grounding, and thinking-level selection. All output is saved to `./generated-images/` and auto-opened on macOS. Images come back as JPEG from the Gemini 3 models (PNG from the legacy 2.5 model); the format cannot be requested.

## Prerequisites

Before any generation, verify the environment:

1. Confirm `$GEMINI_API_KEY` is set. If missing, instruct the user:
   `export GEMINI_API_KEY='your-key-here'`
2. Ensure `python3` is available (Python 3.7+). The script uses only stdlib modules — no pip install needed.

## New Image Generation

When the user requests a new image (no existing session or explicitly new subject):

### 1. Confirm the Prompt

Restate the user's request as a clear generation prompt. If the request is vague, ask for clarification before proceeding.

### 2. Choose Settings

Use API defaults unless the user explicitly requests specific settings. Only pass `--aspect-ratio` and `--resolution` flags when the user asks for them. When omitted, the API applies its own per-model defaults (typically 1:1 aspect ratio and 1K resolution).

If the user asks about available options:
- **Models:** Nano Banana 2.1 (default), Nano Banana 2 Lite, Nano Banana Pro, Nano Banana 2 (deprecated), Nano Banana (legacy 2.5)
- **Aspect ratios:** 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9 on all models; panoramic 1:4, 4:1, 1:8, 8:1 on NB 2.1, NB 2 Lite and NB 2
- **Resolutions:** 1K (default) on all; 2K and 4K on NB 2.1, Pro and NB 2; 512 on NB 2 only
- **Thinking:** `minimal`, `medium` (NB 2.1 only), `high`; `none` keeps the model's default
- **Determinism:** Use `--seed` and/or low `--temperature` for reproducible results

Map model choices:
- Nano Banana 2.1 / "default" → `gemini-nano-banana-2.1`
- Nano Banana 2 Lite / "fast" / "cheap" → `gemini-3.1-flash-lite-image`
- Nano Banana Pro / "Pro" → `gemini-3-pro-image`
- Nano Banana 2 / "Flash 3.1" → `gemini-3.1-flash-image` (deprecated; needed only for 512 output)
- Nano Banana / "Flash 2.5" → `gemini-2.5-flash-image` (legacy, existing API users only)

If the user asks for a setting the chosen model lacks (e.g. 4K on Lite, a panoramic ratio on Pro, 512 on anything but NB 2), say so and offer the nearest model that has it instead of sending a request that will fail.

### 3. Evaluate Thinking Level

Assess prompt complexity using the rubric in `references/advanced-features.md`. Count signal categories (multiple subjects, spatial words, text rendering, photo-realism, named styles, technical rendering, complex composition). Map the score:

- 0-3 signals → `--thinking-level none` (the model's own default: `medium` on NB 2.1, `minimal` on the others)
- 4+ signals → `--thinking-level high`
- User asks for speed over quality → `--thinking-level minimal`

**Note:** `medium` exists only on NB 2.1. For Flash 2.5, always use `--thinking-level none`. Thinking and `--resolution` combine freely; set both when the user wants both.

### 4. Decide on Grounding

Enable `--grounding` when the prompt references real-world information: current events, real people, specific brands, named locations, or factual content. Otherwise omit. Grounding is not available on NB 2 Lite or Flash 2.5; Image Search (part of `--grounding`) works only on NB 2.1 and NB 2.

### 5. Invoke the Script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" generate \
  --prompt "the final prompt" \
  --thinking-level none \
  --output-dir "./generated-images"
```

Add `--model` only when the user picked a non-default model. Add `--aspect-ratio "RATIO"` and/or `--resolution "RES"` only if the user explicitly requested them. Add `--grounding` if grounding was decided.

### 6. Report the Result

The script outputs JSON to stdout. Parse it and report:
- The saved image path
- The model's text response (if any)
- Note that the image has been opened for preview
- Ask if the user wants to edit further or generate something new

## Image Editing with Reference Images

When the user provides file paths to existing images for editing or as reference:

1. Validate each file exists (`test -f`).
2. Choose settings — use API defaults unless the user specifies otherwise.
3. Invoke with `--input-image` for each file (up to 14 on NB 2.1, NB 2 and Pro; NB 2.1 keeps up to 4 characters and 10 objects faithful):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" generate \
  --prompt "editing instruction" \
  --input-image "/path/to/image1.jpg" \
  --input-image "/path/to/image2.png" \
  --output-dir "./generated-images"
```

The script handles base64 encoding internally.

## Video-to-Image

When the user wants an image derived from a video (thumbnail, poster, infographic, artwork inspired by a scene), pass the video with `--input-video`. It accepts a public YouTube URL or a local file up to 20 MB (mp4, mov, webm, mpeg, avi). Supported on NB 2.1 (default), NB 2 Lite and NB 2 only.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" generate \
  --prompt "A cinematic poster capturing the key themes of this video" \
  --input-video "https://www.youtube.com/watch?v=..." \
  --output-dir "./generated-images"
```

## Multi-Turn Editing

For iterative refinement of a previously generated image:

### Check Session Status

Before each generation, check for an active session:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" session status
```

The output is JSON with `exists`, `turn_count`, `last_prompt`, and `updated_at`.

### Continue or Reset

- If a session exists and the user's intent is clearly to edit/refine (words like "change", "edit", "modify", "make it more", "add", "remove"), **continue the session**.
- If the user requests something completely new or says "start fresh", **reset the session**:
  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" session reset
  ```
- If the session is stale (>30 minutes since `updated_at`), ask: "Continue editing the previous image or start a new one?"

### First Turn (Create Session)

On the first generation that should start a session:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" session \
  create --model "gemini-nano-banana-2.1"
```

Use the model the user chose. Add `--aspect-ratio` and `--resolution` only if the user explicitly requested them.

Then invoke `generate_image.py generate` with the `--session-file`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" generate \
  --prompt "initial prompt" \
  --session-file "~/.cache/claude-generate-image/.session.json" \
  --output-dir "./generated-images"
```

### Subsequent Turns

Do NOT re-ask settings — the script inherits model, aspect ratio and resolution from the session. Invoke:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" generate \
  --prompt "refinement instruction" \
  --session-file "~/.cache/claude-generate-image/.session.json" \
  --output-dir "./generated-images"
```

New input images can be added with `--input-image` on any turn.

## Model Selection

| Model | Status | Best For | Limitations |
|---|---|---|---|
| `gemini-nano-banana-2.1` (default) | GA | Almost everything: quality, text, multi-turn, panoramas, video-to-image | No 512 |
| `gemini-3.1-flash-lite-image` | GA | Drafts, bulk, fastest and cheapest | 1K only, no grounding, weak multi-reference |
| `gemini-3-pro-image` | GA | Complex scenes, brand work, dense exact text | No panoramic ratios, no Image Search, no video input |
| `gemini-3.1-flash-image` | Deprecated | 512 output | Superseded by NB 2.1 |
| `gemini-2.5-flash-image` | Legacy | Existing integrations only | 1K only, no thinking, no panoramic ratios |

Always use NB 2.1 by default. Only switch models when the user explicitly requests a specific model (e.g. "use Pro", "use Lite") or a setting only another model has (512 output). Do not infer model choice from prompt complexity or quality keywords. Note: switching models mid-session requires a session reset.

## Error Handling

| Exit Code | Meaning | Action |
|---|---|---|
| 0 | Success | Report image path and text |
| 10 | Missing `$GEMINI_API_KEY` or dependency | Tell user what to set/install |
| 11 | Invalid input (bad path, unsupported format, >14 images, video >20 MB) | Report the specific validation error |
| 20 | HTTP 400 — content policy, bad request, or a setting the model does not support | Show API error message; if it names an unsupported size, ratio or thinking level, offer a model that has it; otherwise suggest rephrasing |
| 21 | HTTP 401/403 — auth failure | "API key is invalid or expired" |
| 22 | HTTP 429 — rate limited | Wait 10 seconds, retry once automatically. If still failing, tell user to wait. |
| 23 | HTTP 500+ — server error | Retry once automatically. If still failing, report. |
| 30 | No image in response | "Model didn't return an image — try rephrasing the prompt" |

On exit codes 22 and 23, retry the same command once before reporting failure.

## Script Reference

### `generate_image.py generate`

Core API caller. Flags:
- `--prompt` (required) — generation or editing prompt
- `--model` — model ID (default: the session's model, else `gemini-nano-banana-2.1`)
- `--aspect-ratio` — aspect ratio (optional; session or API default when omitted)
- `--resolution` — image size: `512`, `1K`, `2K`, `4K` (optional; session or API default when omitted; `512px` is accepted as `512`)
- `--thinking-level` — `none` (model default), `minimal`, `medium`, `high` (default: `none`)
- `--grounding` — enable Google Search + Image Search grounding
- `--seed N` — seed for deterministic generation
- `--temperature F` — creativity control (0.0-2.0)
- `--input-image PATH` — input image file (repeatable, max 14)
- `--input-video PATH|URL` — video for video-to-image: YouTube URL or local file up to 20 MB (repeatable)
- `--session-file PATH` — session file for multi-turn
- `--no-open` — do not open the saved image
- `--output-dir DIR` — output directory (default: `./generated-images`)

### `generate_image.py session`

Session lifecycle. Subcommands: `create`, `append`, `read`, `reset`, `status`, `set-last-output`. See `references/advanced-features.md` for session schema.

## Additional Resources

- **`references/api-reference.md`** — Full Gemini REST API schema: endpoint, models, request/response format, aspect ratios and resolutions per model, error codes, MIME types.
- **`references/advanced-features.md`** — Thinking level rubric, thought signature handling, session schema, grounding attribution, video-to-image, model-specific behaviors, edge cases.
