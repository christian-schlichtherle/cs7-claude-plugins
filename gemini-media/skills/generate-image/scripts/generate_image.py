#!/usr/bin/env python3
"""generate_image.py — Gemini image generation API client.

Replaces common.sh, generate.sh, and session.sh with a single Python script
that uses only the standard library (no pip dependencies).

Subcommands:
    generate    — text-to-image / image editing / multi-turn generation
    session     — multi-turn session lifecycle (create|append|read|reset|status|set-last-output)
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

def log_info(msg):
    """Print an info message to stderr."""
    print(f"\u2139\ufe0f  {msg}", file=sys.stderr)

def log_error(msg):
    """Print an error message to stderr."""
    print(f"\u274c {msg}", file=sys.stderr)

def log_success(msg):
    """Print a success message to stderr."""
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


def get_session_dir():
    """Return the session directory path, creating it if needed."""
    d = Path(os.environ.get("CLAUDE_IMAGE_SESSION_DIR", Path.home() / ".cache" / "claude-generate-image"))
    d.mkdir(parents=True, exist_ok=True)
    return d


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
    return f"{slug}-{ts}.png"


MIME_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}

def detect_mime(filepath):
    """Return the MIME type for an image file based on its extension."""
    ext = Path(filepath).suffix.lstrip(".").lower()
    mime = MIME_MAP.get(ext)
    if not mime:
        log_error(f"Unsupported image format: .{ext} (supported: png, jpg, jpeg, webp, gif)")
        sys.exit(11)
    return mime


def encode_image(filepath):
    """Return a dict suitable for the Gemini inline_data part."""
    p = Path(filepath)
    if not p.is_file():
        log_error(f"Image file not found: {filepath}")
        sys.exit(11)
    mime = detect_mime(filepath)
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return {"inline_data": {"mime_type": mime, "data": data}}


def open_image(filepath):
    """Best-effort open the image in the desktop viewer."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


VALID_RATIOS = {
    "1:1", "1:4", "1:8", "2:3", "3:2", "3:4",
    "4:1", "4:3", "4:5", "5:4", "8:1", "9:16", "16:9", "21:9",
}
VALID_RESOLUTIONS = {"512px", "1K", "2K", "4K"}
VALID_PERSON_GEN = {"ALLOW_ALL", "ALLOW_ADULT", "ALLOW_NONE"}
VALID_OUTPUT_MIME = {"image/png", "image/jpeg"}

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def api_call(model, body, api_key):
    """POST to Gemini generateContent endpoint. Returns parsed JSON response."""
    url = f"{API_BASE}/{model}:generateContent"
    payload = json.dumps(body).encode("utf-8")
    req = Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    })

    try:
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        # Read error body
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
    except URLError as e:
        log_error(f"Network error: {e.reason}")
        sys.exit(23)


def session_file_path():
    """Return the default session file path."""
    return get_session_dir() / ".session.json"


def resolve_refs(contents):
    """Replace inline_data_ref entries with real inline_data (base64-encoded)."""
    resolved = []
    for turn in contents:
        new_parts = []
        for part in turn.get("parts", []):
            ref = part.get("inline_data_ref")
            if ref:
                ref_path = ref["path"]
                ref_mime = ref["mime_type"]
                if Path(ref_path).is_file():
                    data = base64.b64encode(Path(ref_path).read_bytes()).decode("ascii")
                    new_parts.append({"inline_data": {"mime_type": ref_mime, "data": data}})
                else:
                    log_info(f"Reference image missing, skipping: {ref_path}")
            else:
                new_parts.append(part)
        resolved.append({"role": turn["role"], "parts": new_parts})
    return resolved


def cmd_session_create(args):
    """Create a new session file with the given model and optional config."""
    if not args.model:
        log_error("create requires --model")
        sys.exit(11)

    sf = session_file_path()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    config = {}
    if args.aspect_ratio:
        config["aspectRatio"] = args.aspect_ratio
    if args.resolution:
        config["resolution"] = args.resolution

    session = {
        "version": 1,
        "model": args.model,
        "created_at": now,
        "updated_at": now,
        "turn_count": 0,
        "config": config,
        "last_output": None,
        "contents": [],
    }

    with open(sf, "w") as f:
        json.dump(session, f, indent=2)

    print(str(sf))


def _load_session(sf):
    """Read and parse a session JSON file."""
    with open(sf) as f:
        return json.load(f)


def _save_session(sf, session):
    """Write a session dict to a JSON file."""
    with open(sf, "w") as f:
        json.dump(session, f, indent=2)


def _append_turn(session, role, parts):
    """Append a turn to a session dict in-place and update metadata."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    session["contents"].append({"role": role, "parts": parts})
    session["turn_count"] = len(session["contents"])
    session["updated_at"] = now


def cmd_session_append(args):
    """Append a user or model turn to the session file."""
    if not args.session_file or not args.role or not args.content_json:
        log_error("append requires --session-file, --role, --content-json")
        sys.exit(11)

    sf = Path(args.session_file)
    if not sf.is_file():
        log_error(f"Session file not found: {sf}")
        sys.exit(11)

    session = _load_session(sf)
    try:
        content = json.loads(args.content_json)
    except json.JSONDecodeError as e:
        log_error(f"Invalid JSON in --content-json: {e}")
        sys.exit(11)
    _append_turn(session, args.role, content)
    _save_session(sf, session)


def cmd_session_read(args):
    """Read session contents, resolving inline_data_ref to base64 for the API."""
    if not args.session_file:
        log_error("read requires --session-file")
        sys.exit(11)

    sf = Path(args.session_file)
    if not sf.is_file():
        log_error(f"read requires --session-file pointing to an existing file")
        sys.exit(11)

    with open(sf) as f:
        session = json.load(f)

    resolved = resolve_refs(session["contents"])
    print(json.dumps(resolved))


def cmd_session_reset(_args):
    """Delete the active session file."""
    sf = session_file_path()
    if not sf.is_file():
        log_info("No active session to reset.")
        return
    sf.unlink()
    log_info(f"Deleted session: {sf}")


def cmd_session_status(_args):
    """Print session status as JSON (exists, model, turn count, etc.)."""
    sf = session_file_path()
    if not sf.is_file():
        print(json.dumps({"exists": False}))
        return

    with open(sf) as f:
        session = json.load(f)

    # Find last user prompt
    last_prompt = None
    for turn in session.get("contents", []):
        if turn.get("role") == "user":
            for part in turn.get("parts", []):
                if "text" in part:
                    last_prompt = part["text"]

    status = {
        "exists": True,
        "model": session.get("model"),
        "turn_count": session.get("turn_count", 0),
        "config": session.get("config", {}),
        "last_output": session.get("last_output"),
        "updated_at": session.get("updated_at"),
        "last_prompt": last_prompt,
    }
    print(json.dumps(status, indent=2))


def cmd_session_set_last_output(args):
    """Update the last_output filename in the session file."""
    if not args.session_file or not args.filename:
        log_error("set-last-output requires --session-file and --filename")
        sys.exit(11)

    sf = Path(args.session_file)
    if not sf.is_file():
        log_error(f"Session file not found: {sf}")
        sys.exit(11)

    session = _load_session(sf)
    session["last_output"] = args.filename
    _save_session(sf, session)


def _extract_text(parts):
    """Join all text fragments from a list of API response parts."""
    return "\n".join(p["text"] for p in parts if "text" in p)


def _find_image_data(parts):
    """Return the first image inline_data dict from response parts, or None."""
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            mime = inline.get("mimeType") or inline.get("mime_type") or ""
            if mime.startswith("image/"):
                return inline
    return None


def cmd_generate(args):
    """Generate or edit an image via the Gemini API."""
    if not args.prompt:
        log_error("--prompt is required")
        sys.exit(11)

    api_key = load_api_key()

    model = args.model
    aspect_ratio = args.aspect_ratio or ""
    resolution = args.resolution or ""
    thinking_level = args.thinking_level or "none"
    grounding = args.grounding
    person_generation = args.person_generation or ""
    output_mime_type = args.output_mime_type or ""
    compression_quality = args.compression_quality
    seed = args.seed
    temperature = args.temperature
    input_images = args.input_image or []
    session_file = args.session_file or ""
    output_dir = args.output_dir

    # --- Validate ---

    if aspect_ratio and aspect_ratio not in VALID_RATIOS:
        log_error(f"Invalid aspect ratio: {aspect_ratio}")
        log_error(f"Valid: {' '.join(sorted(VALID_RATIOS))}")
        sys.exit(11)

    if resolution and resolution not in VALID_RESOLUTIONS:
        log_error(f"Invalid resolution: {resolution}")
        log_error(f"Valid: {' '.join(sorted(VALID_RESOLUTIONS))}")
        sys.exit(11)

    if person_generation and person_generation not in VALID_PERSON_GEN:
        log_error(f"Invalid person-generation: {person_generation}")
        log_error(f"Valid: {' '.join(sorted(VALID_PERSON_GEN))}")
        sys.exit(11)

    if output_mime_type and output_mime_type not in VALID_OUTPUT_MIME:
        log_error(f"Invalid output-mime-type: {output_mime_type}")
        log_error(f"Valid: {' '.join(sorted(VALID_OUTPUT_MIME))}")
        sys.exit(11)

    if compression_quality is not None and (compression_quality < 1 or compression_quality > 100):
        log_error(f"Invalid compression-quality: {compression_quality} (must be 1-100)")
        sys.exit(11)

    if compression_quality is not None and output_mime_type != "image/jpeg":
        log_info("--compression-quality only applies to JPEG output; forcing --output-mime-type image/jpeg")
        output_mime_type = "image/jpeg"

    if temperature is not None and (temperature < 0.0 or temperature > 2.0):
        log_error(f"Invalid temperature: {temperature} (must be 0.0-2.0)")
        sys.exit(11)

    if resolution and thinking_level != "none":
        log_info(f"Resolution '{resolution}' requested — disabling thinking (thinking causes API to ignore imageSize)")
        thinking_level = "none"

    if len(input_images) > 14:
        log_error(f"Too many input images: {len(input_images)} (maximum 14)")
        sys.exit(11)

    for img in input_images:
        if not Path(img).is_file():
            log_error(f"Input image not found: {img}")
            sys.exit(11)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # --- Build contents array ---

    contents = []

    if session_file and Path(session_file).is_file():
        log_info(f"Loading session from {session_file}")
        session = _load_session(Path(session_file))
        contents = resolve_refs(session["contents"])

    user_parts = [{"text": args.prompt}]
    for img in input_images:
        log_info(f"Encoding image: {img}")
        user_parts.append(encode_image(img))

    contents.append({"role": "user", "parts": user_parts})

    # --- Build generationConfig ---

    gen_config = {"responseModalities": ["TEXT", "IMAGE"]}

    image_config = {}
    if aspect_ratio:
        image_config["aspectRatio"] = aspect_ratio
    if resolution:
        image_config["imageSize"] = resolution
    if person_generation:
        image_config["personGeneration"] = person_generation
    if output_mime_type or compression_quality is not None:
        output_options = {}
        if output_mime_type:
            output_options["mimeType"] = output_mime_type
        if compression_quality is not None:
            output_options["compressionQuality"] = compression_quality
        image_config["imageOutputOptions"] = output_options
    if image_config:
        gen_config["imageConfig"] = image_config

    if seed is not None:
        gen_config["seed"] = seed
    if temperature is not None:
        gen_config["temperature"] = temperature

    if thinking_level != "none":
        gen_config["thinkingConfig"] = {
            "thinkingLevel": thinking_level,
            "includeThoughts": True,
        }

    # --- Build request body ---

    body = {
        "contents": contents,
        "generationConfig": gen_config,
    }

    if grounding:
        body["tools"] = [{"google_search": {"searchTypes": {"webSearch": {}, "imageSearch": {}}}}]

    # --- API call ---

    log_info(f"Calling {model}...")
    response = api_call(model, body, api_key)

    # --- Parse response ---

    candidates = response.get("candidates", [])
    if not candidates:
        log_error("No candidates in API response.")
        sys.exit(30)

    model_parts = candidates[0].get("content", {}).get("parts", [])
    image_data = _find_image_data(model_parts)

    if not image_data:
        text_response = _extract_text(model_parts)
        log_error("No image returned by the model.")
        if text_response:
            log_info(f"Model said: {text_response}")
        sys.exit(30)

    # Decode and save image
    filename = slugify(args.prompt)
    if output_mime_type == "image/jpeg":
        filename = filename.replace(".png", ".jpg")
    image_path = str(Path(output_dir) / filename)

    Path(image_path).write_bytes(base64.b64decode(image_data.get("data")))
    log_success(f"Image saved: {image_path}")

    text_response = _extract_text(model_parts)

    if not args.no_open:
        open_image(image_path)

    # --- Update session (single load → modify → save) ---

    if session_file:
        sf = Path(session_file)
        session = _load_session(sf)

        # User turn: store refs to input images (not raw base64)
        user_session_parts = [{"text": args.prompt}]
        for img in input_images:
            user_session_parts.append({"inline_data_ref": {"path": img, "mime_type": detect_mime(img)}})
        _append_turn(session, "user", user_session_parts)

        # Model turn: image as file ref + thought signatures
        model_session_parts = []
        if text_response:
            model_session_parts.append({"text": text_response})
        img_mime = image_data.get("mimeType") or image_data.get("mime_type") or "image/png"
        model_session_parts.append({"inline_data_ref": {"path": image_path, "mime_type": img_mime}})
        for part in model_parts:
            sig = part.get("thoughtSignature") or part.get("thought_signature")
            if sig:
                model_session_parts.append({"thoughtSignature": sig})
        _append_turn(session, "model", model_session_parts)

        session["last_output"] = filename
        _save_session(sf, session)

    # --- Output structured result ---

    result = {
        "status": "success",
        "image_path": image_path,
        "text_response": text_response,
        "model": model,
        "session_file": session_file if session_file else None,
    }
    print(json.dumps(result, indent=2))



def build_parser():
    """Build the argparse parser with generate and session subcommands."""
    parser = argparse.ArgumentParser(
        description="Gemini image generation API client",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- generate ---
    gen = subparsers.add_parser("generate", help="Generate or edit an image")
    gen.add_argument("--prompt", required=True, help="Generation or editing prompt")
    gen.add_argument("--model", default="gemini-3.1-flash-image-preview", help="Model ID")
    gen.add_argument("--aspect-ratio", dest="aspect_ratio", default="", help="Aspect ratio")
    gen.add_argument("--resolution", default="", help="Image size: 512px, 1K, 2K, 4K")
    gen.add_argument("--thinking-level", dest="thinking_level", default="none",
                     choices=["none", "minimal", "high"], help="Thinking level")
    gen.add_argument("--grounding", action="store_true", help="Enable Google Search grounding")
    gen.add_argument("--person-generation", dest="person_generation", default="",
                     help="ALLOW_ALL, ALLOW_ADULT, or ALLOW_NONE")
    gen.add_argument("--output-mime-type", dest="output_mime_type", default="",
                     help="Output format: image/png (default) or image/jpeg")
    gen.add_argument("--compression-quality", dest="compression_quality", type=int, default=None,
                     help="JPEG compression quality (1-100)")
    gen.add_argument("--seed", type=int, default=None,
                     help="Seed for deterministic generation")
    gen.add_argument("--temperature", type=float, default=None,
                     help="Temperature (0.0-2.0)")
    gen.add_argument("--input-image", dest="input_image", action="append", help="Input image (repeatable)")
    gen.add_argument("--session-file", dest="session_file", default="", help="Session file for multi-turn")
    gen.add_argument("--no-open", dest="no_open", action="store_true", help="Suppress opening the output file")
    gen.add_argument("--output-dir", dest="output_dir", default="./generated-images", help="Output directory")

    # --- session ---
    sess = subparsers.add_parser("session", help="Session lifecycle management")
    sess_sub = sess.add_subparsers(dest="session_command", required=True)

    # session create
    sc = sess_sub.add_parser("create", help="Create a new session")
    sc.add_argument("--model", required=True, help="Model ID")
    sc.add_argument("--aspect-ratio", dest="aspect_ratio", default="", help="Aspect ratio")
    sc.add_argument("--resolution", default="", help="Resolution")

    # session append
    sa = sess_sub.add_parser("append", help="Append a turn to the session")
    sa.add_argument("--session-file", dest="session_file", required=True, help="Session file path")
    sa.add_argument("--role", required=True, choices=["user", "model"], help="Turn role")
    sa.add_argument("--content-json", dest="content_json", required=True, help="JSON array of parts")

    # session read
    sr = sess_sub.add_parser("read", help="Read session contents for API request")
    sr.add_argument("--session-file", dest="session_file", required=True, help="Session file path")

    # session reset
    sess_sub.add_parser("reset", help="Delete the active session")

    # session status
    sess_sub.add_parser("status", help="Show session status")

    # session set-last-output
    slo = sess_sub.add_parser("set-last-output", help="Update last output filename")
    slo.add_argument("--session-file", dest="session_file", required=True, help="Session file path")
    slo.add_argument("--filename", required=True, help="Output filename")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "session":
        dispatch = {
            "create": cmd_session_create,
            "append": cmd_session_append,
            "read": cmd_session_read,
            "reset": cmd_session_reset,
            "status": cmd_session_status,
            "set-last-output": cmd_session_set_last_output,
        }
        dispatch[args.session_command](args)


if __name__ == "__main__":
    main()
