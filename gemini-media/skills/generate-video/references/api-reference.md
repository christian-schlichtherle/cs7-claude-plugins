# Gemini Veo Video Generation — REST API Reference

## Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:predictLongRunning
```

**Headers:**
- `Content-Type: application/json`
- `x-goog-api-key: $GEMINI_API_KEY`

## Supported Models

| Model ID | Status | Notes |
|---|---|---|
| `veo-3.1-generate-preview` | Preview | Full-quality. Native audio, reference images, video extension, frame interpolation. |
| `veo-3.1-fast-generate-preview` | Preview | Faster generation, slightly lower quality. Same feature set as 3.1. |
| `veo-3.0-generate-preview` | Preview | Previous generation. Native audio, no reference images or extension. |
| `veo-3.0-fast-generate-001` | Stable | Production-ready fast variant of Veo 3. |

### Model Compatibility Matrix

| Feature | Veo 3.0 | Veo 3.1 |
|---|---|---|
| Text-to-video | Yes | Yes |
| Image-to-video | Yes | Yes |
| Frame interpolation (lastFrame) | No | Yes |
| Video extension | No | Yes |
| Reference images | No | Yes (up to 3 asset) |
| Native audio (generateAudio) | Yes | Yes |
| Resolution control | Yes | Yes (incl. 4k) |
| Seed for determinism | Yes | Yes |

## Request Body Schemas

### Text-to-Video

```json
{
  "instances": [{
    "prompt": "A slow cinematic drone shot over a misty mountain range at sunrise"
  }],
  "parameters": {
    "aspectRatio": "16:9",
    "resolution": "720p",
    "durationSeconds": 8,
    "negativePrompt": "blurry, low quality, text overlays",
    "personGeneration": "allow_adult",
    "generateAudio": true,
    "seed": 42,
    "sampleCount": 1,
    "compressionQuality": "optimized"
  }
}
```

### Image-to-Video (First Frame Animation)

```json
{
  "instances": [{
    "prompt": "The camera slowly zooms into the scene as leaves drift down",
    "image": {
      "bytesBase64Encoded": "<base64-encoded-image>",
      "mimeType": "image/png"
    }
  }],
  "parameters": {
    "aspectRatio": "16:9",
    "resolution": "720p",
    "resizeMode": "pad"
  }
}
```

### Frame Interpolation (First + Last Frame)

**Note:** Despite Google docs showing `lastFrame` in `parameters` with `inlineData`, the
`predictLongRunning` endpoint only accepts `lastFrame` inside `instances[0]` using
`bytesBase64Encoded` format. The `parameters` placement is rejected with HTTP 400.

```json
{
  "instances": [{
    "prompt": "Smooth transition between the two scenes",
    "image": {
      "bytesBase64Encoded": "<base64-first-frame>",
      "mimeType": "image/png"
    },
    "lastFrame": {
      "bytesBase64Encoded": "<base64-last-frame>",
      "mimeType": "image/png"
    }
  }]
}
```

### Reference Images (Style/Content Guide)

```json
{
  "instances": [{
    "prompt": "A woman walks through a garden wearing the red dress"
  }],
  "parameters": {
    "referenceImages": [
      {
        "image": {
          "bytesBase64Encoded": "<base64-data>",
          "mimeType": "image/png"
        },
        "referenceType": "asset"
      }
    ]
  }
}
```

### Video Extension

```json
{
  "instances": [{
    "prompt": "The camera continues to pan right revealing a waterfall",
    "video": {
      "bytesBase64Encoded": "<base64-encoded-video>",
      "mimeType": "video/mp4"
    }
  }],
  "parameters": {
    "numberOfVideos": 1,
    "resolution": "720p"
  }
}
```

## Parameters Reference

### `instances[0]`

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | Yes | Text description of the video to generate |
| `image` | object | No | Starting frame for image-to-video or interpolation |
| `lastFrame` | object | No | Final frame for interpolation (Veo 3.1 only) |
| `video` | object | No | Previous video for extension |

### `parameters`

| Field | Type | Default | Values | Description |
|---|---|---|---|---|
| `aspectRatio` | string | `"16:9"` | `"16:9"`, `"9:16"` | Video aspect ratio |
| `resolution` | string | `"720p"` | `"720p"`, `"1080p"`, `"4k"` | Output resolution (Veo 3+ only; 4k on Veo 3.1 preview only) |
| `durationSeconds` | int | `8` | `4`, `6`, `8` | Video duration in seconds |
| `negativePrompt` | string | — | free text | Content to exclude |
| `personGeneration` | string | `"allow_adult"` | `"allow_all"`, `"allow_adult"`, `"dont_allow"` | People generation control |
| `generateAudio` | bool | — | `true`, `false` | Enable/disable native audio synthesis (Veo 3+ only) |
| `seed` | uint32 | — | `0`–`4294967295` | Seed for more deterministic output |
| `sampleCount` | int | `1` | `1`–`4` | Number of video variations to generate |
| `resizeMode` | string | `"pad"` | `"pad"`, `"crop"` | How to resize input image for image-to-video (Veo 3+ only) |
| `compressionQuality` | string | `"optimized"` | `"optimized"`, `"lossless"` | Output video compression |
| `referenceImages` | array | — | up to 3 items | Style/content reference images (Veo 3.1 only) |
| `numberOfVideos` | int | — | `1` | Number of videos (extension only) |

### Parameter Constraints

| Constraint | Rule |
|---|---|
| High resolution (1080p/4k) | Duration must be 8 seconds |
| 4k resolution | Veo 3.1 preview models only |
| Video extension | Resolution locked to 720p; duration locked to 8s |
| Reference images | Maximum 3 asset images; Veo 3.1 only; duration must be 8s |
| Frame interpolation | Requires both `image` (first frame) and `lastFrame`; Veo 3.1 only |
| `resizeMode` | Only applies to image-to-video on Veo 3+ models |
| `generateAudio` | Veo 3+ models only (not supported on Veo 2) |
| `personGeneration` | `"allow_all"` may require project allowlist; restricted in EU/UK/CH/MENA |

## Polling Endpoint

```
GET https://generativelanguage.googleapis.com/v1beta/{operation_name}
```

**Headers:**
- `x-goog-api-key: $GEMINI_API_KEY`

### Operation Response (In Progress)

```json
{
  "name": "models/veo-3.1-generate-preview/operations/abc123...",
  "done": false
}
```

### Operation Response (Completed)

```json
{
  "name": "models/veo-3.1-generate-preview/operations/abc123...",
  "done": true,
  "response": {
    "generateVideoResponse": {
      "generatedSamples": [
        {
          "video": {
            "uri": "https://generativelanguage.googleapis.com/v1beta/files/...",
            "mimeType": "video/mp4"
          }
        }
      ]
    }
  }
}
```

### Operation Response (Failed)

```json
{
  "name": "models/veo-3.1-generate-preview/operations/abc123...",
  "done": true,
  "error": {
    "code": 400,
    "message": "Content policy violation",
    "status": "INVALID_ARGUMENT"
  }
}
```

## Video Download

Download the video from the URI returned in the completed operation:

```
GET {video.uri}
Headers: x-goog-api-key: $GEMINI_API_KEY
```

Returns raw MP4 bytes. Videos are retained for **2 days** — download within this window.

## Supported Input MIME Types

**Images (for image-to-video, interpolation, references):**
- `image/png`
- `image/jpeg`
- `image/webp`

**Video (for extension):**
- `video/mp4` (1-30 seconds, 24 fps, 720p or 1080p)

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
| 403 | PERMISSION_DENIED | Invalid API key |
| 429 | RESOURCE_EXHAUSTED | Rate limit exceeded — retry after delay |
| 500 | INTERNAL | Server error — retry |
| 503 | UNAVAILABLE | Service temporarily unavailable — retry |

## Performance Characteristics

| Metric | Value |
|---|---|
| Minimum latency | ~11 seconds |
| Maximum latency (peak) | ~6 minutes |
| Recommended poll interval | 10 seconds |
| Video retention | 2 days |
| Extension limit | Up to 20 extensions per video |
| SynthID watermark | Always applied (invisible) |

## Audio

Veo 3+ models generate native audio synchronized with the video content. Audio cues can be included in the prompt (e.g., "birds chirping", "dialogue between two people", "upbeat background music"). Audio is embedded in the MP4 output. Use the `generateAudio` parameter to explicitly enable or disable audio synthesis.
