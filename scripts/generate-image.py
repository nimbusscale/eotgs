#!/usr/bin/env python3
"""Generate an image via DigitalOcean's inference API and write it to <name>.jpg.

Usage:
    SANDBOX_MODEL_ACCESS_KEY=doo_v1_... python3 scripts/generate-image.py "a prompt here" [--tall|--wide|--square]
    SANDBOX_MODEL_ACCESS_KEY=doo_v1_... python3 scripts/generate-image.py --prompt-file config/image/prompts/some-spec.json

Exactly one of: a prompt argument, or --prompt-file (a .json spec is passed to
the model whole; a .txt file is used as raw prompt text).

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
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

IMAGE_URL = "https://inference.do-ai.run/v1/images/generations"
CHAT_URL = "https://inference.do-ai.run/v1/chat/completions"
MODEL = "openai-gpt-image-2"
NAMING_MODEL = "openai-gpt-4o-mini"
MAX_NAME_LEN = 48
MAX_NAME_ATTEMPTS = 5
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


def generate(prompt: str, access_key: str, size: str) -> bytes:
    """Call the image generation API and return the decoded image bytes."""
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
    parser.set_defaults(size=SIZES["wide"])
    args = parser.parse_args(argv)

    if bool(args.prompt) == bool(args.prompt_file):
        parser.error(
            "provide exactly one of: a prompt argument or --prompt-file"
        )

    access_key = os.environ.get("SANDBOX_MODEL_ACCESS_KEY")
    if not access_key:
        sys.exit(
            "SANDBOX_MODEL_ACCESS_KEY is not set. Export your sandbox key first "
            "(distinct from the customer MODEL_ACCESS_KEY) or pass it in the environment."
        )

    prompt = load_prompt(args.prompt, args.prompt_file)

    image_bytes = generate(prompt, access_key, args.size)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # An explicit --name overwrites any existing file; otherwise the naming
    # model picks a name and a collision triggers a reprompt.
    if args.name:
        name = slugify(args.name)
    else:
        name = unique_llm_name(prompt, access_key, args.out_dir)

    out_path = args.out_dir / f"{name}.jpg"
    out_path.write_bytes(image_bytes)

    print(f"Wrote {len(image_bytes)} bytes to {out_path}")
    return str(out_path)


if __name__ == "__main__":
    main()
