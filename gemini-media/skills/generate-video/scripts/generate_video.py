#!/usr/bin/env python3
"""generate_video.py — Gemini Veo video generation API client.

Uses only the standard library (no pip dependencies).

Subcommands:
    generate    — text-to-video / image-to-video / frame interpolation
    extend      — extend a previously generated video
    poll        — check status of a running operation
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def log_info(msg):
    print(f"\u2139\ufe0f  {msg}", file=sys.stderr)


def log_error(msg):
    print(f"\u274c {msg}", file=sys.stderr)


def log_success(msg):
    print(f"\u2705 {msg}", file=sys.stderr)


def load_api_key():
    """Return GEMINI_API_KEY, loading from .env if necessary."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key

    # Look for .env in the current working directory (where the user runs Claude Code)
    env_file = Path.cwd() / ".env"
    if env_file.is_file():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
                    os.environ["GEMINI_API_KEY"] = key
                    return key

    log_error("GEMINI_API_KEY environment variable is not set.")
    log_error("Run: export GEMINI_API_KEY='your-key-here'")
    log_error("Or add GEMINI_API_KEY=your-key to .env in the repo root.")
    sys.exit(10)


def slugify(prompt):
    """Turn a prompt into a filesystem-safe slug, append unix timestamp."""
    slug = re.sub(r"[^a-z0-9 -]", "", prompt.lower())
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug).strip("-")

    if len(slug) > 50:
        slug = slug[:50]
        if "-" in slug:
            slug = slug.rsplit("-", 1)[0]

    ts = int(datetime.now(timezone.utc).timestamp())
    return f"{slug}-{ts}.mp4"


MIME_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


def detect_image_mime(filepath):
    ext = Path(filepath).suffix.lstrip(".").lower()
    mime = MIME_MAP.get(ext)
    if not mime:
        log_error(f"Unsupported image format: .{ext} (supported: png, jpg, jpeg, webp)")
        sys.exit(11)
    return mime


def encode_image(filepath):
    """Return a dict with base64-encoded image data for the Veo predictLongRunning API.

    The instances-level fields (image, video) use bytesBase64Encoded format.
    """
    p = Path(filepath)
    if not p.is_file():
        log_error(f"Image file not found: {filepath}")
        sys.exit(11)
    mime = detect_image_mime(filepath)
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return {"bytesBase64Encoded": data, "mimeType": mime}


def encode_image_inline(filepath):
    """Return an inlineData dict for parameters-level fields (lastFrame, referenceImages)."""
    p = Path(filepath)
    if not p.is_file():
        log_error(f"Image file not found: {filepath}")
        sys.exit(11)
    mime = detect_image_mime(filepath)
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime, "data": data}}


def encode_video(filepath):
    """Return a dict with base64-encoded video data for the Veo predictLongRunning API."""
    p = Path(filepath)
    if not p.is_file():
        log_error(f"Video file not found: {filepath}")
        sys.exit(11)
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return {"bytesBase64Encoded": data, "mimeType": "video/mp4"}


def open_file(filepath):
    """Best-effort open the file in the desktop viewer."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


VALID_RATIOS = {"16:9", "9:16"}
VALID_RESOLUTIONS = {"720p", "1080p", "4k"}
VALID_DURATIONS = {"4", "6", "8"}
VALID_PERSON_GEN = {"allow_all", "allow_adult", "dont_allow"}
VALID_RESIZE_MODES = {"pad", "crop"}
VALID_COMPRESSION = {"optimized", "lossless"}

API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def api_post(url, body, api_key, timeout=180):
    """POST JSON to a Gemini endpoint. Returns parsed JSON response."""
    payload = json.dumps(body).encode("utf-8")
    req = Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        _handle_http_error(e)
    except URLError as e:
        log_error(f"Network error: {e.reason}")
        sys.exit(23)


def api_get(url, api_key, timeout=30):
    """GET from a Gemini endpoint. Returns parsed JSON response."""
    req = Request(url, method="GET", headers={
        "x-goog-api-key": api_key,
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        _handle_http_error(e)
    except URLError as e:
        log_error(f"Network error: {e.reason}")
        sys.exit(23)


def api_download(url, api_key, dest_path, timeout=120):
    """Download a file from a URI with API key auth."""
    req = Request(url, method="GET", headers={
        "x-goog-api-key": api_key,
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            Path(dest_path).write_bytes(resp.read())
    except HTTPError as e:
        _handle_http_error(e)
    except URLError as e:
        log_error(f"Network error downloading video: {e.reason}")
        sys.exit(23)


def _handle_http_error(e):
    """Handle HTTPError with appropriate exit codes."""
    error_body = ""
    try:
        error_body = e.read().decode("utf-8", errors="replace")
    except Exception:
        pass

    error_msg = "Unknown error"
    try:
        error_msg = json.loads(error_body).get("error", {}).get("message", error_body)
    except (json.JSONDecodeError, AttributeError):
        error_msg = error_body or str(e)

    code = e.code
    if code == 400:
        log_error(f"API error (400): {error_msg}")
        sys.exit(20)
    elif code in (401, 403):
        log_error(f"API auth error ({code}): {error_msg}")
        sys.exit(21)
    elif code == 429:
        log_error("Rate limited by Gemini API (429). Wait and retry.")
        sys.exit(22)
    elif code >= 500:
        log_error(f"API server error ({code}): {error_msg}")
        sys.exit(23)
    else:
        log_error(f"Unexpected HTTP status: {code}")
        log_error(error_msg)
        sys.exit(20)


def poll_operation(operation_name, api_key, poll_interval=10, timeout=600):
    """Poll an operation until done or timeout. Returns the final response."""
    url = f"{API_BASE}/{operation_name}"
    start = time.monotonic()
    first = True

    while True:
        elapsed = int(time.monotonic() - start)
        if elapsed >= timeout:
            break

        if not first:
            time.sleep(poll_interval)
            elapsed = int(time.monotonic() - start)
        first = False

        response = api_get(url, api_key)
        done = response.get("done", False)

        if done:
            error = response.get("error")
            if error:
                log_error(f"Operation failed: {error.get('message', error)}")
                sys.exit(20)
            return response

        log_info(f"Generating video... ({elapsed}s elapsed)")

    log_error(f"Operation timed out after {timeout}s. Operation: {operation_name}")
    log_error("The video may still be generating. Use the poll command to check:")
    log_error(f"  python3 generate_video.py poll --operation \"{operation_name}\"")
    sys.exit(24)


def extract_video_uris(response):
    """Extract all video download URIs from a completed operation response."""
    try:
        resp = response.get("response", {})
        samples = resp.get("generateVideoResponse", {}).get("generatedSamples", [])
        if not samples:
            log_error("No video samples in response.")
            sys.exit(30)
        uris = []
        for sample in samples:
            uri = sample.get("video", {}).get("uri")
            if uri:
                uris.append(uri)
        if not uris:
            log_error("No video URIs in response.")
            sys.exit(30)
        return uris
    except (KeyError, IndexError, TypeError) as e:
        log_error(f"Unexpected response structure: {e}")
        log_error(json.dumps(response, indent=2))
        sys.exit(30)


def cmd_generate(args):
    """Generate a video via the Veo API (text-to-video, image-to-video, or frame interpolation)."""
    if not args.prompt:
        log_error("--prompt is required")
        sys.exit(11)

    api_key = load_api_key()

    model = args.model
    aspect_ratio = args.aspect_ratio or ""
    resolution = args.resolution or ""
    duration = args.duration or ""
    negative_prompt = args.negative_prompt or ""
    person_generation = args.person_generation or ""
    generate_audio = args.generate_audio
    seed = args.seed
    sample_count = args.sample_count
    resize_mode = args.resize_mode or ""
    compression_quality = args.compression_quality or ""
    image_path = args.image or ""
    last_frame_path = args.last_frame or ""
    ref_images = args.reference_image or []
    output_dir = args.output_dir
    poll_interval = args.poll_interval
    timeout = args.timeout

    # --- Validate ---

    if aspect_ratio and aspect_ratio not in VALID_RATIOS:
        log_error(f"Invalid aspect ratio: {aspect_ratio}")
        log_error(f"Valid: {' '.join(sorted(VALID_RATIOS))}")
        sys.exit(11)

    if resolution and resolution not in VALID_RESOLUTIONS:
        log_error(f"Invalid resolution: {resolution}")
        log_error(f"Valid: {' '.join(sorted(VALID_RESOLUTIONS))}")
        sys.exit(11)

    if duration and duration not in VALID_DURATIONS:
        log_error(f"Invalid duration: {duration}")
        log_error(f"Valid: {' '.join(sorted(VALID_DURATIONS))}")
        sys.exit(11)

    if person_generation and person_generation not in VALID_PERSON_GEN:
        log_error(f"Invalid person-generation: {person_generation}")
        log_error(f"Valid: {' '.join(sorted(VALID_PERSON_GEN))}")
        sys.exit(11)

    if resize_mode and resize_mode not in VALID_RESIZE_MODES:
        log_error(f"Invalid resize-mode: {resize_mode}")
        log_error(f"Valid: {' '.join(sorted(VALID_RESIZE_MODES))}")
        sys.exit(11)

    if compression_quality and compression_quality not in VALID_COMPRESSION:
        log_error(f"Invalid compression-quality: {compression_quality}")
        log_error(f"Valid: {' '.join(sorted(VALID_COMPRESSION))}")
        sys.exit(11)

    if sample_count is not None and (sample_count < 1 or sample_count > 4):
        log_error(f"Invalid sample-count: {sample_count} (must be 1-4)")
        sys.exit(11)

    if resize_mode and not image_path:
        log_error("--resize-mode only applies to image-to-video (requires --image)")
        sys.exit(11)

    if resolution in ("1080p", "4k") and duration and duration != "8":
        log_error(f"High resolution ({resolution}) requires duration of 8 seconds.")
        sys.exit(11)

    if len(ref_images) > 3:
        log_error(f"Too many reference images: {len(ref_images)} (maximum 3)")
        sys.exit(11)

    if last_frame_path and not image_path:
        log_error("--last-frame requires --image (first frame)")
        sys.exit(11)

    if image_path and not Path(image_path).is_file():
        log_error(f"Image file not found: {image_path}")
        sys.exit(11)

    if last_frame_path and not Path(last_frame_path).is_file():
        log_error(f"Last frame file not found: {last_frame_path}")
        sys.exit(11)

    for ref in ref_images:
        if not Path(ref).is_file():
            log_error(f"Reference image not found: {ref}")
            sys.exit(11)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # --- Build request body ---

    instance = {"prompt": args.prompt}

    if image_path:
        log_info(f"Encoding image: {image_path}")
        instance["image"] = encode_image(image_path)

    parameters = {}

    if aspect_ratio:
        parameters["aspectRatio"] = aspect_ratio
    if resolution:
        parameters["resolution"] = resolution
    if duration:
        parameters["durationSeconds"] = int(duration)
    if negative_prompt:
        parameters["negativePrompt"] = negative_prompt
    if person_generation:
        parameters["personGeneration"] = person_generation
    if generate_audio is not None:
        parameters["generateAudio"] = generate_audio
    if seed is not None:
        parameters["seed"] = seed
    if sample_count is not None:
        parameters["sampleCount"] = sample_count
    if resize_mode:
        parameters["resizeMode"] = resize_mode
    if compression_quality:
        parameters["compressionQuality"] = compression_quality

    if last_frame_path:
        log_info(f"Encoding last frame: {last_frame_path}")
        # lastFrame goes in instances[0] with bytesBase64Encoded format
        # (parameters placement is rejected by predictLongRunning endpoint)
        if last_frame_path == image_path and "image" in instance:
            instance["lastFrame"] = instance["image"]
            log_info("Reusing first frame data for last frame (same file)")
        else:
            instance["lastFrame"] = encode_image(last_frame_path)

    if ref_images:
        ref_list = []
        for ref_path in ref_images:
            log_info(f"Encoding reference image: {ref_path}")
            ref_list.append({
                "image": encode_image(ref_path),
                "referenceType": "asset",
            })
        parameters["referenceImages"] = ref_list

    body = {"instances": [instance]}
    if parameters:
        body["parameters"] = parameters

    # --- Submit generation ---

    url = f"{API_BASE}/models/{model}:predictLongRunning"
    log_info(f"Submitting video generation to {model}...")
    response = api_post(url, body, api_key)

    operation_name = response.get("name")
    if not operation_name:
        log_error("No operation name in response.")
        log_error(json.dumps(response, indent=2))
        sys.exit(30)

    log_info(f"Operation started: {operation_name}")

    # --- Poll for completion ---

    if args.no_wait:
        result = {
            "status": "submitted",
            "operation": operation_name,
            "model": model,
            "message": "Use the poll command to check status.",
        }
        print(json.dumps(result, indent=2))
        return

    log_info(f"Polling every {poll_interval}s (timeout: {timeout}s)...")
    final_response = poll_operation(operation_name, api_key, poll_interval, timeout)

    # --- Download video(s) ---

    video_uris = extract_video_uris(final_response)
    video_paths = []

    for i, video_uri in enumerate(video_uris):
        suffix = f"-{i + 1}" if len(video_uris) > 1 else ""
        base = slugify(args.prompt)
        filename = base.replace(".mp4", f"{suffix}.mp4") if suffix else base
        video_path = str(Path(output_dir) / filename)

        log_info(f"Downloading video{f' {i + 1}/{len(video_uris)}' if len(video_uris) > 1 else ''}...")
        api_download(video_uri, api_key, video_path)
        log_success(f"Video saved: {video_path}")
        video_paths.append(video_path)
        if not args.no_open:
            open_file(video_path)

    # --- Output structured result ---

    result = {
        "status": "success",
        "video_path": video_paths[0],
        "video_paths": video_paths,
        "model": model,
        "operation": operation_name,
        "duration_seconds": duration or "8",
        "sample_count": len(video_paths),
    }
    print(json.dumps(result, indent=2))


def cmd_extend(args):
    """Extend a previously generated video."""
    if not args.prompt:
        log_error("--prompt is required")
        sys.exit(11)
    if not args.video:
        log_error("--video is required (path to MP4 to extend)")
        sys.exit(11)

    api_key = load_api_key()
    model = args.model
    output_dir = args.output_dir
    poll_interval = args.poll_interval
    timeout = args.timeout

    video_path = args.video
    if not Path(video_path).is_file():
        log_error(f"Video file not found: {video_path}")
        sys.exit(11)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Extension is locked to 720p
    log_info(f"Encoding video for extension: {video_path}")
    instance = {
        "prompt": args.prompt,
        "video": encode_video(video_path),
    }

    parameters = {
        "numberOfVideos": 1,
        "resolution": "720p",
    }

    body = {"instances": [instance], "parameters": parameters}

    url = f"{API_BASE}/models/{model}:predictLongRunning"
    log_info(f"Submitting video extension to {model}...")
    response = api_post(url, body, api_key)

    operation_name = response.get("name")
    if not operation_name:
        log_error("No operation name in response.")
        sys.exit(30)

    log_info(f"Operation started: {operation_name}")

    if args.no_wait:
        result = {
            "status": "submitted",
            "operation": operation_name,
            "model": model,
            "message": "Use the poll command to check status.",
        }
        print(json.dumps(result, indent=2))
        return

    log_info(f"Polling every {poll_interval}s (timeout: {timeout}s)...")
    final_response = poll_operation(operation_name, api_key, poll_interval, timeout)

    video_uri = extract_video_uris(final_response)[0]
    filename = slugify(args.prompt)
    out_path = str(Path(output_dir) / filename)

    log_info("Downloading extended video...")
    api_download(video_uri, api_key, out_path)
    log_success(f"Extended video saved: {out_path}")

    if not args.no_open:
        open_file(out_path)

    result = {
        "status": "success",
        "video_path": out_path,
        "model": model,
        "operation": operation_name,
        "source_video": video_path,
    }
    print(json.dumps(result, indent=2))


def cmd_poll(args):
    """Check status of a running operation, optionally wait and download."""
    if not args.operation:
        log_error("--operation is required")
        sys.exit(11)

    api_key = load_api_key()
    operation_name = args.operation
    output_dir = args.output_dir

    if args.wait:
        poll_interval = args.poll_interval
        timeout = args.timeout
        log_info(f"Waiting for operation: {operation_name}")
        final_response = poll_operation(operation_name, api_key, poll_interval, timeout)

        video_uri = extract_video_uris(final_response)[0]
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ts = int(datetime.now(timezone.utc).timestamp())
        filename = f"video-{ts}.mp4"
        out_path = str(Path(output_dir) / filename)

        log_info("Downloading video...")
        api_download(video_uri, api_key, out_path)
        log_success(f"Video saved: {out_path}")
        if not args.no_open:
            open_file(out_path)

        result = {
            "status": "success",
            "video_path": out_path,
            "operation": operation_name,
        }
        print(json.dumps(result, indent=2))
    else:
        url = f"{API_BASE}/{operation_name}"
        response = api_get(url, api_key)
        done = response.get("done", False)
        error = response.get("error")

        status_info = {
            "operation": operation_name,
            "done": done,
        }
        if error:
            status_info["error"] = error.get("message", str(error))
        if done and not error:
            status_info["message"] = "Video is ready. Run with --wait to download."

        print(json.dumps(status_info, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Gemini Veo video generation API client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- generate ---
    gen = subparsers.add_parser("generate", help="Generate a video (text-to-video, image-to-video, interpolation)")
    gen.add_argument("--prompt", required=True, help="Video generation prompt")
    gen.add_argument("--model", default="veo-3.1-fast-generate-preview", help="Model ID")
    gen.add_argument("--aspect-ratio", dest="aspect_ratio", default="", help="16:9 or 9:16")
    gen.add_argument("--resolution", default="", help="720p, 1080p, or 4k")
    gen.add_argument("--duration", default="", help="4, 6, or 8 seconds")
    gen.add_argument("--negative-prompt", dest="negative_prompt", default="", help="What to exclude")
    gen.add_argument("--person-generation", dest="person_generation", default="",
                     help="allow_all, allow_adult, or dont_allow")
    gen.add_argument("--generate-audio", dest="generate_audio", default=None,
                     action="store_true",
                     help="Generate native audio (Veo 3+ models)")
    gen.add_argument("--no-audio", dest="generate_audio", action="store_false",
                     help="Disable audio generation")
    gen.add_argument("--seed", type=int, default=None,
                     help="Seed for deterministic generation (uint32)")
    gen.add_argument("--sample-count", dest="sample_count", type=int, default=None,
                     help="Number of videos to generate (1-4)")
    gen.add_argument("--resize-mode", dest="resize_mode", default="",
                     help="Resize mode for image-to-video: pad or crop")
    gen.add_argument("--compression-quality", dest="compression_quality", default="",
                     help="Output quality: optimized or lossless")
    gen.add_argument("--image", default="", help="First frame image for image-to-video")
    gen.add_argument("--last-frame", dest="last_frame", default="", help="Last frame for interpolation")
    gen.add_argument("--reference-image", dest="reference_image", action="append",
                     help="Reference image (repeatable, max 3)")
    gen.add_argument("--no-wait", dest="no_wait", action="store_true",
                     help="Submit and return immediately without polling")
    gen.add_argument("--poll-interval", dest="poll_interval", type=int, default=10,
                     help="Seconds between poll attempts (default: 10)")
    gen.add_argument("--timeout", type=int, default=600,
                     help="Max seconds to wait for generation (default: 600)")
    gen.add_argument("--no-open", dest="no_open", action="store_true",
                     help="Suppress opening the output file")
    gen.add_argument("--output-dir", dest="output_dir", default="./generated-videos", help="Output directory")

    # --- extend ---
    ext = subparsers.add_parser("extend", help="Extend a previously generated video")
    ext.add_argument("--prompt", required=True, help="Continuation prompt")
    ext.add_argument("--video", required=True, help="Path to MP4 video to extend")
    ext.add_argument("--model", default="veo-3.1-fast-generate-preview", help="Model ID")
    ext.add_argument("--no-wait", dest="no_wait", action="store_true",
                     help="Submit and return immediately without polling")
    ext.add_argument("--poll-interval", dest="poll_interval", type=int, default=10,
                     help="Seconds between poll attempts (default: 10)")
    ext.add_argument("--timeout", type=int, default=600,
                     help="Max seconds to wait for generation (default: 600)")
    ext.add_argument("--no-open", dest="no_open", action="store_true",
                     help="Suppress opening the output file")
    ext.add_argument("--output-dir", dest="output_dir", default="./generated-videos", help="Output directory")

    # --- poll ---
    pol = subparsers.add_parser("poll", help="Check or wait on a running operation")
    pol.add_argument("--operation", required=True, help="Operation name from a previous submission")
    pol.add_argument("--wait", action="store_true", help="Wait for completion and download")
    pol.add_argument("--poll-interval", dest="poll_interval", type=int, default=10,
                     help="Seconds between poll attempts (default: 10)")
    pol.add_argument("--timeout", type=int, default=600,
                     help="Max seconds to wait (default: 600)")
    pol.add_argument("--no-open", dest="no_open", action="store_true",
                     help="Suppress opening the output file")
    pol.add_argument("--output-dir", dest="output_dir", default="./generated-videos", help="Output directory")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "extend":
        cmd_extend(args)
    elif args.command == "poll":
        cmd_poll(args)


if __name__ == "__main__":
    main()
