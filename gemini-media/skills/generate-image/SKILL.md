---
name: generate-image
description: >-
  This skill should be used when the user asks to "generate an image",
  "create an image", "make a picture", "draw something", "edit an image",
  "modify this image", "change the background", "text to image",
  "generate with Gemini", "create a visual", "refine the image",
  "continue editing", "make it more", "add something to this image",
  or needs AI image generation, image editing, or multi-turn image
  refinement using the Gemini API.
version: 0.1.0
---

# Generate Image

Wrap the Gemini image generation REST API to produce, edit, and iteratively refine images via a Python script (stdlib only, no pip dependencies). Support text-to-image generation, image editing with reference images, multi-turn conversational editing, Google Search grounding, and automatic thinking mode. All output is saved to `./generated-images/` and auto-opened on macOS.

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
- **Aspect ratios:** 1:1, 1:4, 1:8, 2:3, 3:2, 3:4, 4:1, 4:3, 4:5, 5:4, 8:1, 9:16, 16:9, 21:9
- **Resolutions:** 512px, 1K, 2K, 4K
- **Models:** Flash 3.1 (default), Pro 3, Flash 2.5
- **Output format:** PNG (default) or JPEG with compression quality (1-100)
- **People:** `ALLOW_ALL`, `ALLOW_ADULT` (default), `ALLOW_NONE`
- **Determinism:** Use `--seed` and/or low `--temperature` for reproducible results

Map model choices:
- Flash 3.1 → `gemini-3.1-flash-image-preview`
- Pro 3 → `gemini-3-pro-image-preview`
- Flash 2.5 → `gemini-2.5-flash-image`

### 3. Evaluate Thinking Level

Assess prompt complexity using the rubric in `references/advanced-features.md`. Count signal categories (multiple subjects, spatial words, text rendering, photo-realism, named styles, technical rendering, complex composition). Map the score:

- 0-1 signals → `--thinking-level none`
- 2-3 signals → `--thinking-level minimal`
- 4+ signals → `--thinking-level high`

**Note:** Thinking is only supported on Flash 3.1 and Pro 3. For Flash 2.5, always use `--thinking-level none`.

**CRITICAL — Thinking vs. Resolution incompatibility:** When `thinkingConfig` is present in the API request, the Gemini API **silently ignores** the `imageSize` parameter, producing images at a lower default resolution (~1376x768 for 16:9). If the user requests a specific resolution (2K, 4K, or any explicit size like "Full HD"), you **MUST** use `--thinking-level none` to ensure the resolution is respected. The `generate_image.py` script enforces this automatically — if both `--resolution` and a non-none `--thinking-level` are provided, it forces thinking to `none` and logs a warning.

### 4. Decide on Grounding

Enable `--grounding` when the prompt references real-world information: current events, real people, specific brands, named locations, or factual content. Otherwise omit.

### 5. Invoke the Script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" generate \
  --prompt "the final prompt" \
  --model "gemini-3.1-flash-image-preview" \
  --thinking-level none \
  --output-dir "./generated-images"
```

Add `--aspect-ratio "RATIO"` and/or `--resolution "RES"` only if the user explicitly requested them. Add `--grounding` if grounding was decided.

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
3. Invoke with `--input-image` for each file (up to 10 for Flash 3.1, 6 for Pro 3):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" generate \
  --prompt "editing instruction" \
  --input-image "/path/to/image1.jpg" \
  --input-image "/path/to/image2.png" \
  --model "gemini-3.1-flash-image-preview" \
  --output-dir "./generated-images"
```

The script handles base64 encoding internally.

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
  create --model "gemini-3.1-flash-image-preview"
```

Add `--aspect-ratio` and `--resolution` only if the user explicitly requested them.

Then invoke `generate_image.py generate` with the `--session-file`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-image/scripts/generate_image.py" generate \
  --prompt "initial prompt" \
  --session-file "~/.cache/claude-generate-image/.session.json" \
  --output-dir "./generated-images"
```

### Subsequent Turns

Do NOT re-ask settings — inherit from the session. Invoke:

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
| `gemini-3.1-flash-image-preview` (default) | Preview | Fast iteration, all features, Image Search grounding | Preview only |
| `gemini-3-pro-image-preview` | Preview | Final deliverables, complex scenes, highest quality | No Image Search, no extreme ratios, no 512px |
| `gemini-2.5-flash-image` | GA | Stable, production-ready generation | No thinking, no extreme ratios, no 512px |

Always use Flash 3.1 by default. Only switch models when the user explicitly requests a specific model (e.g., "use Pro 3", "use Flash 2.5"). Do not infer model choice from prompt complexity or quality keywords. Note: switching models mid-session requires a session reset.

**Important:** `responseModalities` must always be `["TEXT", "IMAGE"]`. Image-only output `["IMAGE"]` is not supported.

## Error Handling

| Exit Code | Meaning | Action |
|---|---|---|
| 0 | Success | Report image path and text |
| 10 | Missing `$GEMINI_API_KEY` or dependency | Tell user what to set/install |
| 11 | Invalid input (bad path, unsupported format, >14 images) | Report the specific validation error |
| 20 | HTTP 400 — content policy or bad request | Show API error message, suggest rephrasing |
| 21 | HTTP 401/403 — auth failure | "API key is invalid or expired" |
| 22 | HTTP 429 — rate limited | Wait 10 seconds, retry once automatically. If still failing, tell user to wait. |
| 23 | HTTP 500+ — server error | Retry once automatically. If still failing, report. |
| 30 | No image in response | "Model didn't return an image — try rephrasing the prompt" |

On exit codes 22 and 23, retry the same command once before reporting failure.

## Script Reference

### `generate_image.py generate`

Core API caller. Flags:
- `--prompt` (required) — generation or editing prompt
- `--model` — model ID (default: `gemini-3.1-flash-image-preview`)
- `--aspect-ratio` — aspect ratio (optional; API default when omitted)
- `--resolution` — image size: `512px`, `1K`, `2K`, `4K` (optional; API default when omitted)
- `--thinking-level` — `none`, `minimal`, `high` (default: `none`). Not supported on Flash 2.5.
- `--grounding` — enable Google Search + Image Search grounding
- `--person-generation` — `ALLOW_ALL`, `ALLOW_ADULT`, or `ALLOW_NONE`
- `--output-mime-type` — `image/png` (default) or `image/jpeg`
- `--compression-quality N` — JPEG quality (1-100)
- `--seed N` — seed for deterministic generation
- `--temperature F` — creativity control (0.0-2.0)
- `--input-image PATH` — input image file (repeatable, max 14)
- `--session-file PATH` — session file for multi-turn
- `--output-dir DIR` — output directory (default: `./generated-images`)

### `generate_image.py session`

Session lifecycle. Subcommands: `create`, `append`, `read`, `reset`, `status`, `set-last-output`. See `references/advanced-features.md` for session schema.

## Additional Resources

- **`references/api-reference.md`** — Full Gemini REST API schema: endpoint, request/response format, all aspect ratios and resolutions, error codes, MIME types.
- **`references/advanced-features.md`** — Thinking auto-detection rubric, thought signature handling, session schema, grounding attribution, model-specific behaviors, edge cases.
