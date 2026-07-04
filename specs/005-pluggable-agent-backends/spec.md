# Feature Specification: Pluggable Agent Backends

**Feature Branch**: `005-pluggable-agent-backends`

**Created**: 2026-06-24

**Status**: Draft

## User Scenarios & Testing

### User Story 1 — Select agent backend via Settings (Priority: P1)

The user opens the Settings Panel, navigates to the Agents tab, and sees the current active backend (default: Built-in Router). They can switch to a different backend from a list of installed options without restarting JARVIS and without editing any file.

**Why this priority**: The entire feature is gated on this UI entry point. Every other story depends on the ability to select a backend.

**Independent Test**: Can be fully tested by opening Settings → Agents, switching from "Built-in Router" to any other installed backend, sending a voice command, and verifying the response came through the selected backend (visible in the pipeline status log).

**Acceptance Scenarios**:

1. **Given** JARVIS is running with the default Built-in Router, **When** the user opens Settings → Agents, **Then** the tab shows "Built-in Router" as the active backend and a list of available backends.
2. **Given** the user selects a different installed backend, **When** they confirm, **Then** JARVIS switches to that backend immediately — the next voice command is processed by the new backend.
3. **Given** the user switches backends, **When** a voice command is in-flight, **Then** the switch waits for the current command to finish before taking effect.
4. **Given** a backend is selected but fails to initialise (e.g., service not running), **When** the failure is detected, **Then** JARVIS falls back to the Built-in Router and notifies the user via voice and the settings panel.

---

### User Story 2 — Connect an external agent backend (Priority: P1)

The user installs an external agent backend (such as a locally running service or a configured framework) and registers it in JARVIS through the Settings Panel by providing a name and connection details. No code changes are required.

**Why this priority**: This is the core value of the feature — enabling third-party frameworks without touching the codebase.

**Independent Test**: Can be tested by registering a new backend with a name and endpoint URL, selecting it as active, sending a command, and verifying the request reaches the registered endpoint.

**Acceptance Scenarios**:

1. **Given** the user clicks "Add Backend" in Settings → Agents, **When** they fill in the name and connection details, **Then** the backend appears in the available backends list.
2. **Given** a backend is registered, **When** the user clicks "Test Connection", **Then** JARVIS reports within 5 seconds whether the backend is reachable and functional.
3. **Given** a registered backend, **When** the user selects it as active and sends a voice command, **Then** the command is dispatched to that backend and the response is spoken back.
4. **Given** the user clicks "Remove" on a registered backend, **When** it is not the active backend, **Then** it is removed from the list immediately.
5. **Given** the user tries to remove the active backend, **When** they confirm, **Then** JARVIS reverts to the Built-in Router before removing it.

---

### User Story 3 — Per-backend configuration (Priority: P2)

Each registered backend has its own settings panel where the user can configure backend-specific options (e.g., endpoint URL, authentication, model overrides) — all through the interface.

**Why this priority**: Backends have different configuration requirements. Without per-backend settings, the feature is too rigid to be useful for real frameworks.

**Independent Test**: Can be tested by registering a backend, opening its settings, changing the endpoint URL, saving, and verifying the next request uses the updated URL.

**Acceptance Scenarios**:

1. **Given** a registered backend, **When** the user clicks the settings icon next to it, **Then** a panel opens showing that backend's configurable options.
2. **Given** the user changes a backend setting, **When** they save, **Then** the change takes effect for the next request without restarting JARVIS.
3. **Given** a required field is left empty, **When** the user tries to save, **Then** validation highlights the missing field and prevents saving.
4. **Given** credential fields (e.g., API token), **When** the user enters a value, **Then** it is stored in the OS keychain — never in plaintext.

---

### User Story 4 — Backend health monitoring (Priority: P2)

The Settings → Agents tab shows the live health status of each registered backend with a last-seen timestamp and error count. Users can spot unhealthy backends at a glance.

**Why this priority**: Multi-backend setups become unmanageable without visibility into which backends are working.

**Independent Test**: Can be tested by registering a backend, stopping its underlying service, and verifying the health indicator turns red within 30 seconds with an error description.

**Acceptance Scenarios**:

1. **Given** a backend is active and healthy, **When** the user opens Settings → Agents, **Then** a green indicator and "Connected" label appear next to it.
2. **Given** a backend becomes unreachable, **When** JARVIS next attempts to use it, **Then** the indicator turns red, an error message is shown, and JARVIS falls back to the Built-in Router.
3. **Given** a previously failed backend comes back online, **When** the user clicks "Retry", **Then** JARVIS re-checks the connection and updates the indicator.

---

### Edge Cases

- What if two backends have the same name? → Names must be unique; the interface prevents saving a duplicate name.
- What if the active backend hangs indefinitely on a request? → The existing circuit breaker and timeout mechanisms apply; JARVIS falls back to Built-in Router after the configured timeout.
- What if a backend returns a response in an unexpected format? → JARVIS logs the error, falls back to the Built-in Router for that request, and increments the backend's error count.
- What happens to in-flight requests when the user switches backends? → The switch is deferred until the current request completes; queued requests use the new backend.
- Can the Built-in Router be removed? → No. It is the permanent fallback and cannot be deleted or disabled.

---

## Requirements

### Functional Requirements

- **FR-001**: Users MUST be able to view, select, add, configure, and remove agent backends entirely through the Settings → Agents tab — no file editing required.
- **FR-002**: The Built-in Router MUST always be available as a fallback and cannot be removed.
- **FR-003**: Backend switching MUST take effect within one request cycle — no restart required.
- **FR-004**: Each external backend MUST be registered with at minimum: a display name and a connection endpoint.
- **FR-005**: Credential fields for backends MUST be stored in the OS keychain — never in plaintext files or the local database.
- **FR-006**: Users MUST be able to test a backend connection from the settings panel and receive a pass/fail result within 5 seconds.
- **FR-007**: When the active backend fails, JARVIS MUST automatically fall back to the Built-in Router and notify the user via voice and the settings panel.
- **FR-008**: Each backend MUST display a live health indicator (connected / degraded / disconnected) with a last-seen timestamp.
- **FR-009**: Backend-specific configuration changes MUST take effect without restarting JARVIS.
- **FR-010**: All backend dispatch events MUST emit structured audit log entries (backend name, latency, success/failure).
- **FR-011**: Backend names MUST be unique; the interface MUST prevent saving a duplicate name.
- **FR-012**: The active backend selection MUST persist across JARVIS restarts.

### Key Entities

- **AgentBackend**: A registered backend. Has a name (unique), type (built-in or external), connection endpoint, health status, error count, last-seen timestamp, and configuration blob.
- **BackendConfig**: Per-backend configuration key-value pairs. Sensitive values are stored in the OS keychain; non-sensitive values in the local database.
- **BackendHealthStatus**: Live status of a backend. Values: `connected` | `degraded` | `disconnected`.
- **BackendDispatchEvent**: An audit log entry for a request dispatched to a backend. Contains backend name, request ID, latency, and outcome.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can register, configure, and activate a new agent backend in under 2 minutes via the Settings panel.
- **SC-002**: Backend switching takes effect within one request cycle — the very next voice command uses the new backend.
- **SC-003**: When the active backend fails, JARVIS falls back to the Built-in Router and resumes normal operation within 3 seconds.
- **SC-004**: 100% of backend credential fields are stored in the OS keychain — a filesystem scan finds zero plaintext keys.
- **SC-005**: The health indicator reflects the true backend status within 30 seconds of a state change.
- **SC-006**: Zero JARVIS restarts are required for any backend management action (add, switch, configure, remove).

---

## Assumptions

- The initial set of supported external backends is OpenClaw, Hermes Agent, and LangGraph, plus the Built-in Router. Additional backends can be added by the community without modifying the core app.
- External backends expose a standard HTTP endpoint that JARVIS calls with the structured prompt and receives a text response — protocol details are determined during planning.
- The feature is opt-in: users who never open Settings → Agents continue using the Built-in Router with no change in behaviour.
- Backend health checks are lightweight polling — no persistent WebSocket connection required.
- The Built-in Router (Claude → GPT-4o → Gemini → Ollama fallback chain) remains unchanged; this feature adds an outer selection layer on top of it.
- Per-backend configuration forms are defined by backend type; the initial built-in types (OpenClaw, Hermes, LangGraph) ship with predefined forms; custom backends show a generic key-value editor.
