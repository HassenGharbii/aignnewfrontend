"""Stream the extraction call for specific references and print the model's
output as it is generated, to see what a call that never finishes is producing.

Uses exactly the prompt, schema and options the worker uses, but streams, stops
itself after --max-tokens, and needs no timeout.

Run with: python -m app.debug_extract 010000-3065-081617 210200-1059-082989
"""

import argparse
import json
import sys
import time

import requests

from . import config, models
from .db import SessionLocal
from .pipeline import EXTRACTION_SCHEMA, build_extraction_prompt


def stream_extraction(prompt: str, max_tokens: int) -> None:
    payload = {
        "model": config.EXTRACTION_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "format": EXTRACTION_SCHEMA,
        "stream": True,
        "think": False,
        "options": {"temperature": 0, "num_predict": max_tokens},
    }
    started = time.monotonic()
    with requests.post(f"{config.OLLAMA_HOST}/api/chat", json=payload, stream=True, timeout=(10, 600)) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            sys.stdout.write(chunk.get("message", {}).get("content", ""))
            sys.stdout.flush()
            if chunk.get("done"):
                print(
                    f"\n--- elapsed={time.monotonic() - started:.1f}s "
                    f"prompt_tokens={chunk.get('prompt_eval_count')} generated={chunk.get('eval_count')} "
                    f"done_reason={chunk.get('done_reason')}"
                )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("references", nargs="+")
    parser.add_argument("--max-tokens", type=int, default=3000)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        for reference in args.references:
            raw = db.query(models.RawEvent).filter_by(reference=reference).first()
            if raw is None:
                print(f"=== {reference}: not in raw_events")
                continue
            print(f"=== {reference} model={config.EXTRACTION_MODEL}")
            print(f"--- subject: {raw.subject}")
            print(f"--- event_summary ({len(raw.event_summary or '')} chars):\n{raw.event_summary}")
            print("--- model output:")
            stream_extraction(build_extraction_prompt(raw.event_summary or "", raw.subject or ""), args.max_tokens)
    finally:
        db.close()


if __name__ == "__main__":
    main()
