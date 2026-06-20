#!/usr/bin/env python3
"""Generate an image via OpenAI's image API and write it to <name>.jpg.

Usage:
    OPENAI_ACCESS_KEY=sk-... python3 scripts/generate-image.py "a prompt here" [--tall|--wide|--square]
    OPENAI_ACCESS_KEY=sk-... python3 scripts/generate-image.py --prompt-file config/image/prompts/some-spec.json
    OPENAI_ACCESS_KEY=sk-... python3 scripts/generate-image.py "a prompt here" --image images/pcs/roderic-pose.jpg

Exactly one of: a prompt argument, or --prompt-file (a .json spec is passed to
the model whole; a .txt file is used as raw prompt text).

Pass one or more --image reference images to do image-to-image (a known
character/place in a new situation): each reference is sent as a likeness source
to OpenAI's images/edits endpoint instead of plain text-to-image generation.

Pass --count N (N>1) to generate N candidates from the same prompt concurrently
(one independent API call each, run in a thread pool). The outputs are suffixed
<name>-a.jpg, <name>-b.jpg, ...; --count 1 (the default) keeps the single-image
behaviour and naming unchanged.

Size defaults to --wide (1536x1024). The file is written into the repo's images/
directory as <name>.jpg (where build_site.py syncs from). Unless --name is given,
a kebab-case slug is derived from the
prompt by the naming model regardless of how the prompt was supplied. An
explicit --name overwrites any existing file; an LLM-generated name that
collides triggers a reprompt for a fresh name.
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import string
import sys
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

IMAGE_URL = "https://api.openai.com/v1/images/generations"
EDIT_URL = "https://api.openai.com/v1/images/edits"
CHAT_URL = "https://api.openai.com/v1/chat/completions"
MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2")
NAMING_MODEL = os.environ.get("OPENAI_NAMING_MODEL", "gpt-4o-mini")
MAX_NAME_LEN = 48
MAX_NAME_ATTEMPTS = 5
MAX_WORKERS = 8
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "images"


def _post(url: str, body: dict, access_key: str) -> dict:
    """POST a JSON body and return the parsed JSON response."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"API returned HTTP {exc.code}: {detail}") from exc


def _encode_multipart(
    fields: dict, files: list[tuple[str, Path]]
) -> tuple[bytes, str]:
    """Encode form fields and file parts as multipart/form-data.

    ``fields`` are simple name->value text fields; ``files`` are (form_name,
    path) tuples sent with their filename and guessed content type (the same
    form name may repeat, e.g. ``image[]``). Returns (body, content_type).
    """
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        parts.append(b"")
        parts.append(str(value).encode("utf-8"))
    for name, path in files:
        content_type = (
            mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        )
        parts.append(f"--{boundary}".encode())
        parts.append(
            f'Content-Disposition: form-data; name="{name}"; '
            f'filename="{path.name}"'.encode()
        )
        parts.append(f"Content-Type: {content_type}".encode())
        parts.append(b"")
        parts.append(path.read_bytes())
    parts.append(f"--{boundary}--".encode())
    parts.append(b"")
    body = b"\r\n".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def _post_multipart(
    url: str,
    fields: dict,
    files: list[tuple[str, Path]],
    access_key: str,
) -> dict:
    """POST a multipart/form-data body and return the parsed JSON response."""
    body, content_type = _encode_multipart(fields, files)
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {access_key}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"API returned HTTP {exc.code}: {detail}") from exc


def slugify(text: str, max_len: int = MAX_NAME_LEN) -> str:
    """Force arbitrary text into kebab-case, trimmed to max_len chars."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = slug[:max_len].rstrip("-")
    return slug or "image"


def load_prompt(text: str | None, file: str | None) -> str:
    """Resolve the prompt from a literal string or a file.

    For .json files the whole document is passed to the model as the prompt;
    a .txt file is used as raw prompt text.
    """
    if text:
        return text

    path = Path(file)
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
        return json.dumps(data, indent=2, ensure_ascii=False)
    return raw.strip()


def generate_name(
    prompt: str, access_key: str, taken: list[str] | None = None
) -> str:
    """Ask the naming model for a short kebab-case slug describing the prompt.

    If ``taken`` names are supplied, the model is told to avoid them so a
    colliding name can be reprompted into a fresh one.
    """
    system = (
        "You name image files. Given an image prompt, reply with "
        "ONLY a short descriptive filename slug: lowercase words "
        f"joined by hyphens, no extension, at most {MAX_NAME_LEN} "
        "characters. No other text."
    )
    if taken:
        system += (
            " These names are already taken, pick a clearly different one: "
            + ", ".join(taken)
            + "."
        )
    body = {
        "model": NAMING_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3 if not taken else 0.8,
    }
    response = _post(CHAT_URL, body, access_key)
    raw = response["choices"][0]["message"]["content"]
    return slugify(raw)


def unique_llm_name(prompt: str, access_key: str, out_dir: Path) -> str:
    """Get an LLM-generated name that does not collide with an existing file.

    Reprompts the naming model (telling it which names are taken) up to
    ``MAX_NAME_ATTEMPTS`` times, then falls back to a numeric suffix.
    """
    taken: list[str] = []
    name = generate_name(prompt, access_key)
    for _ in range(MAX_NAME_ATTEMPTS):
        if not (out_dir / f"{name}.jpg").exists():
            return name
        taken.append(name)
        name = generate_name(prompt, access_key, taken)
    base = name
    suffix = 2
    while (out_dir / f"{name}.jpg").exists():
        name = f"{base}-{suffix}"
        suffix += 1
    return name


def generate(
    prompt: str,
    access_key: str,
    size: str,
    images: list[Path] | None = None,
) -> bytes:
    """Call the image API and return the decoded image bytes.

    With ``images`` (reference image paths), the image-to-image edits endpoint
    is used and each reference is sent as a likeness source; otherwise plain
    text-to-image generation.
    """
    if images:
        body = _post_multipart(
            EDIT_URL,
            {
                "model": MODEL,
                "prompt": prompt,
                "size": size,
                "quality": "high",
                "n": "1",
                "output_format": "jpeg",
            },
            [("image[]", path) for path in images],
            access_key,
        )
    else:
        body = _post(
            IMAGE_URL,
            {
                "model": MODEL,
                "prompt": prompt,
                "size": size,
                "quality": "high",
                "n": 1,
                "output_format": "jpeg",
            },
            access_key,
        )

    item = body["data"][0]

    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])

    if item.get("url"):
        with urllib.request.urlopen(item["url"]) as image_response:
            return image_response.read()

    raise RuntimeError(
        f"No image data in response. Got keys: {sorted(item)}\n"
        f"Full response: {json.dumps(body, indent=2)[:1000]}"
    )


def candidate_suffixes(count: int) -> list[str]:
    """Suffixes for N concurrent candidates: a, b, c ... then numeric past 26."""
    if count <= len(string.ascii_lowercase):
        return list(string.ascii_lowercase[:count])
    return [str(i + 1) for i in range(count)]


def generate_to_file(
    name: str,
    prompt: str,
    access_key: str,
    size: str,
    images: list[Path] | None,
    out_dir: Path,
) -> tuple[str, str | None, str | None]:
    """Generate one image and write it to ``out_dir/name.jpg``.

    Returns ``(name, path_or_None, error_or_None)`` instead of raising, so one
    failed candidate in a concurrent batch does not abort the others.
    """
    try:
        image_bytes = generate(prompt, access_key, size, images)
        out_path = out_dir / f"{name}.jpg"
        out_path.write_bytes(image_bytes)
        print(f"Wrote {len(image_bytes)} bytes to {out_path}")
        return name, str(out_path), None
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - reported per-candidate
        return name, None, str(exc)


SIZES = {"tall": "1024x1536", "wide": "1536x1024", "square": "1024x1024"}


def main(argv=None) -> str:
    argv = sys.argv[1:] if argv is None else argv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "prompt",
        nargs="?",
        help="image prompt text (required unless --prompt-file is given)",
    )
    parser.add_argument(
        "-f",
        "--prompt-file",
        dest="prompt_file",
        help="read the prompt from a file; .json is passed to the model whole",
    )
    parser.add_argument(
        "-i",
        "--image",
        dest="images",
        action="append",
        metavar="PATH",
        help=(
            "reference image for image-to-image likeness (a known "
            "character/place in a new situation); repeat for multiple "
            "references. Switches from text-to-image to the edits endpoint"
        ),
    )
    group = parser.add_mutually_exclusive_group()
    for name, dim in SIZES.items():
        group.add_argument(
            f"--{name}",
            dest="size",
            action="store_const",
            const=dim,
            help=f"{dim}",
        )
    group.add_argument(
        "--size",
        dest="size",
        metavar="WxH",
        help="arbitrary size, e.g. 1792x1024 (may be rejected by the API)",
    )
    parser.add_argument(
        "--name",
        help=(
            "explicit filename slug (kebab-case); overwrites any existing "
            "file. If omitted, the naming model derives the name from the "
            "prompt regardless of how the prompt was supplied"
        ),
    )
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        type=Path,
        help="directory to write the image into (default: the repo's images/ dir)",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=1,
        metavar="N",
        help=(
            "number of candidates to generate concurrently from the same "
            "prompt (default 1). With N>1, outputs <name>-a.jpg, <name>-b.jpg, "
            "... and requires a base --name (else one is derived once)"
        ),
    )
    parser.set_defaults(size=SIZES["wide"])
    args = parser.parse_args(argv)

    if args.count < 1:
        parser.error("--count must be >= 1")

    if bool(args.prompt) == bool(args.prompt_file):
        parser.error(
            "provide exactly one of: a prompt argument or --prompt-file"
        )

    access_key = os.environ.get("OPENAI_ACCESS_KEY")
    if not access_key:
        sys.exit(
            "OPENAI_ACCESS_KEY is not set. Export your OpenAI API key first "
            "or pass it in the environment."
        )

    prompt = load_prompt(args.prompt, args.prompt_file)

    images = None
    if args.images:
        images = []
        for raw in args.images:
            path = Path(raw)
            if not path.is_file():
                sys.exit(f"reference image not found: {path}")
            images.append(path)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Single image: existing behaviour. An explicit --name overwrites any
    # existing file; otherwise the naming model picks a name and a collision
    # triggers a reprompt.
    if args.count == 1:
        image_bytes = generate(prompt, access_key, args.size, images)
        if args.name:
            name = slugify(args.name)
        else:
            name = unique_llm_name(prompt, access_key, args.out_dir)
        out_path = args.out_dir / f"{name}.jpg"
        out_path.write_bytes(image_bytes)
        print(f"Wrote {len(image_bytes)} bytes to {out_path}")
        return str(out_path)

    # Multiple candidates: one independent API call each, fanned out across a
    # thread pool (the calls are I/O-bound and do not build on one another).
    base = slugify(args.name) if args.name else generate_name(prompt, access_key)
    names = [f"{base}-{suffix}" for suffix in candidate_suffixes(args.count)]

    results: list[tuple[str, str | None, str | None]] = []
    with ThreadPoolExecutor(max_workers=min(args.count, MAX_WORKERS)) as pool:
        futures = [
            pool.submit(
                generate_to_file,
                name,
                prompt,
                access_key,
                args.size,
                images,
                args.out_dir,
            )
            for name in names
        ]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda r: r[0])
    paths = [path for _, path, _ in results if path]
    failures = [(name, err) for name, path, err in results if path is None]
    for name, err in failures:
        print(f"FAILED {name}: {err}", file=sys.stderr)
    if not paths:
        sys.exit("all image generations failed")
    return "\n".join(paths)


if __name__ == "__main__":
    main()
