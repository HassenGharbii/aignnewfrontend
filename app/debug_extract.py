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
from .pipeline import EXTRACTION_SCHEMA, build_extraction_prompt, chat_payload


def stream_extraction(prompt: str, max_tokens: int) -> None:
    payload = chat_payload(config.EXTRACTION_MODEL, prompt, EXTRACTION_SCHEMA, max_tokens, stream=True)
    # stream_options is what makes vLLM emit a final usage chunk; without it a
    # streamed response carries no token counts at all.
    payload["stream_options"] = {"include_usage": True}

    started = time.monotonic()
    url = f"{config.VLLM_HOST}/v1/chat/completions"
    with requests.post(url, json=payload, stream=True, timeout=(10, 600)) as resp:
        resp.raise_for_status()
        finish_reason = None
        for line in resp.iter_lines():
            # vLLM streams server-sent events: "data: {...}" lines, blank lines
            # between them, and a final literal "data: [DONE]".
            if not line:
                continue
            line = line.decode("utf-8") if isinstance(line, bytes) else line
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            for choice in chunk.get("choices") or []:
                sys.stdout.write(choice.get("delta", {}).get("content") or "")
                sys.stdout.flush()
                finish_reason = choice.get("finish_reason") or finish_reason
            # The usage chunk arrives last and carries an empty choices list.
            usage = chunk.get("usage")
            if usage:
                print(
                    f"\n--- elapsed={time.monotonic() - started:.1f}s "
                    f"prompt_tokens={usage.get('prompt_tokens')} "
                    f"generated={usage.get('completion_tokens')} "
                    f"finish_reason={finish_reason}"
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
