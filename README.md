# Morour Traffic Events

React + TypeScript + Vite dashboard over a FastAPI + Postgres backend, with an
Ollama-backed worker that classifies and extracts structured fields from
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
| `db`     | Postgres 16                             | localhost:5432          |

Only Postgres, with `api`/`worker` run natively:

```bash
docker compose -f docker-compose.db.yml up -d
```

`VITE_API_BASE_URL` is baked into the JS bundle at build time, so rebuild the
web image (`docker compose build web`) after changing it.

Ollama is deliberately **not** containerized — it wants your host GPU. The
`api`/`worker` containers reach it at `host.docker.internal:11434`.

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
