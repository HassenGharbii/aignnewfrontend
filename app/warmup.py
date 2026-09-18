"""Block until vLLM is genuinely ready to serve, then make it stay that way.

vLLM answers /health only once weights are loaded, but the first *guided* request
still pays a one-off cost the healthcheck never triggers: xgrammar compiles the
JSON schema into a grammar, and CUDA graphs get captured. On a 14B that can be
tens of seconds, which would otherwise land on the worker's first real event and
look like a hang.

So this waits for the model to appear, then fires one schema-guided request
shaped like the real classify call. It runs as the `warmup` service that api and
worker gate on, and by hand as:

    python -m app.warmup
"""

import os
import sys
import time

import requests

from . import config
from .pipeline import chat_payload, log

# Model load dominates this: weights are pulled from disk (or downloaded from
# HuggingFace on a cold cache) before the server serves anything.
READY_TIMEOUT = float(os.getenv("WARMUP_READY_TIMEOUT", "1800"))
READY_POLL_SECONDS = 5.0
# Generous because it includes grammar compilation, which is the point.
WARMUP_CALL_TIMEOUT = float(os.getenv("WARMUP_CALL_TIMEOUT", "600"))

# Same shape as the classifier's schema (a string constrained to an enum plus a
# number), so the grammar this compiles is representative of the real ones.
PROBE_SCHEMA = {
    "type": "object",
    "properties": {
        "الصنف_الفرعي": {"type": "string", "enum": ["حادث مرور", "حادث آخر"]},
        "نسبة_الثقة": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["الصنف_الفرعي", "نسبة_الثقة"],
}

PROBE_PROMPT = (
    "نص الحدث:\nاصطدام بين سيارتين على الطريق الوطنية دون إصابات.\n\n"
    "عنوان الحدث: حادث مرور\n\n"
    "صنّف نص الحدث أعلاه ضمن إحدى الفئات المتاحة فقط.\n"
    "الفئات المتاحة:\n- حادث مرور\n- حادث آخر\n\n"
    "أعد فقط كائن JSON بالصنف المختار ونسبة ثقة بين 0 و1."
)


def wait_for_model(deadline: float) -> str:
    """Poll /v1/models until the server lists one, and return its id.

    Reading the id back matters: vLLM serves exactly one model, and a mismatch
    between it and CLASSIFICATION_MODEL/EXTRACTION_MODEL fails every later call
    with a 404 that is much harder to read than this message.
    """
    last_error = None
    while time.monotonic() < deadline:
        try:
            resp = requests.get(f"{config.VLLM_HOST}/v1/models", timeout=10)
            resp.raise_for_status()
            served = [m["id"] for m in resp.json().get("data", [])]
            if served:
                return served[0]
            last_error = "server is up but serving no model"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        log(f"[warmup] waiting for {config.VLLM_HOST} ({last_error})")
        time.sleep(READY_POLL_SECONDS)
    raise TimeoutError(f"vLLM not ready after {READY_TIMEOUT:.0f}s; last error: {last_error}")


def main() -> int:
    started = time.monotonic()
    deadline = started + READY_TIMEOUT

    served_model = wait_for_model(deadline)
    log(f"[warmup] vLLM is serving {served_model} after {time.monotonic() - started:.0f}s")

    for configured in {config.CLASSIFICATION_MODEL, config.EXTRACTION_MODEL}:
        if configured != served_model:
            log(
                f"[warmup] WARNING: configured model {configured!r} is not the one "
                f"being served ({served_model!r}) — those calls will fail with 404"
            )

    payload = chat_payload(served_model, PROBE_PROMPT, PROBE_SCHEMA, max_tokens=64)
    call_started = time.monotonic()
    resp = requests.post(
        f"{config.VLLM_HOST}/v1/chat/completions", json=payload, timeout=WARMUP_CALL_TIMEOUT
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    log(
        f"[warmup] guided probe returned in {time.monotonic() - call_started:.1f}s: {content.strip()}"
    )
    log(f"[warmup] ready in {time.monotonic() - started:.0f}s total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
