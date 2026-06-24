# Feature Specification: Settings & Configuration Module

**Feature Branch**: `003-add-settings-config`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Add the Settings & Configuration module to JARVIS."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - First-Run Wizard (Priority: P1)

A brand-new user opens JARVIS for the first time. A guided wizard walks them through the minimum setup required to start using the assistant: choose a provider, connect credentials, pick a hotword, and choose a voice. After completing the wizard, JARVIS is fully functional.

**Why this priority**: Without completing initial setup, the user cannot use JARVIS at all. This is the highest-friction moment in the product — a poor onboarding experience blocks all other features.

**Independent Test**: Can be tested end-to-end by launching JARVIS on a fresh config, completing all five wizard steps, and verifying the assistant responds to the hotword. Delivers a fully operational assistant as standalone value.

**Acceptance Scenarios**:

1. **Given** JARVIS has no existing configuration, **When** the user launches JARVIS, **Then** the first-run wizard opens automatically on the Welcome screen.
2. **Given** the user is on the Provider step, **When** they select a provider and enter credentials, **Then** a "Test Connection" validation runs and must succeed before they can advance.
3. **Given** the user is on the Hotword step, **When** they select a hotword option and click "Test Hotword", **Then** they can speak into the microphone and receive immediate feedback on whether the hotword was detected.
4. **Given** the user is on the Voice step, **When** they click "Test Voice", **Then** JARVIS speaks a sample sentence using the selected voice settings.
5. **Given** all wizard steps are complete, **When** the user clicks "Done", **Then** configuration is persisted and the assistant is immediately usable — no restart required.
6. **Given** the user quits the wizard before finishing, **When** they reopen JARVIS, **Then** the wizard resumes at the last incomplete step.

---

### User Story 2 - Provider & Authentication Management (Priority: P1)

An existing user wants to switch from Claude Code to GPT-4o because their Claude credits ran out. They open Settings from the system tray, navigate to Provider & Authentication, select GPT-4o, paste their OpenAI API key, test the connection, and save. JARVIS immediately uses the new provider.

**Why this priority**: Provider connectivity is the core dependency for all AI functionality. A broken or misconfigured provider makes JARVIS unusable. Users need reliable, verifiable credential management.

**Independent Test**: Can be tested by switching providers and confirming the assistant routes requests to the newly selected provider. Delivers reliable credential management as standalone value.

**Acceptance Scenarios**:

1. **Given** the Settings panel is open, **When** the user navigates to Provider & Authentication, **Then** they see their currently active provider highlighted and all available providers listed.
2. **Given** the user selects a provider requiring an API key, **When** they paste the key and click "Test Connection", **Then** JARVIS validates the key against the provider and shows a success or failure message before any save occurs.
3. **Given** the user selects a provider supporting OAuth 2.0, **When** they initiate the OAuth flow, **Then** a browser window opens for authorization and credentials are stored automatically upon successful callback — no manual key entry required.
4. **Given** credentials are saved, **When** the user closes Settings, **Then** the credential is stored in the OS keychain — never written in plain text to disk.
5. **Given** the user changes providers, **When** the change is saved, **Then** all other settings (hotword, voice, theme) remain unchanged.
6. **Given** "Test Connection" fails, **When** the user attempts to save, **Then** the save is blocked and the user sees a specific error message explaining why the connection failed.

---

### User Story 3 - Voice & Hotword Configuration (Priority: P2)

A user finds the default hotword "Hey Jarvis" awkward and prefers "Computer". They also want a slower speech rate in Brazilian Portuguese. They open Settings, update the hotword, test it, adjust the voice settings, hear a preview, and save.

**Why this priority**: Voice interaction is JARVIS's primary interface. Poor hotword sensitivity or an uncomfortable voice makes the product hard to use daily, reducing retention.

**Independent Test**: Can be tested by changing hotword to "Computer", speaking it, and confirming detection. Voice changes tested via the "Test Voice" button. Delivers an improved voice interaction experience independently.

**Acceptance Scenarios**:

1. **Given** the Hotword section is open, **When** the user selects "Computer" from the preset list, **Then** the custom hotword field is cleared and the sensitivity slider resets to medium.
2. **Given** the user types a custom hotword phrase, **When** they click "Test Hotword" and speak the phrase, **Then** visual feedback indicates whether detection succeeded.
3. **Given** the sensitivity slider is at "high", **When** the user speaks near the microphone at low volume, **Then** the hotword is still detected — and if at "low", only clear close-range speech triggers it.
4. **Given** the user selects voice gender "Female", language "pt-BR", and rate "slow", **When** they click "Test Voice", **Then** they hear a sample sentence in that voice configuration immediately, before saving.
5. **Given** voice changes are saved, **When** JARVIS next responds to a request, **Then** it uses the newly configured voice settings.

---

### User Story 4 - Fallback & Notification Behavior (Priority: P2)

A power user who runs Ollama locally wants JARVIS to automatically retry on Ollama if Claude Code fails, with no voice interruption. Another user wants to be asked what to do instead. Both scenarios must be configurable.

**Why this priority**: Fallback behavior directly affects reliability and user trust. Incorrect defaults will frustrate users when their primary provider fails.

**Independent Test**: Testable by simulating a provider failure and verifying the system either auto-retries silently or prompts the user based on the toggle state.

**Acceptance Scenarios**:

1. **Given** "Auto-fallback to Ollama" is OFF, **When** the active agent fails, **Then** JARVIS notifies the user by voice with the message and offers three choices: try Ollama, retry, or cancel.
2. **Given** "Auto-fallback to Ollama" is ON, **When** the active agent fails, **Then** JARVIS silently retries on Ollama with no voice notification.
3. **Given** the notification preference is "popup only", **When** a failure occurs, **Then** a system notification popup appears — no voice output.
4. **Given** the notification preference is "both", **When** a failure occurs, **Then** both voice and popup notifications are triggered simultaneously.
5. **Given** the user changes the fallback toggle, **When** the change is saved, **Then** the new behavior takes effect on the next agent invocation — no restart required.

---

### User Story 5 - Skills & MCP Management (Priority: P3)

A user wants to add a new skill called "web-search" to their Claude Code agent, and also connect a new MCP server for their local file system. They open Settings, navigate to Skills, install the skill, then go to MCP Manager, add the MCP URL, and authenticate it.

**Why this priority**: Skills and MCPs extend JARVIS's capabilities. However, they require a working provider first (US2), so they are lower priority.

**Independent Test**: Testable by installing a skill and confirming it appears in the skills list; connecting an MCP and confirming it shows as connected. Each can be tested independently of the other.

**Acceptance Scenarios**:

1. **Given** the Skills section is open, **When** the user enters a skill name and clicks "Install", **Then** the skill is added to the active agent's skills directory and appears in the installed list within 10 seconds.
2. **Given** a skill is installed, **When** the user clicks "Remove" and confirms the dialog, **Then** the skill is deleted and no longer appears in the list.
3. **Given** the MCP Manager section is open, **When** the user enters an MCP URL and initiates connection, **Then** JARVIS prompts for authentication (OAuth or API key) and shows connection status upon completion.
4. **Given** an MCP is connected, **When** the user clicks "Disconnect" and confirms, **Then** the MCP is removed from the active agent's configuration.
5. **Given** the user installs or removes a skill, **When** the change is saved, **Then** the active agent's skill directory reflects the change without requiring a JARVIS restart.

---

### User Story 6 - Memory & Permissions Oversight (Priority: P3)

A privacy-conscious user wants to review what memory JARVIS has accumulated and clear session memory without deleting their user profile. They also want to see which permissions have been granted to the agent.

**Why this priority**: Trust and privacy are non-negotiable for an always-on assistant. Users need visibility and control over what the assistant remembers and can access.

**Independent Test**: Testable by reviewing the memory summary display, clicking "Clear session memory", and confirming the session count resets. Permission list visibility is independently verifiable.

**Acceptance Scenarios**:

1. **Given** the Memory section is open, **When** the page loads, **Then** the user sees a human-readable summary of their user profile and the current session count and storage size.
2. **Given** the user clicks "Clear session memory", **When** they confirm the action, **Then** all claude-mem sessions are deleted and the session count resets to zero.
3. **Given** the user clicks "Clear user profile", **When** they confirm the confirmation dialog explicitly stating data will be permanently lost, **Then** the user_profile.md is deleted.
4. **Given** the user clicks "Export memory", **When** the export completes, **Then** a ZIP file containing all memory files is saved to a user-chosen location.
5. **Given** the Permissions section is open, **When** the page loads, **Then** the agent's current whitelist and blacklist are displayed in a read-only list.
6. **Given** "Ask before any new permission request" is ON, **When** the agent requests a new permission at runtime, **Then** JARVIS prompts the user before granting it.

---

### User Story 7 - Dashboard & Budget Tracking (Priority: P3)

A cost-conscious user wants to see how much they've spent on tokens this month and set a daily cap of $2.00 so they don't accidentally over-spend. They also want to be notified by voice when 80% of the cap is reached.

**Why this priority**: Cost visibility is important for trust, especially for users running expensive cloud providers. However, the assistant must be functional before budget tracking matters.

**Independent Test**: Testable by reviewing the usage dashboard with mock data and setting a budget cap with an alert threshold. Verifiable without any AI provider being active.

**Acceptance Scenarios**:

1. **Given** the Dashboard section is open, **When** it loads, **Then** the user sees token usage broken down by today, this week, and this month — with a cost estimate per active provider.
2. **Given** the user has Ollama routing enabled, **When** the dashboard loads, **Then** a "Savings from local routing" figure is displayed showing the estimated cost difference vs. using only cloud providers.
3. **Given** the user sets a daily cap of $2.00 and an alert at 80%, **When** usage reaches $1.60, **Then** JARVIS announces by voice "You've used 80% of your daily budget."
4. **Given** the daily cap is set and usage reaches the cap, **When** the next request would exceed it, **Then** JARVIS pauses auto-execution and notifies the user rather than proceeding silently.
5. **Given** the budget cap is set to a specific value, **When** the user saves and reopens Settings, **Then** the same cap value is displayed — it persisted correctly.

---

### Edge Cases

- What happens when the OS keychain is unavailable (e.g., no keyring daemon running on Linux)?
- How does the system behave if the user closes the first-run wizard mid-flow and the config is partially written?
- What if an installed skill has the same name as an existing one — overwrite or reject?
- What if the MCP URL is unreachable during connection — timeout behavior?
- What if the user sets a hotword that is a very common word (e.g., "the") — any warning?
- What if token usage data is unavailable for a provider that doesn't expose usage APIs?
- What if "Clear user profile" is clicked during an active JARVIS session — does it take effect immediately or on next start?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a Settings panel accessible from the system tray icon via right-click.
- **FR-002**: The system MUST present a first-run wizard on initial launch when no configuration exists.
- **FR-003**: The system MUST support at least three AI providers: Claude Code, GPT-4o, and Ollama; additional providers may be added later.
- **FR-004**: The system MUST validate provider credentials via a "Test Connection" action before persisting them.
- **FR-005**: The system MUST support both API key and OAuth 2.0 as authentication methods, depending on the provider.
- **FR-006**: All credentials MUST be stored in the OS keychain — never in plain text on disk.
- **FR-007**: The system MUST persist all non-sensitive settings to a user-owned configuration file at a well-known location in the user's home directory.
- **FR-008**: The system MUST provide a hotword picker with at least three preset options and a free-text custom option.
- **FR-009**: The system MUST provide a "Test Hotword" function that gives live feedback on whether the hotword was detected.
- **FR-010**: The system MUST provide a "Test Voice" function that speaks a sample sentence using the currently selected voice settings before the user saves.
- **FR-011**: The system MUST allow the user to toggle automatic fallback to a local provider on agent failure.
- **FR-012**: When auto-fallback is OFF and an agent fails, the system MUST notify the user by voice and offer at minimum three options: retry, fallback, or cancel.
- **FR-013**: The system MUST allow the user to configure notification delivery: voice only, popup only, or both.
- **FR-014**: The system MUST display a read-only list of permissions currently granted to the active agent.
- **FR-015**: The system MUST allow the user to install and remove skills for the active agent.
- **FR-016**: The system MUST allow the user to connect and disconnect MCP servers for the active agent.
- **FR-017**: The system MUST display memory usage summary (session count, storage size, user profile overview).
- **FR-018**: The system MUST provide a "Clear session memory" action that destroys all session data after explicit confirmation.
- **FR-019**: The system MUST provide a "Clear user profile" action that destroys the user profile after explicit double-confirmation (due to irreversibility).
- **FR-020**: The system MUST provide an "Export memory" action that saves all memory data as a compressed archive to a user-chosen location.
- **FR-021**: The system MUST display token usage and cost estimates broken down by time period (today, week, month) and by provider.
- **FR-022**: The system MUST allow the user to set a daily budget cap and an alert threshold (as a percentage of the cap).
- **FR-023**: When the alert threshold is reached, the system MUST notify the user by the configured notification method.
- **FR-024**: When the daily cap is reached, the system MUST pause auto-execution and notify the user rather than silently failing.
- **FR-025**: All Settings sections MUST be keyboard-navigable (full tab order, no mouse required).
- **FR-026**: The Settings panel MUST respect the user's system theme (light/dark) by default, with a manual override option.
- **FR-027**: All setting changes MUST be validated before being persisted — no partial or inconsistent configurations allowed.

### Key Entities

- **Configuration**: The complete set of user preferences persisted between sessions. Contains provider selection, voice settings, hotword settings, UI preferences, fallback behavior, and budget parameters. Does not contain credentials.
- **Credential**: A provider-specific authentication artifact (API key or OAuth token). Stored exclusively in the OS keychain, never in the configuration file.
- **Provider**: A connected AI service or local model. Has an identity, an authentication method, a connection status, and routing priority.
- **Skill**: A named capability extension installed into the active agent's skills directory. Has a name, source, and installation status.
- **MCP Connection**: A configured connection to a Model Context Protocol server. Has a URL, authentication method, and connection status.
- **MemorySnapshot**: A point-in-time summary of session count, storage size, and user profile existence — used for display in the Memory section.
- **UsageRecord**: A time-bucketed (day/week/month) record of token consumption and estimated cost per provider.
- **BudgetPolicy**: The user's configured daily cap and alert threshold, applied to control spending at runtime.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user completes the full onboarding wizard and has a functioning assistant in under 3 minutes.
- **SC-002**: All credential operations (save, update, delete) leave no plain-text secrets in any file on disk — verifiable by scanning the config directory.
- **SC-003**: Provider switching takes effect on the next assistant invocation — no restart required.
- **SC-004**: The hotword test gives a response (detected or not detected) within 5 seconds of the user speaking.
- **SC-005**: The voice preview plays within 2 seconds of the user clicking "Test Voice."
- **SC-006**: "Clear session memory" completes within 3 seconds for up to 500 stored sessions.
- **SC-007**: The usage dashboard loads and displays accurate data within 2 seconds of the section being opened.
- **SC-008**: When the budget alert threshold is reached, the notification fires within 1 second of the triggering request completing.
- **SC-009**: 90% of Settings tasks (change a setting, save, verify it persisted) are completable via keyboard alone — no mouse required.
- **SC-010**: All Settings sections load on first click within 1 second on standard hardware.

## Assumptions

- A user is assumed to have exactly one "active agent" at any time; multi-agent orchestration is out of scope for this spec.
- The OS keychain is assumed to be available on all supported platforms (Linux: libsecret/keyring, macOS: Keychain, Windows: Credential Manager). A graceful degradation path when the keychain is unavailable is required but the specific fallback behavior is out of scope for this spec.
- OAuth 2.0 callback handling via a local server (localhost) is assumed to be feasible on all target platforms.
- The Ollama provider is assumed to be installed separately by the user; JARVIS does not install it.
- Token usage data is displayed only for providers that expose a usage API; providers without usage APIs show "Usage data unavailable."
- Supabase login and cloud sync are explicitly out of scope (separate spec).
- Remote or multi-device settings sync is out of scope for this version.
- Team and multi-user features are out of scope for this version.
- The first-run wizard state is tracked via a flag in the configuration file; if the file is deleted, the wizard reappears.
