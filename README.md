# Morour Traffic Events

React + TypeScript + Vite dashboard over a FastAPI + Postgres backend, with an
vLLM-backed worker that classifies and extracts structured fields from
incoming traffic events.

## Running with Docker

```bash
cp .env.example .env    # then edit it
docker compose up --build
```

| Service  | What it is                              | URL                     |
|----------|-----------------------------------------|-------------------------|
| `web`    | Dashboard (Vite build behind nginx)     | http://localhost:5173   |
| `api`    | FastAPI                                 | http://localhost:9911   |
| `worker` | Classify + extract loop                 | —                       |
| `proxy`  | Forwarder to the source events API      | localhost:8004          |
| `vllm`   | Inference server (Qwen3-8B-AWQ)        | http://localhost:8000   |
| `warmup` | One-shot model warm-up, then exits      | —                       |
| `db`     | Postgres 16                             | localhost:5432          |

Only Postgres, with `api`/`worker` run natively:

```bash
docker compose -f docker-compose.db.yml up -d
```

`VITE_API_BASE_URL` is baked into the JS bundle at build time, so rebuild the
web image (`docker compose build web`) after changing it.

### Inference (vLLM)

`vllm` serves **`Qwen/Qwen3-8B-AWQ`** through an OpenAI-compatible API and needs
an NVIDIA GPU with working container passthrough. Check yours with:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

**VRAM budgeting.** `--gpu-memory-utilization` is a fraction of *total* VRAM, not
an absolute. The default `0.85` targets ~13.9GB on a 16GB card (RTX 5060 Ti),
which holds the int4 weights (~5.7GB) plus KV cache. Recalculate it for a different card or
model — `VLLM_MODEL`, `VLLM_GPU_FRACTION` and `VLLM_MAX_MODEL_LEN` are all env
vars, and `.env.example` lists the models that fit a 16GB card.

vLLM serves **one model per process**, so `VLLM_MODEL` is injected as both
`CLASSIFICATION_MODEL` and `EXTRACTION_MODEL`; they cannot drift apart. Serving
two different models means running a second `vllm` container and splitting VRAM.

**Thinking must stay off.** Qwen3 is a hybrid reasoning model, and its `<think>`
blocks are not valid under the JSON schemas used for guided decoding. Every call
sends `chat_template_kwargs: {enable_thinking: false}`. `VLLM_ENABLE_THINKING`
exists for debugging only — turning it on will corrupt the extraction output.

**First start is slow**: the weights (~6GB) download from HuggingFace, then load.
They're cached in the `hf_cache` volume, so later starts only pay the load. The
healthcheck allows 30 minutes for this before it starts counting failures.

### Warm-up

`/health` goes green once weights are loaded, but the first *schema-guided*
request still pays a one-off cost the healthcheck never triggers: xgrammar
compiling the JSON schema into a grammar. On an 8B that can take tens of
seconds, which would otherwise land on the worker's first real event and look
like a hang.

The `warmup` service runs once, waits for the model, fires one guided request
shaped like the real classifier call, and exits. `api` and `worker` gate on
`service_completed_successfully`, so they never start against a cold model.
Run it by hand with:

```bash
docker compose run --rm warmup
```

### Verifying vLLM on a new machine

The inference path has been verified against a stub server (request shape, JSON
parsing, SSE streaming, warm-up gating, worker cycle) but **not against real
weights on a GPU**. On the deployment machine, check these in order:

```bash
# 1. GPU passthrough works at all
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi

# 2. Start just the model server and watch it load (several minutes; the first
#    run also downloads ~6GB)
docker compose up vllm

# 3. It reports the model it is serving
curl -s http://localhost:8000/v1/models | jq .

# 4. Warm-up completes — this is the real test of schema-guided decoding
docker compose run --rm warmup

# 5. Whole stack
docker compose up -d
docker compose logs -f worker
```

Things most likely to need adjusting:

- **`VLLM_GPU_FRACTION`** is arithmetic, not measured. If vLLM OOMs on startup,
  lower it; if `nvidia-smi` shows lots of VRAM idle, raise it for more KV cache.
- **`VLLM_TIMEOUT=300`** is a guess at 8B latency. Watch the `elapsed=` field in
  the `[vllm]` log lines and adjust.
- **`finish_reason=length`** in those logs means `VLLM_MAX_TOKENS` is cutting
  generation off mid-JSON — raise it.
- **Extraction quality** is the one thing no automated check covers. Compare a
  few `[extract]` results against the source Arabic text before trusting them.

### Source API proxy

`API_BASE_URL` points at `172.19.0.37:8003`. That address falls inside Docker's
own default bridge pool (`172.17.0.0/16`–`172.31.0.0/16`), so a container whose
network sits in that range resolves it to a peer on its own bridge instead of
routing it out to the real host. The `proxy` service (`proxy.py`, a plain TCP
forwarder) sidesteps this: `api`/`worker` talk to `proxy:8004`, which forwards
to `PROXY_TARGET_HOST:PROXY_TARGET_PORT`.

Two layers keep that route clear:

1. **Per-project (already applied).** `docker-compose.yml` pins this stack's
   network to `10.201.0.0/24`, so its containers never claim `172.19.x`.
   Routing is per-container, so this alone is normally enough.

2. **Machine-wide (optional).** If you still can't reach the source API — other
   Docker networks on the host can affect NAT egress — move Docker off the
   colliding range entirely. Add to `~/.docker/daemon.json` (Docker Desktop:
   Settings -> Docker Engine):

   ```json
   { "default-address-pools": [ { "base": "10.201.0.0/16", "size": 24 } ] }
   ```

   Then restart Docker and run `docker network prune`. Existing networks keep
   their old subnets, so the prune is what actually applies the change.

---

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
