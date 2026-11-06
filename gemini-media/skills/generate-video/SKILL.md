---
name: generate-video
description: >-
  This skill should be used when the user asks to "generate a video",
  "create a video", "make a video", "animate this", "text to video",
  "generate with Omni", "generate with Veo", "create a clip",
  "make a short film", "extend the video", "continue the video",
  "edit the video", "change the video", "interpolate between",
  "image to video", "animate this image", "video from image",
  or needs AI video generation, conversational video editing, video
  extension, or frame interpolation using the Gemini API.
version: 0.2.0
---

# Generate Video

Wrap Gemini Omni Flash (`gemini-omni-1.2-flash`) through the Gemini Interactions API to generate, edit, and extend videos with native audio via a Python script (stdlib only, no pip dependencies). Support text-to-video, image-to-video, first/last-frame interpolation, up to 6 reference images, conversational editing of the previous video, and extension up to 30 seconds. All output is saved to `./generated-videos/` and auto-opened on macOS.

Veo is gone from the Gemini API: the Veo 3.1 preview models shut down on 2026-10-22 and Omni Flash replaces them. If the user asks for Veo, say so and use Omni.

## Prerequisites

Before any generation, verify the environment:

1. Confirm `$GEMINI_API_KEY` is set. If missing, instruct the user:
   `export GEMINI_API_KEY='your-key-here'`
2. Ensure `python3` is available (Python 3.7+). The script uses only stdlib modules — no pip install needed.

## Text-to-Video Generation

When the user requests a new video from a text description:

### 1. Confirm the Prompt

Restate the user's request as a clear generation prompt. If the request is vague, ask for clarification before proceeding. Omni prompts work best when they describe:
- **Scene and subject action** (what happens over time; use "After 3 seconds, ..." or `[0-5s] ...` timecodes for timing)
- **Camera** (tracking, aerial, handheld) — and say "single continuous shot, no scene cuts" if one shot is wanted, because Omni cuts between shots by default
- **Mood/lighting** (golden hour, neon, foggy)
- **Audio** (dialogue, music, sound effects) — Omni always generates audio; say "No dialogue" or "no music" to suppress it
- **Exclusions** as plain sentences ("No text overlays") — there is no negative-prompt parameter

See `references/advanced-features.md` for the full prompt guide.

### 2. Choose Settings

Use API defaults unless the user explicitly requests specific settings. Only pass flags when the user asks for them.

If the user asks about available options:
- **Model:** `gemini-omni-1.2-flash` (default and only current model; `gemini-omni-1.1-flash` routes to it from 2026-12-03)
- **Aspect ratios:** 16:9 (default), 9:16
- **Resolutions:** 360p, 720p (default), 1080p, 4k (1080p and 4k are upscaled and take longer)
- **Duration:** any whole second from 3 to 15 (default 10); 3-10 for interpolation and per-turn extension
- **Audio:** always generated; steer it in the prompt

### 3. Invoke the Script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-video/scripts/generate_video.py" generate \
  --prompt "the final prompt" \
  --output-dir "./generated-videos"
```

Add optional flags only when the user explicitly requests them:
- `--aspect-ratio "9:16"` — portrait/vertical video
- `--resolution "1080p"` — higher resolution (or `360p` for quick drafts)
- `--duration 5` — length in seconds (3-15)

**Important:** Generation runs in the background on Google's side; the script polls until it finishes. A short clip takes 15-40 seconds; long, high-resolution clips take minutes. Warn the user that this is slower than image generation. Run the command with a Bash timeout of at least 600000 ms.

### 4. Report the Result

The script outputs JSON to stdout. Parse it and report:
- The saved video path
- The generation time
- Note that the video has been opened for preview
- Ask if the user wants to edit or extend the video, generate a new one, or adjust settings

## Image-to-Video (Animation)

When the user provides an image to animate:

1. Validate the image file exists (`test -f`).
2. Describe the desired **motion** — camera movement, subject motion, environmental effects — not the image content. Say how the image should be used ("use the drawing only as a guide for movement").

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-video/scripts/generate_video.py" generate \
  --prompt "Bring this photo to life: the camera slowly pulls back as the leaves begin to sway" \
  --image "/path/to/image.png" \
  --output-dir "./generated-videos"
```

## Frame Interpolation

When the user provides two images and wants a transition between them, pass both with `--image` (first frame first) and describe the transition. Duration must be 3-10 seconds.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-video/scripts/generate_video.py" generate \
  --prompt "A smooth cinematic transition from the first image to the second" \
  --image "/path/to/first-frame.png" \
  --image "/path/to/last-frame.png" \
  --output-dir "./generated-videos"
```

## Reference Images

When the user provides images of characters, objects or styles to keep consistent, pass each with `--image` (up to 6; up to 3 per character for up to 2 characters) and say in the prompt what each one is for.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-video/scripts/generate_video.py" generate \
  --prompt "The woman from the first image walks through the garden from the second image, wearing the red dress" \
  --image "/path/to/woman.png" \
  --image "/path/to/garden.png" \
  --output-dir "./generated-videos"
```

The model infers from the prompt whether images are frames or references. Only if it picks the wrong mode, retry with `--task image_to_video` or `--task reference_to_video`. Never put tags like `<FIRST_FRAME>` or `<IMAGE_REF_0>` in the prompt; they are deprecated.

## Editing and Extending the Last Video

Every successful run records its interaction ID. `--continue` sends the next prompt as a follow-up turn on that video, so there is no re-upload.

- **Edit** — keep the prompt short and add "Keep everything else the same." Example: "Make the phone invisible. Keep everything else the same." The output is the edited video.
- **Extend** — say "Extend this video: ..." or "The scene continues: ...". Each turn adds 3-10 seconds (`--duration`, default 10), up to 30 seconds in total. The model sees only the last 10 seconds, so re-mention anything that appeared earlier. The output is the whole, longer video.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-video/scripts/generate_video.py" generate \
  --continue \
  --prompt "Extend this video: the camera pans right, revealing a waterfall" \
  --duration 5 \
  --output-dir "./generated-videos"
```

To continue from an older video instead of the last one, pass `--previous-interaction ID` with the `interaction_id` from that run's JSON. Check what `--continue` will use with `generate_video.py session status`; forget it with `session reset`. Interactions are kept on Google's side for 55 days on the paid tier and 1 day on the free tier.

Reference images (`--image`) can be added on edit and extension turns, e.g. to bring a new character into the scene.

### Editing or Extending an Existing File

For a video file not generated in this session, pass it with `--video` (up to 15 seconds and 20 MB) plus an edit or extension prompt:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-video/scripts/generate_video.py" generate \
  --video "/path/to/clip.mp4" \
  --prompt "Make this video anime. Keep everything else the same." \
  --output-dir "./generated-videos"
```

**Regional limit:** Google does not allow editing or extending *uploaded* videos for users in the EEA, Switzerland and the UK. There, `--video` edits fail; videos generated by Omni can still be edited and extended with `--continue`.

## Background Submission

To submit without waiting:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-video/scripts/generate_video.py" generate \
  --prompt "the prompt" \
  --no-wait \
  --output-dir "./generated-videos"
```

This returns an `interaction_id`. Check on it or wait for it later (without `--interaction`, the last submission is used):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/generate-video/scripts/generate_video.py" poll \
  --interaction "v1_..." \
  --wait \
  --output-dir "./generated-videos"
```

## Error Handling

| Exit Code | Meaning | Action |
|---|---|---|
| 0 | Success | Report video path |
| 10 | Missing `$GEMINI_API_KEY` | Tell user what to set |
| 11 | Invalid input (bad path, unsupported format, out-of-range setting, nothing to continue) | Report the specific validation error |
| 20 | HTTP 400/404 — content policy, bad request, unknown interaction, regional restriction | Show API error message; suggest rephrasing or a different setting |
| 21 | HTTP 401/403 — auth failure | "API key is invalid or expired" |
| 22 | HTTP 429 — rate limited | Wait 10 seconds, retry once automatically. If still failing, tell user to wait. |
| 23 | HTTP 500+ or network error | Retry once automatically. If still failing, report. |
| 24 | Poll timeout | Report the interaction ID so the user can check later with `poll` |
| 30 | Interaction failed or returned no video | Show what the model said; suggest rephrasing |

On exit codes 22 and 23, retry the same command once before reporting failure.

## Script Reference

### `generate_video.py generate`

Flags:
- `--prompt` (required) — generation, editing or extension prompt
- `--model` — model ID (default: `gemini-omni-1.2-flash`)
- `--aspect-ratio` — `16:9` or `9:16` (API default 16:9)
- `--resolution` — `360p`, `720p`, `1080p`, `4k` (API default 720p)
- `--duration N` — seconds, 3-15 (API default 10)
- `--image PATH` — first frame, last frame or reference image (repeatable, max 6)
- `--video PATH` — local video to edit or extend (max 20 MB; not in EEA/CH/UK)
- `--continue` — follow up on the last generated video
- `--previous-interaction ID` — follow up on a specific earlier interaction
- `--task` — fallback mode hint: `text_to_video`, `image_to_video`, `reference_to_video`, `edit`, `extend`
- `--no-wait` — submit and return immediately
- `--poll-interval N` — seconds between polls (default: 10)
- `--timeout N` — max seconds to wait (default: 900)
- `--no-open` — do not open the saved video
- `--output-dir DIR` — output directory (default: `./generated-videos`)

### `generate_video.py poll`

Flags:
- `--interaction ID` — interaction to check (default: the last submission)
- `--wait` — wait for completion and download the video
- `--poll-interval`, `--timeout`, `--no-open`, `--output-dir` — as above

### `generate_video.py session`

Subcommands: `status` (show the interaction `--continue` will use), `reset` (forget it).

## Additional Resources

- **`references/api-reference.md`** — Interactions API request/response schema for Omni, polling, limits, error format.
- **`references/advanced-features.md`** — Prompt guide, editing and extension rules, reference media limits, regional restrictions, migration from Veo.
