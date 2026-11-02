#!/usr/bin/env python3
"""Call Gemini from Python.

Setup:  pip install google-genai
        export GEMINI_API_KEY="..."
Usage:  ./ask.py "explain diffusion models in 3 sentences"
        ./ask.py --stream "write a haiku about GPUs"
        ./ask.py --image photo.jpg "what's in this picture?"
"""
import argparse
import os
import sys

from google import genai
from google.genai import types

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="*", help="prompt text (or pipe via stdin)")
    ap.add_argument("-m", "--model", default=DEFAULT_MODEL)
    ap.add_argument("--stream", action="store_true", help="stream tokens as they arrive")
    ap.add_argument("--image", help="path to an image to include")
    ap.add_argument("--system", help="system instruction")
    args = ap.parse_args()

    prompt = " ".join(args.prompt) or sys.stdin.read()
    if not prompt.strip():
        ap.error("no prompt given")

    # Reads GEMINI_API_KEY (or GOOGLE_API_KEY) from the environment automatically.
    client = genai.Client()

    contents = [prompt]
    if args.image:
        with open(args.image, "rb") as fh:
            data = fh.read()
        mime = "image/png" if args.image.lower().endswith(".png") else "image/jpeg"
        contents.insert(0, types.Part.from_bytes(data=data, mime_type=mime))

    config = types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=2048,
        system_instruction=args.system,
    )

    if args.stream:
        for chunk in client.models.generate_content_stream(
            model=args.model, contents=contents, config=config
        ):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print()
    else:
        resp = client.models.generate_content(
            model=args.model, contents=contents, config=config
        )
        print(resp.text)
        if resp.usage_metadata:
            print(
                f"\n[{args.model}] in={resp.usage_metadata.prompt_token_count} "
                f"out={resp.usage_metadata.candidates_token_count}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
