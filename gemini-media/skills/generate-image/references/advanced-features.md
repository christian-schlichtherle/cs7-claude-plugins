# Advanced Features — generate-image Skill

## Thinking Level Selection

The Gemini 3 image models always think before they draw; the thinking level only tunes how much. More thinking helps complex prompts but is slower, and thinking tokens are billed.

**Model support:**

| Model | Levels | Default (when `thinkingConfig` is omitted) |
|---|---|---|
| `gemini-nano-banana-2.1` | `minimal`, `medium`, `high` | `medium` |
| `gemini-3.1-flash-lite-image` | `minimal`, `high` | `minimal` |
| `gemini-3-pro-image` | `minimal`, `high` | model-chosen |
| `gemini-3.1-flash-image` | `minimal`, `high` | `minimal` |
| `gemini-2.5-flash-image` | not supported — always pass `none` | — |

An unsupported level fails with HTTP 400 ("Thinking level MEDIUM is not supported for this model").

The `--thinking-level` flag on `generate_image.py` maps: `none` → `thinkingConfig` omitted (model default), otherwise the value is passed as `thinkingLevel`. The script does not request thought output (`includeThoughts`), and it never saves an interim "thought image" as the result.

**Thinking and resolution combine freely.** Earlier preview models ignored `imageSize` when thinking was configured; the GA models do not (checked 2026-11-06: NB 2.1 at `high` with `2K` and 16:9 returns 2752×1536). The script no longer drops thinking when a resolution is set.

### Complexity Scoring Rubric

Evaluate the prompt against these signal categories. Each category scores 1 point if matched:

| # | Signal Category | Pattern Examples |
|---|---|---|
| 1 | **Multiple distinct subjects** (3+) | "a robot, a dog, and a tree by a lake" |
| 2 | **Spatial relationships** | "behind", "above", "between", "inside", "next to", "surrounding", "in the foreground", "reflected in" |
| 3 | **Text rendering requests** | Any quoted text in prompt: `"NOVA"`, `text that says`, `sign reading`, `label with` |
| 4 | **Photo-realism keywords** | "photorealistic", "hyper-realistic", "DSLR", "8K", "cinematic lighting", "product shot" |
| 5 | **Named art styles** | "in the style of", "art deco", "ukiyo-e", "impressionist", "Monet", "Studio Ghibli" |
| 6 | **Technical rendering** | "ray tracing", "volumetric lighting", "subsurface scattering", "depth of field", "bokeh", "HDR", "rim light" |
| 7 | **Complex composition** | "foreground...background", "layers", "split screen", "triptych", "multi-panel" |

### Scoring Thresholds

| Score | Thinking Level | Flag Value | API Value |
|---|---|---|---|
| 0-3 | Model default | `--thinking-level none` | omitted |
| 4+ | High | `--thinking-level high` | `"high"` |

Use `--thinking-level minimal` only when the user asks for speed over quality. Use `medium` only on NB 2.1, and only when the user asks for it, since it is that model's default anyway.

This rubric is applied by Claude (the AI) before calling `generate_image.py`. It is a heuristic — Claude uses judgment and may adjust based on the full context of the request.

## Thought Signatures

Every Gemini 3 image response carries encrypted `thoughtSignature` fields. They sit on the response parts themselves (the final image part and any non-thought text part), not in parts of their own. They are opaque base64 strings that encode the model's reasoning chain.

**Critical for multi-turn**: send each signature back, exactly as received, on the same part in the conversation history. Without them, the model loses context about its earlier decisions and the request may fail.

The `generate_image.py` script keeps each signature on its part in the session file when `--session-file` is used. Both `thoughtSignature` and `thought_signature` spellings are read.

## Session File Schema (`.session.json`)

```json
{
  "version": 1,
  "model": "gemini-nano-banana-2.1",
  "created_at": "2026-02-28T12:00:00Z",
  "updated_at": "2026-02-28T12:05:00Z",
  "turn_count": 4,
  "config": {
    "aspectRatio": "16:9",
    "resolution": "2K"
  },
  "last_output": "cosmic-garden-brighter-1709145900.jpg",
  "contents": [
    {
      "role": "user",
      "parts": [
        { "text": "A cosmic garden with bioluminescent flowers" }
      ]
    },
    {
      "role": "model",
      "parts": [
        { "text": "Here is your cosmic garden..." },
        {
          "inline_data_ref": { "path": "generated-images/cosmic-garden-1709145600.jpg", "mime_type": "image/jpeg" },
          "thoughtSignature": "encrypted-base64-string..."
        }
      ]
    },
    {
      "role": "user",
      "parts": [
        { "text": "Make the flowers brighter and add a moon" }
      ]
    },
    {
      "role": "model",
      "parts": [
        { "text": "I've brightened the flowers and added a crescent moon..." },
        {
          "inline_data_ref": { "path": "generated-images/cosmic-garden-brighter-1709145900.jpg", "mime_type": "image/jpeg" },
          "thoughtSignature": "encrypted-base64-string..."
        }
      ]
    }
  ]
}
```

### Key Design Decisions

**`inline_data_ref` instead of raw base64**: The session stores file paths to generated images rather than full base64 blobs. This keeps the session file at a manageable size (kilobytes, not megabytes). When `generate_image.py session read` is called, it re-encodes images from disk to produce the base64 `inline_data` the API expects.

**Session settings are inherited**: `generate` uses the session's `model`, `config.aspectRatio` and `config.resolution` unless a flag overrides them, so later turns need only `--prompt` and `--session-file`.

**Videos in sessions**: a YouTube URL passed with `--input-video` is replayed in later turns as `file_data`; a local video file is sent only on the turn it was given.

**Global session**: The session file lives at `~/.cache/claude-generate-image/.session.json`, outside the repo. Override the directory with the `CLAUDE_IMAGE_SESSION_DIR` env var.

**Session lifecycle**:
- Created automatically on first multi-turn invocation
- Reset via `generate_image.py session reset` (deletes the session file)
- Stale sessions (>30 min since last update) should prompt the user to confirm continuation

## Grounding with Google Search

Enable grounding when the prompt references real-world information:
- Current events, weather, news
- Real people, brands, or products
- Specific locations or landmarks
- Factual content that benefits from web context

### Response Attribution

When grounding is active, the response includes `groundingMetadata` with:
- `groundingChunks` — up to 3 web sources used for context
- `imageSearchQueries` — queries used for visual reference (when Image Search enabled)
- `groundingSupports` — maps specific content to citations

Present attribution links to the user when available.

### Google Image Search

Image Search grounding adds visual reference from the web. Useful for:
- Generating images of real species, objects, or places
- Style reference from existing artwork
- Accurate depictions of specific items

**NB 2.1 and NB 2 only** — Pro supports web search but not Image Search, NB 2 Lite supports no grounding at all, and Image Search cannot be used to find people.

Enabled via the combined tool config:
```json
{"google_search": {"searchTypes": {"webSearch": {}, "imageSearch": {}}}}
```

## Output Format

The API decides the output format; it can no longer be requested. The Gemini 3 models return JPEG, `gemini-2.5-flash-image` returns PNG. The script names the file after the returned MIME type (`.jpg` or `.png`). The former `personGeneration` and `imageOutputOptions` request fields now fail with HTTP 400, so the `--person-generation`, `--output-mime-type` and `--compression-quality` flags were removed. If the user needs a PNG, convert afterwards (`sips -s format png in.jpg --out out.png` on macOS).

## Video-to-Image

NB 2.1, NB 2 Lite and NB 2 accept a video as context: a public YouTube URL or a local file (up to 20 MB, sent inline). Typical uses are thumbnails, posters, summary infographics, or new artwork inspired by a scene.

```
--input-video "https://www.youtube.com/watch?v=..." --prompt "A poster capturing the key themes of this video"
--input-video clip.mp4 --aspect-ratio 4:1 --prompt "A panoramic banner in the mood of this clip"
```

## Deterministic Generation (Seed)

Use `--seed <number>` to request more deterministic output. Providing the same seed with the same parameters produces similar (not guaranteed identical) results. Useful for:
- Iterating on a prompt while keeping the visual style consistent
- Reproducing a specific result for comparison
- A/B testing with controlled variation

## Temperature

Use `--temperature <0.0-2.0>` to control creative variation:

| Range | Behavior |
|---|---|
| 0.0–0.5 | More deterministic, consistent output |
| 0.5–1.0 | Balanced (default behavior when omitted) |
| 1.0–2.0 | More creative variation, surprising results |

Lower temperature combined with a fixed seed gives the most reproducible results.

## Reference Image Editing Patterns

### Single Image Edit
One input image + text instruction = targeted edit.
```
--input-image photo.jpg --prompt "Remove the background and replace with a sunset"
```

### Style Transfer
One input image + style description.
```
--input-image photo.jpg --prompt "Transform into a watercolor painting"
```

### Multi-Reference Composition
Multiple input images + composition instruction. Up to 14 images on NB 2.1, NB 2 and Pro (NB 2.1 keeps up to 4 characters and 10 objects faithful). NB 2 Lite is not built for multi-reference work.
```
--input-image person1.jpg --input-image person2.jpg --prompt "Group photo of these people in a park"
```

### Iterative Multi-Turn Editing
Use sessions to refine progressively:
1. Generate initial image
2. "Make the sky more dramatic"
3. "Add birds in the foreground"
4. "Increase contrast"

Each turn builds on the previous, maintaining visual consistency.

## Model-Specific Behaviors

### gemini-nano-banana-2.1 (default, Nano Banana 2.1)
- GA since 2026-10-06; Google's recommended model for new work
- Better visual quality, prompt adherence, text rendering and multi-turn character consistency than NB 2
- 1K (default), 2K, 4K; no `512`
- All 14 aspect ratios, with the tiling artifacts of NB 2 on panoramic ratios at 2K/4K fixed
- Thinking `minimal` / `medium` (default) / `high`
- Web and Image Search grounding; video input
- Input token limit: 131,072

### gemini-3.1-flash-lite-image (Nano Banana 2 Lite)
- Fastest and cheapest (sub-2-second target); good for drafts and quick local edits
- 1K only; all 14 aspect ratios
- Thinking `minimal` (default) / `high`
- No grounding; not optimized for multiple references or long multi-turn edits

### gemini-3-pro-image (Nano Banana Pro)
- Premium reasoning model: complex instructions, brand consistency, dense or exact text, factual visuals
- 1K, 2K, 4K; no panoramic ratios, no `512`
- Thinking `minimal` / `high`
- Web search grounding only (no Image Search); no video input
- Up to 14 reference images, 5 at high fidelity; input token limit 65,536

### gemini-3.1-flash-image (Nano Banana 2, deprecated)
- Deprecated 2026-10-06 in favor of NB 2.1; no shutdown date yet
- The only model with `512` output
- Thinking `minimal` (default) / `high`

### gemini-2.5-flash-image (Nano Banana, legacy)
- API access limited to existing users; Google recommends NB 2 Lite instead
- No `thinkingConfig` — always pass `--thinking-level none`
- 1K only; no panoramic ratios; returns PNG

## Session Edge Cases

**Model switch mid-session**: If the user requests a different model during a session, warn them that switching models may affect continuity. Reset the session and start fresh with the new model.

**Very long sessions (10+ turns)**: The payload grows with each turn since all history is sent. If the session becomes slow, suggest resetting and starting a focused new session.

**Deleted image files**: If a referenced image file in the session is missing, `generate_image.py session read` logs a warning and skips that part. The model may produce unexpected results without the visual context.

**Concurrent access**: Sessions are designed for single-user sequential access. Do not run multiple `generate_image.py` calls with the same session file simultaneously.
