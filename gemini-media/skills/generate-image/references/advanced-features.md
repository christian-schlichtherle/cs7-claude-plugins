# Advanced Features — generate-image Skill

## Thinking Mode Auto-Detection

The thinking level controls how much internal reasoning the model does before generating an image. Higher thinking = better quality for complex prompts, but slower and more expensive.

**Model support:** Thinking is supported on Flash 3.1 and Pro 3. It is **NOT supported** on Flash 2.5 — omit `thinkingConfig` entirely for that model.

The API accepts two `thinkingLevel` values: `"minimal"` and `"high"`. The `--thinking-level` flag on `generate_image.py` maps: `none` → omitted, `minimal` → `"minimal"`, `high` → `"high"`.

### CRITICAL: Thinking and Resolution Are Mutually Exclusive

When `thinkingConfig` is included in the API request (any level — `"minimal"` or `"high"`), the Gemini API **silently ignores** the `imageSize` parameter in `imageConfig`. The output falls back to a lower default resolution (observed: ~1376x768 for 16:9 aspect ratio) regardless of the requested `imageSize`.

**Workaround:** When a specific resolution is requested (2K, 4K, or user asks for "Full HD", "4K", etc.), **omit `thinkingConfig` entirely**. The `generate_image.py` script enforces this — if both `--resolution` and a non-none `--thinking-level` are passed, it automatically forces thinking to `none` and logs a warning.

| User Request | `--resolution` | `--thinking-level` | Effective Behavior |
|---|---|---|---|
| "Generate a complex scene" | _(omitted)_ | `high` | Thinking enabled, API-default resolution (1K) |
| "Generate in 4K" | `4K` | _(any)_ | Thinking forced to `none`, 4K resolution respected |
| "Full HD steampunk scene" | `2K` or `4K` | _(any)_ | Thinking forced to `none`, resolution respected |
| Simple prompt, no size request | _(omitted)_ | `none` | No thinking, API-default resolution |

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
| 0-1 | None | `--thinking-level none` | omitted |
| 2-3 | Minimal | `--thinking-level minimal` | `"minimal"` |
| 4+ | High | `--thinking-level high` | `"high"` |

This rubric is applied by Claude (the AI) before calling `generate_image.py`. It is a heuristic — Claude uses judgment and may adjust based on the full context of the request.

## Thought Signatures

When thinking mode is enabled, the API response includes encrypted `thoughtSignature` parts alongside text and image parts. These are opaque base64 strings that encode the model's reasoning chain.

**Critical for multi-turn**: Thought signatures MUST be preserved in the session and passed back in subsequent turns. The Gemini API requires them for reasoning continuity. Without them, the model loses context about its previous generation decisions.

The `generate_image.py` script automatically preserves thought signatures in the session file when using `--session-file`.

Thought signatures appear in model response parts as:
```json
{ "thoughtSignature": "abc123..." }
```

Or in snake_case:
```json
{ "thought_signature": "abc123..." }
```

Both formats are handled by the scripts.

## Session File Schema (`.session.json`)

```json
{
  "version": 1,
  "model": "gemini-3.1-flash-image-preview",
  "created_at": "2026-02-28T12:00:00Z",
  "updated_at": "2026-02-28T12:05:00Z",
  "turn_count": 4,
  "config": {
    "aspectRatio": "16:9",
    "resolution": "2K"
  },
  "last_output": "cosmic-garden-brighter-1709145900.png",
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
        { "inline_data_ref": { "path": "generated-images/cosmic-garden-1709145600.png", "mime_type": "image/png" } },
        { "thoughtSignature": "encrypted-base64-string..." }
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
        { "inline_data_ref": { "path": "generated-images/cosmic-garden-brighter-1709145900.png", "mime_type": "image/png" } }
      ]
    }
  ]
}
```

### Key Design Decisions

**`inline_data_ref` instead of raw base64**: The session stores file paths to generated images rather than full base64 blobs. This keeps the session file at a manageable size (kilobytes, not megabytes). When `generate_image.py session read` is called, it re-encodes images from disk to produce the base64 `inline_data` the API expects.

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

**Flash models only** — the Pro model does not support Image Search grounding.

Enabled via the combined tool config:
```json
{"google_search": {"searchTypes": {"webSearch": {}, "imageSearch": {}}}}
```

## Person Generation

Use `--person-generation` to control whether the model generates images of people:

| Value | Description | Notes |
|---|---|---|
| `ALLOW_ALL` | Adults and children | May require project allowlist; restricted in EU/UK/CH/MENA |
| `ALLOW_ADULT` | Adults only (default) | Use for most requests involving people |
| `ALLOW_NONE` | No people | Use when people are not desired |

Only set this when the user specifically needs (or wants to avoid) people in the image.

## Output Format Control

Use `--output-mime-type` to control the output image format:

| Format | Flag | Best For |
|---|---|---|
| PNG (default) | `--output-mime-type image/png` | Transparency, lossless quality, editing workflows |
| JPEG | `--output-mime-type image/jpeg` | Smaller files, photographs, web content |

When using JPEG, add `--compression-quality <1-100>` to control quality (higher = better quality, larger file). If `--compression-quality` is set without `--output-mime-type`, the script automatically sets the format to JPEG.

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
Multiple input images + composition instruction. Up to 14 images.
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

### gemini-3.1-flash-image-preview (default)
- Fastest generation time (4-6s)
- Supports all features: Image Search grounding, thinking, extreme ratios, 512px
- Up to 10 reference images (objects), 4 (characters)
- Input token limit: 131,072
- Good for iterative workflows where speed matters

### gemini-3-pro-image-preview
- Highest quality output — best for final deliverables
- Slower generation (8-12s)
- Supports thinking (`minimal`, `high`)
- Does NOT support Google Image Search grounding (web search only)
- Up to 6 reference images (objects), 5 (characters)
- Input token limit: 65,536
- No extreme aspect ratios (1:4, 4:1, 1:8, 8:1), no 512px resolution

### gemini-2.5-flash-image
- GA / production-ready — most stable
- Does NOT support `thinkingConfig` — omit entirely
- Fewer aspect ratios (no extreme ratios: 1:4, 4:1, 1:8, 8:1)
- No 512px resolution
- Good balance of speed and quality

## Session Edge Cases

**Model switch mid-session**: If the user requests a different model during a session, warn them that switching models may affect continuity. Reset the session and start fresh with the new model.

**Very long sessions (10+ turns)**: The payload grows with each turn since all history is sent. If the session becomes slow, suggest resetting and starting a focused new session.

**Deleted image files**: If a referenced image file in the session is missing, `generate_image.py session read` logs a warning and skips that part. The model may produce unexpected results without the visual context.

**Concurrent access**: Sessions are designed for single-user sequential access. Do not run multiple `generate_image.py` calls with the same session file simultaneously.
