# Gemini Image Generation — REST API Reference

## Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
```

**Headers:**
- `Content-Type: application/json`
- `x-goog-api-key: $GEMINI_API_KEY`

## Supported Models

| Model ID | Type | Status | Notes |
|---|---|---|---|
| `gemini-3.1-flash-image-preview` | Flash (latest) | Preview | Default. Fastest. All features: Image Search grounding, thinking, extreme ratios, 512px. |
| `gemini-3-pro-image-preview` | Pro | Preview | Highest quality. Slower. No Image Search grounding. |
| `gemini-2.5-flash-image` | Flash (stable) | GA | Production-ready. No thinking support. Fewer aspect ratios. |

### Model Comparison

| Feature | Flash 3.1 | Pro 3 | Flash 2.5 |
|---|---|---|---|
| Max resolution | 4K + 512px | 4K | 4K |
| 512px support | Yes | No | No |
| Input token limit | 131,072 | 65,536 | ~1M |
| Max reference images (objects) | 10 | 6 | Limited |
| Max reference images (characters) | 4 | 5 | Limited |
| Image Search grounding | Yes | No | No |
| Thinking support | Yes | Yes | No |
| Extreme aspect ratios (1:4, 4:1, 1:8, 8:1) | Yes | No | No |
| Speed | Fast (4-6s) | Slower (8-12s) | Fast |

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
      "imageSize": "2K",
      "personGeneration": "ALLOW_ADULT",
      "imageOutputOptions": {
        "mimeType": "image/png",
        "compressionQuality": 85
      }
    },
    "seed": 42,
    "temperature": 1.0,
    "thinkingConfig": {
      "thinkingLevel": "high",
      "includeThoughts": true
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
  - `{"inline_data": {"mime_type": "...", "data": "..."}}` — base64-encoded image

For multi-turn, include the full conversation history with alternating user/model roles.

### `generationConfig`

#### `responseModalities`
- `["TEXT", "IMAGE"]` — return both text commentary and generated image (**required for image generation**)
- `["TEXT"]` — return text only (no image generation)

**Important:** `["IMAGE"]` (image only without text) is NOT supported. Always include `"TEXT"` when generating images.

#### `imageConfig`

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

Flash 3.1 only (extreme ratios):

| Ratio | Use Case |
|---|---|
| `1:4` | Ultra-tall vertical strip |
| `1:8` | Extreme vertical strip |
| `4:1` | Ultra-wide horizontal strip |
| `8:1` | Extreme horizontal strip |

**Resolution / Image Size:**

| Value | Description | Model Support |
|---|---|---|
| `512px` | Low resolution, fastest | Flash 3.1 only |
| `1K` | Standard resolution (API default) | All models |
| `2K` | High resolution | All models |
| `4K` | Ultra-high resolution, slowest | All models |

**`personGeneration`** (optional, inside `imageConfig`):

| Value | Description |
|---|---|
| `"ALLOW_ALL"` | Adults and children (may require allowlist; restricted in EU/UK/CH/MENA) |
| `"ALLOW_ADULT"` | Adults only (default) |
| `"ALLOW_NONE"` | No people |

**`imageOutputOptions`** (optional, inside `imageConfig`):

| Field | Type | Default | Description |
|---|---|---|---|
| `mimeType` | string | `"image/png"` | Output format: `"image/png"` or `"image/jpeg"` |
| `compressionQuality` | int | — | JPEG quality (1-100). Only applies when mimeType is `"image/jpeg"`. |

#### `seed` (optional, in `generationConfig`)

Integer. Improves determinism — same seed with same parameters produces similar output. Not guaranteed identical.

#### `temperature` (optional, in `generationConfig`)

Float, range `0.0`–`2.0`. Lower values produce more deterministic output. Higher values increase creative variation.

#### `thinkingConfig`

**Supported on:** Flash 3.1, Pro 3. **Not supported on:** Flash 2.5.

| Field | Values | Description |
|---|---|---|
| `thinkingLevel` | `"minimal"`, `"high"` | Depth of internal reasoning before generation |
| `includeThoughts` | `true` / `false` | Whether to return the model's thought process in response parts |

### `tools`

#### Google Search Grounding (web only)
```json
{"google_search": {}}
```

#### Google Search + Image Search Grounding
```json
{"google_search": {"searchTypes": {"webSearch": {}, "imageSearch": {}}}}
```

Image Search is currently supported on Flash models only.

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
              "mimeType": "image/png",
              "data": "<base64-encoded-png>"
            }
          },
          {
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
| Thought | `thought` | Model's visible reasoning (when `includeThoughts: true`) |
| Thought Signature | `thoughtSignature` / `thought_signature` | Encrypted reasoning token — must be preserved for multi-turn |

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

Maximum input images per request: 10 (Flash 3.1), 6 (Pro 3). Up to 14 total inline_data parts including input+output across multi-turn.

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
