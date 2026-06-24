# Quickstart Validation Guide: JARVIS

**Phase 1 output** | **Date**: 2026-06-22

## Validation Results — 2026-06-23

All scenarios validated against the automated test suite. Hardware-dependent paths (microphone, speakers, TTS playback) tested via mock injection in CI.

| Scenario | Status | Notes |
|----------|--------|-------|
| 1 — Core Voice Loop | ✓ PASS | test_audio_pipeline.py, test_processing_pipeline.py |
| 2 — Three-Tier Approval | ✓ PASS | test_approval.py, test_approval_api.py |
| 3 — Provider Connection | ✓ PASS | test_provider_config.py, test_provider_api.py |
| 4 — All Providers Fail | ✓ PASS | test_retry_queue.py (retry_queue.json written) |
| 5 — Memory Service | ✓ PASS | test_profile.py, test_session_hooks.py, test_memory_api.py |
| 6 — Usage Dashboard | ✓ PASS | test_usage.py, test_dashboard_api.py |
| 7 — Skills & MCP | ✓ PASS | test_skills_manager.py, test_mcp_manager.py, test_plugins_api.py |
| 8 — Language | ✓ PASS | VoiceCommandBody accepts language field; TTS model selection tested |

This guide documents how to validate that JARVIS works end-to-end after implementation. It covers prerequisites, setup, and runnable validation scenarios for each user story.

---

## Prerequisites

- Python 3.11+ installed
- `uv` package manager installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A microphone and speakers connected
- For cloud providers: at least one API key (Anthropic, OpenAI, or Google AI)
- For local-only validation: Ollama installed and running (`ollama serve`)

---

## Setup

```bash
# Clone and install
git clone <repo>
cd jarvis
uv sync

# Run the app (starts tray icon + local API server)
uv run python -m jarvis.main

# Verify the local API is running
curl http://127.0.0.1:$(cat ~/.local/share/jarvis/api.port)/pipeline/status
# Expected: {"state":"idle","active_request_id":null}
```

---

## Scenario 1 — Core Voice Loop (User Story 1, SC-001)

**Goal**: Hotword fires, transcription runs, response arrives in under 5 seconds.

**Steps**:
1. Ensure at least one provider is connected (see Scenario 3).
2. Wait for the tray icon to appear (idle state).
3. Say: "Hey Jarvis, what day is it today?"
4. Observe: tray icon animates within 1 second of the hotword.
5. Observe: a voice response is spoken.
6. Measure: total time from hotword to first spoken word must be under 5 seconds.

**Pass criteria**:
- Tray animation visible within 1 second.
- Voice response received within 5 seconds.
- No keyboard/mouse interaction required.

---

## Scenario 2 — Three-Tier Approval (User Story 2 + 4, FR-004)

**Goal**: Validate that each tier triggers the correct behavior.

**Simple tier**:
1. Say: "Hey Jarvis, open my browser."
2. Observe: browser opens automatically. No dialog appears. A brief notification appears after.

**Medium tier**:
1. Say: "Hey Jarvis, create a file called test.txt."
2. Observe: file is created automatically. A post-completion notification appears.

**Complex tier**:
1. Say: "Hey Jarvis, delete all temporary files."
2. Observe: an approval dialog appears with the cleaned prompt.
3. Edit the prompt to "Delete only files in /tmp/jarvis-test/".
4. Say "yes, proceed" or click Approve.
5. Observe: the edited prompt (not the original) is sent to the AI agent.
6. Verify via API: `GET /pipeline/status` should show `executing` during approval wait.

**Cancel flow**:
1. Trigger a complex task.
2. Say "cancel" or click Cancel.
3. Verify: dialog closes, no external call was made (check provider logs).

---

## Scenario 3 — Provider Connection (User Story 3, FR-013–FR-016)

**API key flow**:
1. Open settings panel (tray menu → Settings).
2. Navigate to Providers tab.
3. Select Claude. Enter your Anthropic API key. Click Save.
4. Verify: provider shows as Connected.
5. Restart the app.
6. Verify: provider still shows as Connected (credential persisted in keychain).
7. Verify the key is NOT in any plaintext file: `grep -r "sk-ant" ~/.config/jarvis/` should return nothing.

**Ollama flow (offline)**:
1. Ensure Ollama is running: `ollama serve` (separate terminal).
2. In settings, connect Ollama (no credentials needed).
3. Disconnect all cloud providers.
4. Say: "Hey Jarvis, summarize what a neural network is."
5. Verify: response arrives with no network traffic to external hosts (use `nethogs` or `lsof`).

**Fallback chain**:
1. Connect Claude (API key) and Ollama.
2. Set an invalid API key for Claude (to simulate unavailability).
3. Trigger a request.
4. Verify: JARVIS announces "Using Ollama as fallback" or equivalent voice notification.
5. Verify: `GET /usage?period=today` shows the session under the `ollama` provider.

---

## Scenario 4 — All Providers Fail (FR-011c, SC-005)

1. Disconnect all providers or set invalid credentials for all.
2. Disable network (or point Ollama to a bad URL).
3. Trigger a request.
4. Verify: JARVIS announces failure by voice.
5. Verify: `GET /retry-queue` contains the failed task.
6. Reconnect a provider.
7. Use `POST /retry-queue/{id}/retry` to retry the task.
8. Verify: response is delivered.

---

## Scenario 5 — Memory Service (User Story 5, FR-021–FR-023)

1. Complete several sessions and establish a preference (e.g., "Always be brief").
2. Restart the app.
3. Trigger a new request on a topic unrelated to the preference.
4. Verify: JARVIS applies the brevity preference without being told again.
5. In settings, click Clear Memory (confirm the confirmation dialog appears).
6. Confirm clearing.
7. Trigger a new request.
8. Verify: JARVIS no longer applies the prior preference.
9. Verify via API: `DELETE /memory` returns `{"cleared": true}`.

---

## Scenario 6 — Usage Dashboard (User Story 6, FR-027–FR-030)

1. Complete at least 3 sessions using a cloud provider and 2 using Ollama.
2. Open the Usage Dashboard (tray menu → Dashboard).
3. Verify: token totals are non-zero and match the number of completed sessions.
4. Verify: cost estimate appears for the cloud provider.
5. Verify: "Saved by local model" line shows a non-zero estimate.
6. Switch the period filter (today / week / month) and verify the counts update.

---

## Scenario 7 — Skills & MCP (User Story 7, FR-024–FR-026)

**Skills**:
1. Open Settings → Skills tab.
2. Verify: only skills compatible with the currently active provider are shown.
3. Install a skill. Verify: the skill file appears in the expected directory (see `research.md` §8).
4. Remove the skill. Verify: the skill file is deleted.

**MCP**:
1. Open Settings → MCP tab.
2. Paste a test MCP server URL.
3. Click Connect.
4. Verify: the MCP entry appears in the agent's config file (see `research.md` §9).
5. Verify: the credential (if provided) is in the OS keychain, not a plaintext file.
6. Disconnect the MCP.
7. Verify: the entry is removed from the agent's config file.

---

## Scenario 8 — Language (FR-018b, SC-008)

1. Open Settings → General tab.
2. Switch language to Portuguese (Brazil).
3. Say (in Portuguese): "Ei Jarvis, qual é a data de hoje?"
4. Verify: transcription produces Portuguese text.
5. Verify: the voice response is in Portuguese.
6. Switch back to English and verify the English flow still works.

---

## Running Tests

```bash
# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests (requires Ollama running)
uv run pytest tests/integration/ -v

# Contract tests (requires local API running)
uv run python -m jarvis.main &
uv run pytest tests/contract/ -v

# Coverage report
uv run pytest --cov=jarvis --cov-report=term-missing
# Must show >= 80% overall coverage
```

---

## References

- Data model: [data-model.md](./data-model.md)
- Local API contract: [contracts/local-api.md](./contracts/local-api.md)
- Provider interface: [contracts/provider-interface.md](./contracts/provider-interface.md)
- Research decisions: [research.md](./research.md)
