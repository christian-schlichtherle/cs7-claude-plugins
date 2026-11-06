# Gemini Image Generation — REST API Reference

Checked against the live API on 2026-11-06.

## Endpoint

```
POST https://generativelanguage.googleapis.com/v1/models/{model}:generateContent
```

**Headers:**
- `Content-Type: application/json`
- `x-goog-api-key: $GEMINI_API_KEY`

The GA image models are served on `v1`; `v1beta` still answers as well.

## Supported Models

| Model ID | Name | Status | Notes |
|---|---|---|---|
| `gemini-nano-banana-2.1` | Nano Banana 2.1 | GA (Oct 2026) | **Default.** Best quality per cost, text rendering, multi-turn consistency. 1K/2K/4K. |
| `gemini-3.1-flash-lite-image` | Nano Banana 2 Lite | GA | Fastest and cheapest. 1K only. No grounding. Weak at multi-reference and multi-turn. |
| `gemini-3-pro-image` | Nano Banana Pro | GA | Premium reasoning model for complex scenes, brand assets, dense text. |
| `gemini-3.1-flash-image` | Nano Banana 2 | Deprecated (Oct 2026, no shutdown date) | The only model with `512` output. Migrate to 2.1. |
| `gemini-2.5-flash-image` | Nano Banana | Legacy (existing users only) | No thinking, no extreme ratios. |

Shut down: `gemini-3.1-flash-image-preview` and `gemini-3-pro-image-preview` (2026-06-25), all Imagen 4 models (2026-08-17).

### Model Comparison

| Feature | NB 2.1 | NB 2 Lite | Pro | NB 2 | NB (2.5) |
|---|---|---|---|---|---|
| Image sizes | 1K, 2K, 4K | 1K | 1K, 2K, 4K | 512, 1K, 2K, 4K | 1K |
| Extreme ratios (1:4, 4:1, 1:8, 8:1) | Yes | Yes | No | Yes | No |
| Thinking levels | `minimal`, `medium` (default), `high` | `minimal` (default), `high` | `minimal`, `high` | `minimal` (default), `high` | none |
| Web Search grounding | Yes | No | Yes | Yes | No |
| Image Search grounding | Yes | No | No | Yes | No |
| Video input (video-to-image) | Yes | Yes | No | Yes | No |
| Reference images | up to 14 (4 characters, 10 objects) | few | up to 14 (5 high-fidelity) | up to 14 (4 characters, 10 objects) | ~3 |
| Input token limit | 131,072 | — | 65,536 | 131,072 | 65,536 |

## Request Body Schema

```json
{
  "contents": [
    {
      "role": "user",
      "parts": [
        { "text": "A futuristic city in a glass bottle floating in space" },
        {
          "inline_data": {
            "mime_type": "image/jpeg",
            "data": "<base64-encoded-image>"
          }
        }
      ]
    }
  ],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"],
    "imageConfig": {
      "aspectRatio": "16:9",
      "imageSize": "2K"
    },
    "seed": 42,
    "temperature": 1.0,
    "thinkingConfig": {
      "thinkingLevel": "high"
    }
  },
  "tools": [
    {
      "google_search": {
        "searchTypes": {
          "webSearch": {},
          "imageSearch": {}
        }
      }
    }
  ]
}
```

### `contents` Array

Each entry has:
- `role`: `"user"` or `"model"` (alternating for multi-turn)
- `parts`: Array of content parts:
  - `{"text": "..."}` — text prompt or response
  - `{"inline_data": {"mime_type": "...", "data": "..."}}` — base64-encoded image or video
  - `{"file_data": {"file_uri": "https://www.youtube.com/watch?v=..."}}` — public YouTube video (video-to-image)

For multi-turn, include the full conversation history with alternating user/model roles, and send every `thoughtSignature` back on the part it arrived with.

### `generationConfig`

#### `responseModalities`
- `["TEXT", "IMAGE"]` — text commentary plus the generated image (what the script sends)
- `["IMAGE"]` — image only; accepted by the current models

#### `imageConfig`

Only `aspectRatio` and `imageSize` exist. The former `personGeneration` and `imageOutputOptions` (output MIME type, JPEG quality) fields are rejected with HTTP 400 ("Cannot find field").

**Aspect Ratios:**

All models support:

| Ratio | Use Case |
|---|---|
| `1:1` | Square — social media, avatars |
| `2:3` | Portrait — print, photography |
| `3:2` | Landscape — photography |
| `3:4` | Portrait — tablets, frames |
| `4:3` | Classic landscape — presentations |
| `4:5` | Portrait — Instagram |
| `5:4` | Near-square landscape |
| `9:16` | Vertical — phone screens, Stories |
| `16:9` | Widescreen — desktop, video |
| `21:9` | Ultra-wide — cinematic |

NB 2.1, NB 2 Lite and NB 2 only (panoramic ratios):

| Ratio | Use Case |
|---|---|
| `1:4` | Ultra-tall vertical strip |
| `1:8` | Extreme vertical strip |
| `4:1` | Ultra-wide horizontal strip |
| `8:1` | Extreme horizontal strip |

Without an `aspectRatio`, the output matches the input image's ratio, or the model picks one.

**Resolution / Image Size** (uppercase `K`; lowercase is rejected):

| Value | Description | Model Support |
|---|---|---|
| `512` | 0.5K, fastest | NB 2 (`gemini-3.1-flash-image`) only |
| `1K` | Standard (default) | All models |
| `2K` | High resolution | NB 2.1, Pro, NB 2 |
| `4K` | Ultra-high resolution, slowest | NB 2.1, Pro, NB 2 |

Unsupported combinations fail with HTTP 400, e.g. "Image size 4K is not supported for this model".

**Output format:** the API picks it. The Gemini 3 models return JPEG, `gemini-2.5-flash-image` returns PNG. The script names the file after the returned `mimeType`.

#### `seed` (optional, in `generationConfig`)

Integer. Improves determinism — same seed with same parameters produces similar output. Not guaranteed identical.

#### `temperature` (optional, in `generationConfig`)

Float, range `0.0`–`2.0`. Lower values produce more deterministic output. Higher values increase creative variation.

#### `thinkingConfig`

The Gemini 3 image models always think; the level only tunes how much. Omit `thinkingConfig` to get the model's default level. Not supported on `gemini-2.5-flash-image`.

| Field | Values | Description |
|---|---|---|
| `thinkingLevel` | `"minimal"`, `"medium"` (NB 2.1 only), `"high"` | Depth of reasoning before generation. An unsupported level fails with HTTP 400. |
| `includeThoughts` | `true` / `false` | Return the thought text and up to two interim "thought images" as parts flagged `"thought": true`. Thinking tokens are billed either way. |

Thinking and `imageSize` combine fine: NB 2.1 at `high` with `2K` returns 2752×1536.

### `tools`

#### Google Search Grounding (web only)
```json
{"google_search": {}}
```

#### Google Search + Image Search Grounding
```json
{"google_search": {"searchTypes": {"webSearch": {}, "imageSearch": {}}}}
```

Image Search works on NB 2.1 and NB 2 only and cannot search for people. NB 2 Lite supports no grounding at all.

## Response Schema

Successful response (HTTP 200):

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          { "text": "Here is your futuristic city..." },
          {
            "inlineData": {
              "mimeType": "image/jpeg",
              "data": "<base64-encoded-jpeg>"
            },
            "thoughtSignature": "<encrypted-base64-string>"
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP"
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 10,
    "candidatesTokenCount": 303,
    "totalTokenCount": 313
  }
}
```

**Response parts may use camelCase** (`inlineData`, `mimeType`, `thoughtSignature`) — scripts handle both camelCase and snake_case variants.

### Part Types in Response

| Part Type | Field | Description |
|---|---|---|
| Text | `text` | Model's text commentary or description |
| Image | `inlineData` / `inline_data` | Base64-encoded generated image |
| Thought | `"thought": true` on a text or image part | Reasoning text and interim images (only with `includeThoughts: true`). Never the final image. |
| Thought Signature | `thoughtSignature` / `thought_signature` on a part | Encrypted reasoning token — send back on the same part in multi-turn history |

### Grounding Metadata

When grounding tools are used, the response includes:

```json
{
  "groundingMetadata": {
    "searchEntryPoint": { "renderedContent": "<html>..." },
    "groundingChunks": [
      { "web": { "uri": "https://...", "title": "..." } }
    ],
    "imageSearchQueries": ["query used for visual context"],
    "groundingSupports": [
      {
        "segment": { "startIndex": 0, "endIndex": 100, "text": "..." },
        "groundingChunkIndices": [0],
        "confidenceScores": [0.95]
      }
    ]
  }
}
```

## Supported Input MIME Types

- `image/png`
- `image/jpeg`
- `image/webp`
- `image/gif`
- Video (NB 2.1, NB 2 Lite, NB 2): `video/mp4`, `video/quicktime`, `video/webm`, `video/mpeg`, `video/x-msvideo` inline (the script caps inline video at 20 MB), or a public YouTube URL via `file_data`

Up to 14 reference images per request on NB 2.1, NB 2 and Pro.

## Error Responses

```json
{
  "error": {
    "code": 400,
    "message": "Request contains an invalid argument.",
    "status": "INVALID_ARGUMENT"
  }
}
```

| HTTP Code | Status | Common Cause |
|---|---|---|
| 400 | INVALID_ARGUMENT | Malformed request, invalid parameters, content policy violation |
| 403 | PERMISSION_DENIED | Invalid API key, key lacks permissions |
| 429 | RESOURCE_EXHAUSTED | Rate limit exceeded — retry after delay |
| 500 | INTERNAL | Server error — retry |
| 503 | UNAVAILABLE | Service temporarily unavailable — retry |

## Rate Limits

Rate limits vary by model and API tier. Common defaults:
- **RPM** (requests per minute): 15-60 depending on tier
- **TPM** (tokens per minute): varies
- Image generation requests are heavier than text — expect lower effective RPM.

When rate limited (429), wait at least 10 seconds before retrying.
