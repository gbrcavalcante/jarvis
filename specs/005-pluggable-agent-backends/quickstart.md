# Quickstart: Pluggable Agent Backends

Validation guide for feature 005. Proves the feature works end-to-end.

## Prerequisites

- JARVIS running (`uv run python -m src.main`)
- One external backend running locally (optional for scenarios 1–2)

---

## Scenario 1 — Default state: Built-in Router is active

**Goal**: Verify that a fresh install starts with the Built-in Router as the only backend.

```bash
curl http://127.0.0.1:37420/backends
```

**Expected**:
```json
{
  "backends": [
    {
      "name": "Built-in Router",
      "backend_type": "built_in",
      "is_active": true,
      "is_built_in": true,
      "health_status": "connected"
    }
  ],
  "active_backend": "Built-in Router"
}
```

---

## Scenario 2 — Register an external backend via API

**Goal**: Verify a backend can be registered and appears in the list.

```bash
curl -X POST http://127.0.0.1:37420/backends \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My OpenClaw",
    "backend_type": "openai_compatible",
    "base_url": "http://localhost:18789",
    "model_name": "openclaw",
    "api_key": "test-key"
  }'
```

**Expected**: HTTP 201, backend appears in `GET /backends`.

---

## Scenario 3 — Test connection before activating

**Goal**: Verify the test-connection flow returns a result within 5 seconds.

```bash
# Get the backend ID from the previous step
BACKEND_ID="<id from scenario 2>"

curl -X POST http://127.0.0.1:37420/backends/$BACKEND_ID/test
```

**Expected**: Response within 5 s. `ok: true` if OpenClaw is running, `ok: false` with error message if not.

---

## Scenario 4 — Switch active backend

**Goal**: Verify switching backends takes effect on the next request.

```bash
# Activate the registered backend
curl -X POST http://127.0.0.1:37420/backends/active \
  -H "Content-Type: application/json" \
  -d '{"id": "'$BACKEND_ID'"}'
```

**Expected**:
```json
{ "active_backend": "My OpenClaw", "effective_from": "next_request" }
```

Send a voice command and verify the audit log shows `backend_name: "My OpenClaw"`:

```bash
tail -f ~/.jarvis/jarvis.log | grep backend_dispatch
```

---

## Scenario 5 — Automatic fallback on backend failure

**Goal**: Verify JARVIS falls back to Built-in Router when the active backend goes down.

1. Set "My OpenClaw" as active (Scenario 4)
2. Stop OpenClaw
3. Send a voice command
4. **Expected**: JARVIS responds normally (via Built-in Router), emits a `backend_fallback` log event, and the settings panel shows "My OpenClaw" as `disconnected`

```bash
tail -f ~/.jarvis/jarvis.log | grep backend_fallback
```

---

## Scenario 6 — Remove the Built-in Router (should fail)

**Goal**: Verify the built-in backend cannot be deleted.

```bash
# Get the Built-in Router ID
BUILTIN_ID=$(curl -s http://127.0.0.1:37420/backends | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(next(b['id'] for b in data['backends'] if b['is_built_in']))
")

curl -X DELETE http://127.0.0.1:37420/backends/$BUILTIN_ID
```

**Expected**: HTTP 400 — `"The Built-in Router cannot be deleted."`

---

## Scenario 7 — Settings Panel UI

**Goal**: Verify the full UI flow works without touching the API.

1. Open JARVIS tray → Settings → Agents tab
2. Verify "Built-in Router" shows as active with a green indicator
3. Click "Add Backend" → fill in name, URL, model, API key → Save
4. Click "Test Connection" → verify result shown within 5 s
5. Click the new backend → "Set as Active"
6. Send a voice command → verify it routes through the new backend
7. Click the backend → "Remove" → verify it disappears and Built-in Router becomes active

---

## Scenario 8 — Health monitoring

**Goal**: Verify the health indicator updates within 30 seconds of a state change.

1. Register and activate an external backend
2. Stop the backend service
3. Wait up to 30 seconds
4. Open Settings → Agents
5. **Expected**: Backend shows red indicator + `disconnected` status + error count > 0
