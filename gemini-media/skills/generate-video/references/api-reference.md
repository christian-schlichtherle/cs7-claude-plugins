# Gemini Omni Flash — Interactions API Reference

Checked against the live API on 2026-11-06.

## Models

| Model ID | Status | Notes |
|---|---|---|
| `gemini-omni-1.2-flash` | GA (2026-11-05) | **Default.** 3-15 s, native audio, up to 6 reference images, extension to 30 s. |
| `gemini-omni-1.1-flash` | GA, superseded | 3-10 s. Requests route to 1.2 from 2026-12-03. |
| `gemini-omni-flash-preview` | Shut down | — |

Shut down: every Veo model in the Gemini API — `veo-2.0-generate-001`, `veo-3.0-generate-001`, `veo-3.0-fast-generate-001` (2026-06-30) and `veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview`, `veo-3.1-lite-generate-preview` (2026-10-22). GA Veo 3.1 remains only on Google's Gemini Enterprise Agent Platform (Vertex), which this plugin does not use.

## Endpoints

```
POST   https://generativelanguage.googleapis.com/v1beta/interactions          create
GET    https://generativelanguage.googleapis.com/v1beta/interactions/{id}     poll / fetch
POST   https://generativelanguage.googleapis.com/v1beta/interactions/{id}/cancel
DELETE https://generativelanguage.googleapis.com/v1beta/interactions/{id}
```

**Headers:**
- `Content-Type: application/json`
- `x-goog-api-key: $GEMINI_API_KEY`
- `Api-Revision: 2026-05-20` — pins the Interactions API revision the script was written against

Omni does not support `generateContent` for video output; use the Interactions API.

## Request Body

```json
{
  "model": "gemini-omni-1.2-flash",
  "input": [
    {"type": "image", "mime_type": "image/png", "data": "<base64>"},
    {"type": "text", "text": "Bring this drawing to life, using it only as a guide for movement."}
  ],
  "response_format": {
    "type": "video",
    "aspect_ratio": "16:9",
    "resolution": "720p",
    "duration": "8s"
  },
  "previous_interaction_id": "v1_...",
  "generation_config": {
    "video_config": {"task": "image_to_video"}
  },
  "background": true
}
```

| Field | Values | Notes |
|---|---|---|
| `model` | `gemini-omni-1.2-flash` | required |
| `input` | string, or array of content blocks | A plain string is a text-only prompt. |
| `response_format.type` | `"video"` | |
| `response_format.aspect_ratio` | `"16:9"` (default), `"9:16"` | |
| `response_format.resolution` | `"360p"`, `"720p"` (default), `"1080p"`, `"4k"` | 1080p and 4k are upscaled. |
| `response_format.duration` | `"3s"` … `"15s"` (default `"10s"`) | Overrides any length in the prompt. Over 15 s → 400. Interpolation and per-turn extension: 3-10 s. |
| `response_format.delivery` | `"uri"` | Return a Files API URI instead of inline data (for >4 MB). The URI is only in the create response or stream; a later GET returns inline data. |
| `previous_interaction_id` | interaction ID | Edit or extend the video of that interaction. It must be `completed`. |
| `generation_config.video_config.task` | `text_to_video`, `image_to_video`, `reference_to_video`, `edit`, `extend` | Fallback only; constrains how inputs combine. Try prompting first. |
| `background` | `true` | Return immediately with `status: "in_progress"`; poll with GET. Requires `store` true (the default). |
| `store` | `true` (default) / `false` | `false` makes the result un-editable via `previous_interaction_id` and is incompatible with `background`. |

Not supported: system instructions, temperature, `top_p`, stop sequences, negative prompts, seed, sample count, audio input, YouTube input.

### Content blocks

| Block | Shape |
|---|---|
| Text | `{"type": "text", "text": "..."}` |
| Image (inline) | `{"type": "image", "mime_type": "image/png", "data": "<base64>"}` |
| Image (file) | `{"type": "image", "uri": "<Files API URI>"}` |
| Video (inline) | `{"type": "video", "mime_type": "video/mp4", "data": "<base64>"}` |
| Video (file) | `{"type": "video", "uri": "<Files API URI>"}` |

One image + text → image-to-video. Two images + a transition prompt → first/last-frame interpolation. Images described as characters/objects → reference-to-video. A video + edit prompt → edit; a video + "extend/continue" prompt → extension.

## Response

Create (background):

```json
{"id": "v1_...", "status": "in_progress", "object": "interaction", "model": "gemini-omni-1.2-flash", ...}
```

GET once finished:

```json
{
  "id": "v1_...",
  "status": "completed",
  "model": "gemini-omni-1.2-flash",
  "object": "interaction",
  "steps": [
    {"type": "user_input", "content": [{"type": "text", "text": "..."}]},
    {"type": "thought", "signature": "...", "content": []},
    {"type": "model_output", "content": [
      {"type": "video", "mime_type": "video/mp4", "data": "<base64 mp4>"}
    ]}
  ],
  "usage": {
    "total_input_tokens": 17,
    "total_output_tokens": 5793,
    "output_tokens_by_modality": [{"modality": "video", "tokens": 5793}],
    "total_thought_tokens": 422
  }
}
```

The `steps` array holds only the current turn. On an extension turn, the returned video is the whole, longer video, not just the new part. `output_video` is an SDK convenience field and is not in the REST response.

### Status values

| Status | Meaning |
|---|---|
| `in_progress` | Still generating — poll again |
| `requires_action` | Paused for client input (not used by Omni video) |
| `completed` | Video available in `steps` |
| `failed` | Error; see `error` |
| `cancelled` | Stopped via the cancel endpoint |

## Errors

```json
{"error": {"message": "Requested video duration 20s 0ns exceeds the maximum allowed 15s 0ns", "code": "invalid_request"}}
```

`code` is a string here, unlike `generateContent`. Map by HTTP status:

| HTTP | Typical cause |
|---|---|
| 400 | Invalid argument (duration, too many references, interpolation over 10 s, chaining onto an unfinished interaction), safety block, regional restriction |
| 401/403 | Invalid key or missing permission |
| 404 | Unknown or expired interaction ID |
| 429 | Rate limit |
| 5xx | Server error — retry |

## Observed timing and cost

| Request | Time | Output tokens |
|---|---|---|
| 3 s, 360p, text-to-video | ~15 s | ~5,800 video tokens |
| 3 s, 360p, two-frame interpolation | ~26 s | — |
| 3 s, 360p, edit via `previous_interaction_id` | ~37 s | — |

Video output is billed at $12.00 per 1M tokens on `gemini-omni-1.2-flash` (the price at GA). Longer and higher-resolution videos take longer and cost more.
