# Advanced Features — generate-video Skill

## Migration from Veo

The skill used Veo until Google shut down the Veo models in the Gemini API (Veo 3.1 previews on 2026-10-22). Omni Flash replaces them with a different API and different controls:

| Veo (old) | Omni Flash (now) |
|---|---|
| `predictLongRunning` + operation polling | Interactions API with `background: true` + `GET /interactions/{id}` |
| Durations 4, 6, 8 s | Any whole second 3-15 s (default 10) |
| 720p / 1080p / 4k | 360p / 720p / 1080p / 4k |
| `--negative-prompt` | Write exclusions into the prompt ("No text overlays") |
| `--no-audio` | Audio always generated; prompt "No dialogue", "no music" |
| `--seed`, `--sample-count`, `--person-generation`, `--resize-mode`, `--compression-quality` | Not available |
| `--last-frame`, `--reference-image` | Pass every image with `--image`; the prompt says how to use each |
| `extend --video` (~7 s per hop, up to 20 hops) | `--continue` (3-10 s per turn, 30 s total) |
| — | Conversational editing of the last video with `--continue` |
| `poll --operation` | `poll --interaction` |

## Prompt Guide

### Single scene vs. shots

Omni builds a short narrative with several shots by default. For one shot, say so: "single continuous shot", "one unbroken scene", "no scene cuts".

```
Continuous, unbroken handheld shot of a fluffy tabby cat on a sunny windowsill, looking out into a leafy garden. Its tail twitches slowly. Sunbeams light dust motes. Sound design: gentle breeze, distant birdsong. No dialogue.
```

### Removing unwanted elements

There is no negative-prompt field. Add plain exclusions: "No dialogue", "No embellishments", "No extra sound effects", "No text on screen".

### Audio

Omni always generates a soundtrack. Describe what you want, especially music: "calm background music", "high-energy techno beat", "a tinny radio playing in the background". Use "No dialogue" or "No music" to suppress.

### Timing

Natural language works: "After 3 seconds, a woman enters", "At 5s the chorus starts", "Every 2 seconds cut to a new location". So does a timecode list:

```
[0-5s] A person walks down a quiet street
[5-10s] They stop and turn toward a glowing doorway
[10-15s] They run into the portal
```

In an extension prompt, 0 s is the start of the new part.

### Detail

Meta-instructions help: "Be extremely detailed in describing characters and environments; apply costume-design principles", "Include plenty of natural background detail".

### Text in video

Omni renders legible text. Spell out any text that will be visible, including incidental signage: `A street sign that says "Main St"`.

### Editing prompts

Short beats long. End with "Keep everything else the same."

| Avoid | Prefer |
|---|---|
| "Please remove the cell phone the person is holding and fill in the background so it looks like the hand is empty." | "Make the phone invisible. Keep everything else the same." |
| "Add a small black cat that runs in from the right, jumps onto his lap, and he strokes its head while looking down." | "Add a cat that jumps onto his lap; he pets it. Keep everything else the same." |

Other good edits: "Make this video anime", "Put a fashionable hat on this person", "Change the lighting to be more dramatic", `Change the text on the sign to say "Open"`.

### Language

English is fully supported; other languages may work but are not evaluated.

## Image Inputs

All images go in with `--image` (max 6). The prompt decides their role:

| Images | Prompt says | Mode |
|---|---|---|
| 1 | "bring this to life", "animate", "use as the first frame" | image-to-video |
| 2 | "transition from the first to the second" | first/last-frame interpolation (3-10 s) |
| 1-6 | "the character in the first image…", "wearing the dress from…" | reference-to-video (up to 3 images per character, up to 2 characters) |

If the model picks the wrong mode, retry with `--task image_to_video` or `--task reference_to_video`. Do not use `<FIRST_FRAME>`, `<LAST_FRAME>`, `<IMAGE_REF_0>` or `<VIDEO_REF_0>` tags; they are deprecated.

For image-to-video, use high-resolution images and specific motion: camera movement, subject motion, environmental effects. "Make it move" gives weak results.

## Editing and Extension

### Multi-turn (`--continue` / `--previous-interaction`)

The script stores the last interaction ID in `~/.cache/claude-generate-video/.session.json` (override the directory with `CLAUDE_VIDEO_SESSION_DIR`). `--continue` sends the next prompt with `previous_interaction_id`, so the model works on its own last video without a re-upload. The previous interaction must be `completed`.

- **Edit:** videos up to 15 s. Voice editing is not supported.
- **Extend:** 3-10 s per turn (`--duration`, default 10), 30 s total. The model uses the last 10 s as context and edits a few final frames for a seamless join. Anything that appeared earlier must be mentioned again or supplied as a reference image. Only appending is possible, never prepending or inserting. Spoken dialogue in extensions works in multi-turn mode.
- Reference images can be added on edit and extension turns ("the person in the reference image enters the scene").

### Uploaded videos (`--video`)

A local video (≤15 s, ≤20 MB, mp4/mov/webm) can be edited or extended. Restrictions:
- **Not available in the EEA, Switzerland and the UK** — uploaded-video editing and extension are blocked there. Generated videos can still be edited and extended via `--continue`.
- An uploaded video in which someone talks cannot be extended with more dialogue.
- Reference videos (likeness only, audio ignored, ≤3 s each) work only for new generations: 1 for 11-15 s outputs, up to 3 for 3-10 s outputs. The script sends one `--video`; combining several videos degrades results.

## Session Schema (`.session.json`)

```json
{
  "interaction_id": "v1_...",
  "model": "gemini-omni-1.2-flash",
  "last_output": "/abs/path/generated-videos/a-red-kite-in-a-blue-sky-1793999142.mp4",
  "last_prompt": "A red kite in a blue sky",
  "pending_interaction_id": null,
  "pending_prompt": null,
  "updated_at": "2026-11-06T21:05:42Z"
}
```

`pending_*` is set on submission and cleared when a video is saved; `poll` without `--interaction` uses it. `interaction_id` is what `--continue` chains onto.

## Retention

Interactions are stored for 55 days on the paid tier (configurable to 7, 14 or 28 in AI Studio) and 1 day on the free tier. After that, `--continue` and `poll` on them fail with HTTP 400/404.

## Other Limits

- Images of minors cannot be uploaded or edited in the EEA, CH and UK; images of certain recognizable people are refused everywhere.
- Audio input is not supported.
- All outputs carry an invisible SynthID watermark.
- Safety filters apply to prompts and outputs and vary by region.
