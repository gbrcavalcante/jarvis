# Quickstart: Obsidian Memory

Validation guide for feature 004. Proves the feature works end-to-end.

## Prerequisites

- JARVIS running (`uv run python -m src.main`)
- An empty (or existing) folder to use as a test vault, e.g. `/tmp/test-vault`

---

## Scenario 1 — No vault configured (default state)

```bash
curl http://127.0.0.1:37420/vault/status
```

**Expected**: `{"connected": false, "path": null, "note_count": 0, "last_indexed_at": null}`

---

## Scenario 2 — Connect a vault

```bash
mkdir -p /tmp/test-vault
curl -X POST http://127.0.0.1:37420/vault/connect \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/test-vault"}'
```

**Expected**: HTTP 200, `connected: true`. A `_jarvis/` subfolder now exists inside `/tmp/test-vault`.

```bash
ls /tmp/test-vault/_jarvis
```

---

## Scenario 3 — Reject the JARVIS project directory as a vault

```bash
curl -X POST http://127.0.0.1:37420/vault/connect \
  -H "Content-Type: application/json" \
  -d '{"path": "'"$(pwd)"'"}'
```

**Expected**: HTTP 409 — vault must be a separate folder.

---

## Scenario 4 — Vault search injects context into a response

```bash
mkdir -p /tmp/test-vault/Projects
cat > /tmp/test-vault/Projects/jarvis.md <<'EOF'
# jarvis

JARVIS is a voice-first AI assistant with hot-swappable agent backends.
EOF

curl -X POST http://127.0.0.1:37420/voice/command \
  -H "Content-Type: application/json" \
  -d '{"text": "What is JARVIS?"}'
```

**Expected**: `response` field demonstrates awareness of the note's content
(references "voice-first" or "hot-swappable agent backends").

Check the audit log to confirm the vault was searched:
```bash
tail -f ~/.jarvis/jarvis.log | grep vault_search
```

---

## Scenario 5 — Knowledge written at session end

Send a command expressing a preference:

```bash
curl -X POST http://127.0.0.1:37420/voice/command \
  -H "Content-Type: application/json" \
  -d '{"text": "I prefer dark mode for the settings panel"}'
```

**Expected**: after the session ends, a new/updated file appears:

```bash
cat /tmp/test-vault/_jarvis/knowledge/*.md
```

It contains a structured summary of the preference — **not** the literal transcript text.

---

## Scenario 6 — Graph View reflects linked notes

```bash
cat > /tmp/test-vault/Projects/voice-ui.md <<'EOF'
# voice-ui

See [[jarvis]] for the parent project.
EOF

curl -s http://127.0.0.1:37420/vault/graph | python3 -m json.tool
```

**Expected**: two nodes (`jarvis`, `voice-ui`) with one edge connecting them.

1. Open JARVIS tray → Settings → Memory tab → "Open Graph View"
2. Verify both notes appear as connected nodes
3. Click the `jarvis` node → verify its content shows in the side panel

---

## Scenario 7 — Vault becomes unavailable mid-session

```bash
mv /tmp/test-vault /tmp/test-vault-moved

curl -X POST http://127.0.0.1:37420/voice/command \
  -H "Content-Type: application/json" \
  -d '{"text": "hello"}'
```

**Expected**: HTTP 200 — JARVIS responds normally (falls back to
`user_profile.md`), no crash. Audit log shows a `vault_unavailable` warning.

```bash
tail -f ~/.jarvis/jarvis.log | grep vault_unavailable
mv /tmp/test-vault-moved /tmp/test-vault   # restore for further testing
```

---

## Scenario 8 — Disconnect the vault

```bash
curl -X POST http://127.0.0.1:37420/vault/disconnect
curl http://127.0.0.1:37420/vault/status
```

**Expected**: `connected: false`. Subsequent voice commands no longer inject
vault context; JARVIS uses `user_profile.md` only.
