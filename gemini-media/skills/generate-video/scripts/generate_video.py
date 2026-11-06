#!/usr/bin/env python3
"""generate_video.py — Gemini Omni Flash video generation API client.

Uses only the standard library (no pip dependencies). Talks to the
Interactions API (POST /v1beta/interactions) with background execution
and client-side polling.

Subcommands:
    generate    — text-to-video, image-to-video, interpolation, reference
                  images, and editing or extending a previous video
    poll        — check on (or wait for) a background interaction
    session     — show or reset the last interaction used by --continue
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
    print(f"ℹ️  {msg}", file=sys.stderr)


def log_error(msg):
    print(f"❌ {msg}", file=sys.stderr)


def log_success(msg):
    print(f"✅ {msg}", file=sys.stderr)


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
    return f"{slug or 'video'}-{ts}.mp4"


IMAGE_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}
VIDEO_MIME = {
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
}
MAX_INLINE_VIDEO_BYTES = 20 * 1024 * 1024


def encode_media(filepath, kind):
    """Return an Interactions API content block with the file inlined as base64."""
    p = Path(filepath)
    if not p.is_file():
        log_error(f"{kind.capitalize()} file not found: {filepath}")
        sys.exit(11)
    table = IMAGE_MIME if kind == "image" else VIDEO_MIME
    ext = p.suffix.lstrip(".").lower()
    mime = table.get(ext)
    if not mime:
        log_error(f"Unsupported {kind} format: .{ext} (supported: {', '.join(sorted(table))})")
        sys.exit(11)
    if kind == "video" and p.stat().st_size > MAX_INLINE_VIDEO_BYTES:
        log_error(f"Video too large to send inline: {p.stat().st_size} bytes (max {MAX_INLINE_VIDEO_BYTES})")
        sys.exit(11)
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return {"type": kind, "mime_type": mime, "data": data}


def open_file(filepath):
    """Best-effort open the file in the desktop viewer."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


DEFAULT_MODEL = "gemini-omni-1.2-flash"
VALID_RATIOS = {"16:9", "9:16"}
VALID_RESOLUTIONS = {"360p", "720p", "1080p", "4k"}
VALID_TASKS = {"text_to_video", "image_to_video", "reference_to_video", "edit", "extend"}
MAX_IMAGES = 6
MIN_DURATION, MAX_DURATION = 3, 15

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
# Pin the Interactions API revision so a future breaking change does not
# silently alter the request or response shape this script relies on.
API_REVISION = "2026-05-20"
TERMINAL_STATES = {"completed", "failed", "cancelled", "incomplete"}


def _headers(api_key):
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
        "Api-Revision": API_REVISION,
    }


def api_request(method, url, api_key, body=None, timeout=180):
    """Send a JSON request to the Gemini API. Returns parsed JSON response."""
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(url, data=payload, method=method, headers=_headers(api_key))
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        _handle_http_error(e)
    except URLError as e:
        log_error(f"Network error: {e.reason}")
        sys.exit(23)


def api_download(url, api_key, dest_path, timeout=300):
    """Download a file from a URI with API key auth."""
    req = Request(url, method="GET", headers={"x-goog-api-key": api_key})
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
    if code in (400, 404):
        log_error(f"API error ({code}): {error_msg}")
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


# --- Session: remembers the last interaction so --continue can chain onto it ---

def session_file_path():
    d = Path(os.environ.get("CLAUDE_VIDEO_SESSION_DIR", Path.home() / ".cache" / "claude-generate-video"))
    d.mkdir(parents=True, exist_ok=True)
    return d / ".session.json"


def load_session():
    sf = session_file_path()
    if not sf.is_file():
        return None
    with open(sf) as f:
        return json.load(f)


def save_session(**fields):
    session = load_session() or {}
    session.update(fields)
    session["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(session_file_path(), "w") as f:
        json.dump(session, f, indent=2)


# --- Interaction handling ---

def poll_interaction(interaction_id, api_key, poll_interval=10, timeout=900):
    """Poll an interaction until it reaches a terminal state. Returns the interaction."""
    start = time.time()
    while True:
        interaction = api_request("GET", f"{API_BASE}/interactions/{interaction_id}", api_key, timeout=300)
        status = interaction.get("status", "")
        elapsed = int(time.time() - start)
        if status in TERMINAL_STATES:
            return interaction
        if elapsed >= timeout:
            log_error(f"Timed out after {elapsed}s waiting for interaction (status: {status}).")
            log_error(f"Check later with: poll --interaction {interaction_id} --wait")
            sys.exit(24)
        log_info(f"Status: {status or 'unknown'} ({elapsed}s elapsed)...")
        time.sleep(poll_interval)


def extract_video(interaction):
    """Return the last video content block of the interaction's model output."""
    status = interaction.get("status")
    if status != "completed":
        log_error(f"Interaction ended with status '{status}'.")
        err = interaction.get("error")
        if err:
            log_error(json.dumps(err))
        text = extract_text(interaction)
        if text:
            log_info(f"Model said: {text}")
        sys.exit(30)

    videos = [
        block
        for step in interaction.get("steps", [])
        if step.get("type") == "model_output"
        for block in step.get("content", [])
        if block.get("type") == "video"
    ]
    if not videos:
        log_error("No video in the model output.")
        text = extract_text(interaction)
        if text:
            log_info(f"Model said: {text}")
        sys.exit(30)
    return videos[-1]


def extract_text(interaction):
    return "\n".join(
        block["text"]
        for step in interaction.get("steps", [])
        if step.get("type") == "model_output"
        for block in step.get("content", [])
        if block.get("type") == "text" and block.get("text")
    )


def save_video(video, api_key, dest_path):
    if video.get("data"):
        Path(dest_path).write_bytes(base64.b64decode(video["data"]))
    elif video.get("uri"):
        api_download(video["uri"], api_key, dest_path)
    else:
        log_error("Video block has neither data nor uri.")
        sys.exit(30)


def finish(interaction, api_key, prompt, output_dir, no_open, elapsed=None):
    """Save the interaction's video, update the session, print the result JSON."""
    video = extract_video(interaction)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    video_path = str(Path(output_dir) / slugify(prompt))
    save_video(video, api_key, video_path)
    log_success(f"Video saved: {video_path}")

    save_session(
        interaction_id=interaction["id"],
        model=interaction.get("model"),
        last_output=video_path,
        last_prompt=prompt,
        pending_interaction_id=None,
        pending_prompt=None,
    )

    if not no_open:
        open_file(video_path)

    result = {
        "status": "success",
        "video_path": video_path,
        "interaction_id": interaction["id"],
        "model": interaction.get("model"),
        "text_response": extract_text(interaction),
    }
    if elapsed is not None:
        result["generation_time_seconds"] = elapsed
    print(json.dumps(result, indent=2))


def cmd_generate(args):
    api_key = load_api_key()

    images = args.image or []
    if len(images) > MAX_IMAGES:
        log_error(f"Too many images: {len(images)} (maximum {MAX_IMAGES})")
        sys.exit(11)
    if args.aspect_ratio and args.aspect_ratio not in VALID_RATIOS:
        log_error(f"Invalid aspect ratio: {args.aspect_ratio} (valid: {', '.join(sorted(VALID_RATIOS))})")
        sys.exit(11)
    if args.resolution and args.resolution not in VALID_RESOLUTIONS:
        log_error(f"Invalid resolution: {args.resolution} (valid: {', '.join(sorted(VALID_RESOLUTIONS))})")
        sys.exit(11)
    if args.duration is not None and not (MIN_DURATION <= args.duration <= MAX_DURATION):
        log_error(f"Invalid duration: {args.duration} (must be {MIN_DURATION}-{MAX_DURATION} seconds)")
        sys.exit(11)
    if args.task and args.task not in VALID_TASKS:
        log_error(f"Invalid task: {args.task} (valid: {', '.join(sorted(VALID_TASKS))})")
        sys.exit(11)

    previous_id = args.previous_interaction or ""
    if args.continue_session:
        if previous_id:
            log_error("Use either --continue or --previous-interaction, not both.")
            sys.exit(11)
        session = load_session()
        if not session or not session.get("interaction_id"):
            log_error("No previous video to continue from. Generate one first.")
            sys.exit(11)
        previous_id = session["interaction_id"]
        log_info(f"Continuing from interaction {previous_id}")

    # --- Build input ---

    blocks = []
    if args.video:
        log_info(f"Encoding video: {args.video}")
        blocks.append(encode_media(args.video, "video"))
    for img in images:
        log_info(f"Encoding image: {img}")
        blocks.append(encode_media(img, "image"))

    if blocks:
        blocks.append({"type": "text", "text": args.prompt})
        input_value = blocks
    else:
        input_value = args.prompt

    response_format = {"type": "video"}
    if args.aspect_ratio:
        response_format["aspect_ratio"] = args.aspect_ratio
    if args.resolution:
        response_format["resolution"] = args.resolution
    if args.duration is not None:
        response_format["duration"] = f"{args.duration}s"

    body = {
        "model": args.model,
        "input": input_value,
        "response_format": response_format,
        "background": True,
    }
    if previous_id:
        body["previous_interaction_id"] = previous_id
    if args.task:
        body["generation_config"] = {"video_config": {"task": args.task}}

    # --- Submit ---

    log_info(f"Submitting to {args.model}...")
    start = time.time()
    interaction = api_request("POST", f"{API_BASE}/interactions", api_key, body=body)
    interaction_id = interaction.get("id")
    if not interaction_id:
        log_error("API response has no interaction id.")
        log_error(json.dumps(interaction)[:500])
        sys.exit(30)
    log_info(f"Interaction: {interaction_id}")

    save_session(pending_interaction_id=interaction_id, pending_prompt=args.prompt)

    if args.no_wait and interaction.get("status") not in TERMINAL_STATES:
        print(json.dumps({
            "status": "submitted",
            "interaction_id": interaction_id,
            "model": args.model,
        }, indent=2))
        return

    if interaction.get("status") not in TERMINAL_STATES:
        log_info("Generating video (typically 15 seconds to a few minutes)...")
        interaction = poll_interaction(interaction_id, api_key, args.poll_interval, args.timeout)

    finish(interaction, api_key, args.prompt, args.output_dir, args.no_open,
           elapsed=int(time.time() - start))


def cmd_poll(args):
    api_key = load_api_key()
    interaction_id = args.interaction
    session = load_session() or {}
    if not interaction_id:
        interaction_id = session.get("pending_interaction_id")
        if not interaction_id:
            log_error("No --interaction given and no pending interaction recorded.")
            sys.exit(11)

    if args.wait:
        interaction = poll_interaction(interaction_id, api_key, args.poll_interval, args.timeout)
    else:
        interaction = api_request("GET", f"{API_BASE}/interactions/{interaction_id}", api_key, timeout=300)
        if interaction.get("status") not in TERMINAL_STATES:
            print(json.dumps({
                "status": interaction.get("status"),
                "interaction_id": interaction_id,
            }, indent=2))
            return

    prompt = session.get("pending_prompt") if session.get("pending_interaction_id") == interaction_id else None
    if not prompt:
        prompt = next(
            (block.get("text", "")
             for step in interaction.get("steps", []) if step.get("type") == "user_input"
             for block in step.get("content", []) if block.get("type") == "text"),
            "video",
        )
    finish(interaction, api_key, prompt, args.output_dir, args.no_open)


def cmd_session(args):
    if args.session_command == "status":
        session = load_session()
        print(json.dumps({"exists": True, **session} if session else {"exists": False}, indent=2))
    elif args.session_command == "reset":
        sf = session_file_path()
        if sf.is_file():
            sf.unlink()
            log_info(f"Deleted session: {sf}")
        else:
            log_info("No active session to reset.")


def build_parser():
    parser = argparse.ArgumentParser(description="Gemini Omni Flash video generation API client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_wait_flags(p):
        p.add_argument("--poll-interval", dest="poll_interval", type=int, default=10,
                       help="Seconds between polls (default: 10)")
        p.add_argument("--timeout", type=int, default=900,
                       help="Max seconds to wait (default: 900)")
        p.add_argument("--no-open", dest="no_open", action="store_true",
                       help="Suppress opening the output file")
        p.add_argument("--output-dir", dest="output_dir", default="./generated-videos",
                       help="Output directory")

    gen = subparsers.add_parser("generate", help="Generate, edit or extend a video")
    gen.add_argument("--prompt", required=True, help="Generation, editing or extension prompt")
    gen.add_argument("--model", default=DEFAULT_MODEL, help=f"Model ID (default: {DEFAULT_MODEL})")
    gen.add_argument("--aspect-ratio", dest="aspect_ratio", default="", help="16:9 (default) or 9:16")
    gen.add_argument("--resolution", default="", help="360p, 720p (default), 1080p, or 4k")
    gen.add_argument("--duration", type=int, default=None,
                     help="Seconds, 3-15 (default 10; 3-10 for interpolation and extension)")
    gen.add_argument("--image", action="append",
                     help="Input image: first frame, last frame or reference (repeatable, max 6)")
    gen.add_argument("--video", default="", help="Local video to edit or extend (sent inline, max 20 MB)")
    gen.add_argument("--continue", dest="continue_session", action="store_true",
                     help="Edit or extend the last generated video")
    gen.add_argument("--previous-interaction", dest="previous_interaction", default="",
                     help="Interaction ID to edit or extend")
    gen.add_argument("--task", default="",
                     help="Fallback mode hint: " + ", ".join(sorted(VALID_TASKS)))
    gen.add_argument("--no-wait", dest="no_wait", action="store_true",
                     help="Submit and return immediately")
    add_wait_flags(gen)

    pol = subparsers.add_parser("poll", help="Check or wait on a background interaction")
    pol.add_argument("--interaction", default="",
                     help="Interaction ID (default: the last one submitted)")
    pol.add_argument("--wait", action="store_true", help="Wait for completion and download")
    add_wait_flags(pol)

    sess = subparsers.add_parser("session", help="Show or reset the --continue session")
    sess_sub = sess.add_subparsers(dest="session_command", required=True)
    sess_sub.add_parser("status", help="Show the last interaction")
    sess_sub.add_parser("reset", help="Forget the last interaction")

    return parser


def main():
    args = build_parser().parse_args()
    {"generate": cmd_generate, "poll": cmd_poll, "session": cmd_session}[args.command](args)


if __name__ == "__main__":
    main()
