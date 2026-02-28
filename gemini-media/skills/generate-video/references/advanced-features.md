# Advanced Features — generate-video Skill

## Available Models

| Model ID | Speed | Quality | Best For |
|---|---|---|---|
| `veo-3.1-generate-preview` | Slower | Highest | Final deliverables, complex scenes, reference images |
| `veo-3.1-fast-generate-preview` | Fast | High | Iteration, drafts, programmatic generation (default) |
| `veo-3.0-generate-preview` | Slower | High | Text-to-video and image-to-video without advanced features |
| `veo-3.0-fast-generate-001` | Fastest | Good | Production workloads, high-volume generation |

**Recommendation:** Use `veo-3.1-fast-generate-preview` (default) for iteration. Switch to `veo-3.1-generate-preview` for final quality. Use Veo 3.0 variants only if you don't need reference images, frame interpolation, or video extension.

## Generation Modes

### Text-to-Video
The simplest mode. Provide a text prompt describing the desired video. Veo 3.1 generates both visual content and synchronized audio.

**Audio cues in prompts:** Include audio descriptions directly in the prompt for native audio synthesis:
- "A thunderstorm over a city skyline with rain sounds and distant thunder"
- "Two people having a conversation in a cafe with ambient background noise"
- "A guitar being played in a sunlit room"

### Image-to-Video
Provide a starting frame image via `--image`. The model animates the scene from that frame. Useful for:
- Animating still photographs
- Creating motion from concept art or mockups
- Bringing product shots to life

The prompt should describe the desired motion, not the image content (the model can see the image).

### Frame Interpolation
Provide both `--image` (first frame) and `--last-frame` (final frame). The model generates a smooth transition between the two images. Use cases:
- Morphing between two states
- Creating transitions for presentations
- Animating before/after comparisons

### Video Extension
Use the `extend` command with `--video` pointing to a previously generated MP4. Extensions:
- Add 7 seconds at a time
- Up to 20 extensions per video chain
- Locked to 720p resolution
- The prompt describes what happens next in the video
- Each extension resets the 2-day retention timer

## Prompt Engineering for Video

### Effective Prompts
Video prompts benefit from describing:
1. **Camera movement** — "slow dolly shot", "aerial tracking shot", "handheld closeup"
2. **Subject action** — what happens over time, not just a static scene
3. **Lighting/mood** — "golden hour", "neon-lit", "foggy morning"
4. **Audio** — sound effects, music, dialogue, ambient noise
5. **Pacing** — "slowly", "sudden", "gradual transition"

### Negative Prompts
Use `--negative-prompt` to exclude unwanted elements:
- "blurry, shaky, low quality, text overlays, watermark"
- "cartoon, animation" (when wanting photorealism)
- "static, no motion" (when wanting dynamic footage)

### Duration Selection

| Duration | Best For |
|---|---|
| 4 seconds | Quick clips, GIFs, social media snippets |
| 6 seconds | Short scenes, product reveals |
| 8 seconds | Full scenes, dialogue, complex motion (required for 1080p/4k) |

## Resolution Guide

| Resolution | Pixel Size | Best For | Constraints |
|---|---|---|---|
| 720p | 1280x720 | Fast iteration, drafts, extensions | Default; fastest generation |
| 1080p | 1920x1080 | Final deliverables, social media | Duration must be 8s |
| 4k | 3840x2160 | Professional production, large displays | Duration must be 8s; slowest |

**Recommendation:** Start with 720p for iteration, then regenerate the final version at higher resolution.

## Reference Images

Up to 3 reference images can guide the generation. Each reference has a `referenceType`:

| Type | Use Case |
|---|---|
| `asset` | Objects, clothing, props — things that appear in the video |

Reference images work best when:
- The prompt explicitly mentions the referenced objects (e.g., "wearing the red dress from the reference")
- Images are clear, well-lit, and show the subject prominently
- You use 1-3 focused references rather than many vague ones

## Person Generation

| Value | Description | Regional Note |
|---|---|---|
| `allow_all` | Adults and children | May require project allowlist; restricted in EU/UK/CH/MENA |
| `allow_adult` | Adults only (default) | Required in EU/UK/CH/MENA for image-to-video |
| `dont_allow` | No people | Use when people are not desired |

Omit the parameter to use API defaults (`allow_adult`). Only set it when the user specifically needs people in the video.

## Audio Control

Use `--generate-audio` to explicitly enable native audio synthesis, or `--no-audio` to disable it. Veo 3+ models can generate synchronized dialogue, sound effects, ambient noise, and music.

When audio is enabled, include audio cues in the prompt for best results:
- "Two people chatting in a busy cafe with clinking glasses"
- "A thunderstorm with heavy rain and distant thunder"
- "Upbeat electronic music playing in the background"

**Note:** During video extension, audio from the last 1 second of the source video carries forward. If the source has no audio in its final second, the extension may also lack audio continuity.

## Deterministic Generation (Seed)

Use `--seed <number>` to request more deterministic output. Providing the same seed with the same parameters will produce similar (though not guaranteed identical) results. Useful for:
- Iterating on a prompt while keeping the visual style consistent
- Reproducing a specific result for comparison
- A/B testing with controlled variation

Seed values are unsigned 32-bit integers (0–4,294,967,295).

## Multiple Video Outputs

Use `--sample-count <1-4>` to request multiple video variations in a single API call. All videos use the same prompt and parameters but will differ in their creative interpretation. Useful for:
- Picking the best take from multiple options
- Exploring different visual interpretations of a prompt
- Generating content variations for A/B testing

When multiple videos are requested, all are downloaded and saved with numbered suffixes (e.g., `-1.mp4`, `-2.mp4`).

## Resize Mode (Image-to-Video)

Use `--resize-mode` to control how input images are resized when their aspect ratio doesn't match the output:

| Mode | Behavior |
|---|---|
| `pad` (default) | Adds black bars to preserve the full image |
| `crop` | Crops the image to fill the frame, may lose edges |

Only applies to image-to-video generation on Veo 3+ models.

## Compression Quality

Use `--compression-quality` to control the output video compression:

| Quality | Description |
|---|---|
| `optimized` (default) | Balanced quality and file size |
| `lossless` | Maximum quality, larger file size |

## Async Operation Workflow

Video generation is asynchronous — the API returns an operation immediately, and the video is generated in the background.

### Workflow

```
1. POST predictLongRunning → returns operation name
2. GET operation (poll every 10s) → "done": false
3. GET operation (poll every 10s) → "done": true, response.video.uri
4. GET video.uri → download MP4 bytes
```

### `--no-wait` Mode

Use `--no-wait` to submit and return immediately. The script prints the operation name. Check later with:

```bash
python3 generate_video.py poll --operation "models/veo-3.1-generate-preview/operations/..." --wait
```

This is useful for:
- Submitting multiple videos in parallel
- Long-running generations where you don't want to block
- CI/CD pipelines

### Timeout Handling

Default timeout is 600 seconds (10 minutes). If generation times out:
- The operation is still running server-side
- Use the `poll` command with the operation name to check later
- Videos are retained for 2 days once generated

## Error Handling Details

| Exit Code | Meaning | Action |
|---|---|---|
| 0 | Success | Report video path |
| 10 | Missing `$GEMINI_API_KEY` | Tell user what to set |
| 11 | Invalid input (bad path, unsupported format, constraint violation) | Report the specific validation error |
| 20 | HTTP 400 — content policy or bad request | Show API error, suggest rephrasing |
| 21 | HTTP 401/403 — auth failure | "API key is invalid or expired" |
| 22 | HTTP 429 — rate limited | Wait and retry |
| 23 | HTTP 500+ — server error | Retry once |
| 24 | Poll timeout | Report operation name for manual polling |
| 30 | No video in response | "Model didn't return a video — try rephrasing" |

## Video Extension Chain

Extensions create a chain of video segments. Best practices:

1. **Keep continuity:** Reference what happened in the previous segment in your prompt
2. **720p only:** Extensions are locked to 720p regardless of the original resolution
3. **Duration locked to 8s:** Each extension adds ~7 seconds
4. **20 extension limit:** Plan the narrative arc within this constraint
5. **Download each segment:** The extension produces a new video, not a concatenated one

To combine extended segments into one video, use an external tool like ffmpeg:
```bash
# Create file list
for f in segment1.mp4 segment2.mp4 segment3.mp4; do
  echo "file '$f'" >> list.txt
done
# Concatenate
ffmpeg -f concat -safe 0 -i list.txt -c copy combined.mp4
```

## SynthID Watermark

All Veo-generated videos include an invisible SynthID watermark for AI-generated content identification. This cannot be disabled. It does not affect visual quality.
