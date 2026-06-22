# Feature Specification: JARVIS — Voice-First AI Assistant for Desktop

**Feature Branch**: `001-jarvis-voice-assistant`

**Created**: 2026-06-22

**Status**: Clarified

**Input**: User description: "Build JARVIS — a commercial voice-first AI assistant for desktop."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Core Voice Interaction Loop (Priority: P1)

A user speaks the hotword "Hey Jarvis," JARVIS activates, the user speaks a natural-language request, and JARVIS responds with a voice reply. The entire flow completes without the user touching the keyboard or mouse.

**Why this priority**: This is the defining capability of JARVIS. Without it, the product does not exist. Every other story builds on this loop.

**Independent Test**: Can be fully tested by launching the app, speaking the hotword, asking a simple factual question (e.g., "What time is it?"), and confirming a voice response is received within 5 seconds. Delivers the core product promise in isolation.

**Acceptance Scenarios**:

1. **Given** the app is running in the background, **When** the user says "Hey Jarvis," **Then** the tray icon animates to indicate listening and the microphone activates within 1 second.
2. **Given** JARVIS is listening, **When** the user speaks a request and pauses, **Then** the speech is transcribed locally and a response is spoken aloud.
3. **Given** JARVIS is listening, **When** the user stays silent for 5 seconds, **Then** the assistant deactivates and the tray icon returns to idle.
4. **Given** the app is running, **When** the user says "Hey Jarvis" again while already listening, **Then** the previous session is cancelled and a new one starts.

---

### User Story 2 — AI Agent Routing & Execution (Priority: P2)

A user asks JARVIS to perform a task. JARVIS classifies the task complexity, routes it to the appropriate AI agent (Claude, Codex, Gemini, or Ollama), executes it, and delivers the result via voice.

**Why this priority**: Routing to AI agents is what makes JARVIS useful beyond a simple voice clock. Without routing, no meaningful tasks can be completed.

**Independent Test**: Can be tested by connecting one AI provider (e.g., Ollama locally), asking a simple question and a complex code-writing task, and confirming correct routing decisions and voice responses in both cases.

**Acceptance Scenarios**:

1. **Given** a simple task is detected (e.g., "open my browser," "read this file"), **When** JARVIS classifies it, **Then** it executes automatically without any prompt or notification beforehand.
2. **Given** a medium task is detected (e.g., "create a file," "install a package"), **When** JARVIS classifies it, **Then** it executes automatically and shows a brief notification after completion.
3. **Given** a complex task is detected (e.g., "write a Python script," "commit these changes," "delete this folder"), **When** JARVIS classifies it, **Then** a confirmation dialog displays the cleaned prompt and waits for user approval before proceeding.
4. **Given** a complex task is pending approval, **When** the user says "yes, proceed" or clicks Approve, **Then** the task is sent to the selected AI agent and the result is returned via voice.
5. **Given** a complex task is pending approval, **When** the user says "cancel" or clicks Cancel, **Then** the task is discarded and JARVIS returns to idle.
6. **Given** the active provider is unreachable, **When** a request is made, **Then** JARVIS automatically tries the next provider in the fallback chain (Claude → Codex → Gemini → Ollama) and notifies the user which provider handled the request.
7. **Given** all providers in the fallback chain are unreachable, **When** a request is made, **Then** JARVIS notifies the user by voice, logs the task to a retry queue, and returns to idle.
8. **Given** Ollama is configured, **When** the user asks a general knowledge question, **Then** JARVIS routes to Ollama locally with no external network call.

---

### User Story 3 — Provider Configuration & Authentication (Priority: P3)

A user connects their AI provider (Claude, Codex, Gemini, Ollama) via the settings panel using either OAuth or an API key. The app stores credentials securely and uses them for all subsequent requests.

**Why this priority**: Without a connected provider, JARVIS cannot answer any requests. This story enables the product to work with real AI capabilities.

**Independent Test**: Can be tested by opening settings, connecting one provider via API key, restarting the app, and confirming the provider is still connected without re-entering credentials.

**Acceptance Scenarios**:

1. **Given** the settings panel is open, **When** an end user selects a provider and clicks "Connect via OAuth," **Then** a browser-based OAuth flow opens and credentials are stored securely without the user seeing a raw API key.
2. **Given** the settings panel is open, **When** a developer enters an API key manually, **Then** the key is stored in the OS keychain (not plain text) and the provider becomes active.
3. **Given** credentials are saved, **When** the app restarts, **Then** the provider remains connected without requiring re-authentication.
4. **Given** multiple providers are configured, **When** the user switches the active provider in settings, **Then** all subsequent requests route to the newly selected provider.

---

### User Story 4 — Three-Tier Approval Flow (Priority: P3)

JARVIS uses a three-tier classification — Simple, Medium, and Complex — to decide how much friction to introduce before executing a task. Users can override the default thresholds per task type from settings.

**Why this priority**: Approval flow is a safety and trust mechanism. Users must feel in control of what is sent to external AI services, especially for destructive actions like commits or deletions — without being interrupted for routine tasks.

**Independent Test**: Can be tested by triggering one task from each tier, verifying the correct behavior (auto-execute / post-notify / pre-approve), editing the prompt on a complex task, approving, and confirming the edited prompt is what gets sent.

**Acceptance Scenarios**:

1. **Given** a complex task is classified, **When** the approval dialog appears, **Then** it displays the cleaned prompt text, an editable text field, and Approve/Cancel options.
2. **Given** the approval dialog is shown, **When** the user edits the prompt text and says "yes, proceed," **Then** the edited text (not the original) is sent to the AI agent.
3. **Given** the approval dialog is shown, **When** the user says "cancel," **Then** the dialog closes, the task is discarded, and JARVIS returns to idle without contacting any external service.
4. **Given** any task is running, **When** the user says "stop" at any point, **Then** execution is immediately halted.
5. **Given** the settings panel is open, **When** the user changes the classification threshold for a task type, **Then** subsequent tasks of that type follow the new threshold.

---

### User Story 5 — Session Memory & Personalization (Priority: P4)

A background memory service runs alongside JARVIS, hooks into the agent lifecycle (session start and end), compresses relevant context from completed sessions, and injects it at the beginning of new sessions — so JARVIS progressively learns how the user communicates. The user can clear memory at any time from settings.

**Why this priority**: Memory is a differentiator that increases long-term retention. It is not required for the core loop but significantly improves the experience over time.

**Independent Test**: Can be tested by establishing a session preference (e.g., "always use formal language"), restarting the app, and confirming the preference is applied to the next interaction without being stated again.

**Acceptance Scenarios**:

1. **Given** the user has completed several sessions, **When** they start a new session, **Then** JARVIS applies learned communication preferences without the user restating them.
2. **Given** a task was run previously, **When** the same task is requested again, **Then** the response returns faster than the first invocation (prompt cache active).
3. **Given** the settings panel is open, **When** the user clicks "Clear Memory," **Then** all session memory is erased and JARVIS reverts to default behavior on the next interaction.
4. **Given** a session ends, **When** the memory service processes it, **Then** only relevant behavioral patterns are persisted — raw transcripts and voice audio are not retained.

---

### User Story 6 — Usage Dashboard (Priority: P5)

The user can view token usage, estimated cost per provider, and savings from using Ollama for simple tasks — broken down by day, week, and month.

**Why this priority**: Transparency about cost and usage builds trust, especially for commercial users paying for AI API access.

**Independent Test**: Can be tested by making several requests across two providers, opening the dashboard, and confirming accurate token counts and cost estimates appear for each provider.

**Acceptance Scenarios**:

1. **Given** requests have been made, **When** the user opens the dashboard, **Then** they see token usage totals for today, this week, and this month.
2. **Given** multiple providers are used, **When** the dashboard is viewed, **Then** estimated cost is shown per provider in the user's local currency.
3. **Given** Ollama handled some tasks, **When** the dashboard is viewed, **Then** a "Savings from local model" line shows the estimated cost avoided vs. using a paid provider.

---

### User Story 7 — Skills & MCP Connections (Priority: P6)

The user installs agent Skills and connects external services (Notion, Figma, GitHub, Vercel) via MCP from the settings panel. Skills are installed by detecting the active agent's skills directory and placing or removing the skill files there. MCP connections are added by pasting a service URL or browsing Smithery — the app then configures the agent accordingly. The app shows only Skills compatible with the active AI provider.

**Why this priority**: Skills and MCPs extend JARVIS beyond conversation into real-world action. This is a high-value differentiator but requires the core loop and provider integration to be working first.

**Independent Test**: Can be tested by connecting one MCP (e.g., Notion), asking JARVIS to "create a Notion page," and confirming the page is created in the connected Notion workspace.

**Acceptance Scenarios**:

1. **Given** the settings panel is open, **When** the user navigates to Skills, **Then** only Skills compatible with the currently active AI provider are shown.
2. **Given** a Skill is installed, **When** JARVIS routes a matching task, **Then** the Skill is invoked as part of the agent execution.
3. **Given** the user pastes an MCP service URL or selects a service from the Smithery browser, **When** they click Connect, **Then** the service is added to the agent's MCP configuration and available for voice requests immediately.
4. **Given** an MCP requires OAuth, **When** the user connects it, **Then** a browser-based OAuth flow opens and the token is stored in the OS keychain.
5. **Given** an MCP is connected, **When** the user makes a voice request that involves that service, **Then** JARVIS uses the MCP to fulfill the request without the user leaving the app.

---

### Edge Cases

- What happens when the microphone is unavailable or access is denied?
- What happens when the hotword fires in a noisy environment with false positives?
- What happens when the primary AI provider is unreachable — does the fallback chain activate automatically?
- What happens when all providers in the fallback chain (Claude → Codex → Gemini → Ollama) are unavailable simultaneously?
- What happens when the retry queue accumulates tasks that are never retried (e.g., provider stays down)?
- What happens when the AI agent returns an error or refuses the request?
- What happens when transcription produces an empty or incoherent result?
- What happens when the user speaks over the voice response?
- What happens when Ollama is not installed and is the only configured provider?
- What happens when a task approval dialog is left open for an extended time?
- What happens when the OS keychain is unavailable (e.g., headless server)?
- What happens when a task is classified as Medium but the user expected Complex-level approval?

---

## Requirements *(mandatory)*

### Functional Requirements

**Audio Pipeline**

- **FR-001**: System MUST continuously listen for the configured hotword in the background with minimal CPU usage when idle.
- **FR-002**: System MUST transcribe captured speech locally using the on-device transcription model.
- **FR-003**: System MUST clean and normalize the transcribed text before sending it to any AI agent.
- **FR-004**: System MUST classify each request into one of three tiers before routing: Simple (auto-execute silently), Medium (execute then notify), or Complex (pause for user approval).
- **FR-005**: System MUST respond to the user via synthesized speech after task completion.
- **FR-006**: System MUST display a tray icon animation whenever it transitions from idle to listening state.

**Agent Routing**

- **FR-007**: System MUST route Simple-tier tasks directly to execution without any user interaction.
- **FR-007b**: System MUST route Medium-tier tasks to execution and display a brief completion notification after the task finishes.
- **FR-008**: System MUST display an approval dialog for Complex-tier tasks before any external AI call is made.
- **FR-009**: System MUST allow the user to edit the cleaned prompt in the approval dialog before approving.
- **FR-010**: System MUST support cancellation of any pending or running task by voice or UI interaction at any point.
- **FR-011**: System MUST support at least four AI providers: Claude, Codex, Gemini, and Ollama.
- **FR-011b**: System MUST implement a provider fallback chain in the following order: Claude → Codex → Gemini → Ollama. When the active provider is unreachable, the next available provider in the chain is tried automatically.
- **FR-011c**: When all providers in the fallback chain are unreachable, the system MUST notify the user by voice and add the task to a local retry queue for later processing.
- **FR-012**: System MUST support fully offline operation when Ollama is the active provider.
- **FR-012b**: System MUST allow the user to configure and override the default classification tier for any task type from the settings panel.

**Authentication & Credentials**

- **FR-013**: System MUST store all API keys and OAuth tokens in the OS keychain — never in plain text files.
- **FR-014**: System MUST support OAuth-based provider connection for end users.
- **FR-015**: System MUST support API key–based provider connection for developers.
- **FR-016**: System MUST persist provider credentials across application restarts without re-authentication.

**Configuration & Settings**

- **FR-017**: System MUST allow the user to configure a custom hotword phrase.
- **FR-018**: System MUST allow the user to select a voice (at minimum: one male, one female) in each supported language.
- **FR-018b**: System MUST support voice interaction in English and Portuguese (Brazil) for MVP. The user selects their preferred language from settings; hotword detection, transcription, and voice response all operate in the selected language.
- **FR-019**: System MUST support light and dark themes, defaulting to the OS system theme.
- **FR-020**: System MUST allow the user to switch the active AI provider from the settings panel.

**Memory**

- **FR-021**: A background memory service MUST run alongside JARVIS, hook into agent lifecycle events (session start and end), compress session data, and inject relevant context at the start of each new session.
- **FR-021b**: System MUST persist user communication preferences across sessions without retaining raw voice audio or raw transcripts.
- **FR-022**: System MUST cache repeated prompts to reduce response latency on subsequent identical requests.
- **FR-023**: System MUST allow the user to clear all session memory from the settings panel, with a confirmation step to prevent accidental erasure.

**Skills & MCPs**

- **FR-024**: System MUST display only Skills compatible with the currently active AI provider.
- **FR-025**: System MUST allow the user to install and remove Skills from the settings panel. Installation places skill files in the active agent's skills directory; removal deletes them.
- **FR-026**: System MUST allow the user to connect MCP integrations by pasting a service URL or browsing the Smithery catalog from the settings panel. Each MCP connection supports OAuth or API key authentication, stored in the OS keychain.

**Usage Dashboard**

- **FR-027**: System MUST track token usage per provider per session and persist it locally.
- **FR-028**: System MUST display token usage grouped by day, week, and month.
- **FR-029**: System MUST display estimated cost per provider based on published pricing.
- **FR-030**: System MUST display the estimated cost savings from Ollama usage versus paid providers.

**Authentication (End Users)**

- **FR-031**: System MUST allow end users to sign up and log in with email/password or Google OAuth.

### Key Entities

- **User**: The person interacting with JARVIS. Has a profile, preferences, memory, and connected providers.
- **Session**: A single activation of JARVIS — from hotword detection to voice response. Tracks duration, tokens used, provider used.
- **Request**: A single voice command captured in one session. Has raw transcript, cleaned prompt, classification tier (Simple/Medium/Complex), and routing outcome.
- **Provider**: An AI service connected to JARVIS (Claude, Codex, Gemini, Ollama). Has credentials, type (cloud/local), and active status.
- **Skill**: An installable capability extension for a specific AI provider. Compatible with one or more providers.
- **MCP Connection**: A link to an external service (Notion, GitHub, etc.) exposed to the AI agent via the Model Context Protocol.
- **Memory Entry**: A persisted user preference or behavioral pattern captured from prior sessions.
- **Usage Record**: A log entry of tokens consumed, provider used, estimated cost, and timestamp for each completed request.
- **Retry Queue**: A local queue of tasks that could not be completed because all providers were unavailable. Persisted across restarts; the user can inspect and retry items from the settings panel.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Average voice-to-response time is under 5 seconds on a mid-range consumer desktop (8 GB RAM, quad-core CPU).
- **SC-002**: The application works fully offline — hotword detection, transcription, and AI response — when Ollama is the active provider with no network connection.
- **SC-003**: A first-time user can install the application and complete their first voice interaction in under 2 minutes on Windows and Linux.
- **SC-004**: No user data (voice, transcripts, prompts, credentials) is transmitted to any external server without explicit user consent and an active provider connection.
- **SC-005**: The application remains responsive (tray icon interactive, settings accessible) even when the AI provider is unavailable.
- **SC-006**: 90% of simple-vs-complex task classifications match user expectation as measured in user testing (10 representative tasks per category).
- **SC-007**: Prompt cache reduces response latency for repeated tasks by at least 30% compared to the first invocation.
- **SC-008**: A user whose system language is Portuguese (Brazil) can complete the full voice interaction loop — hotword, transcription, and voice response — entirely in Portuguese without switching to English.

---

## Assumptions

- End users run Windows 10+ or Ubuntu 20.04+ (Mac support is roadmap v2, explicitly out of scope for this spec).
- "Average hardware" means a consumer desktop with at least 8 GB RAM, a quad-core CPU, and no dedicated GPU required for local operation.
- The hotword "Hey Jarvis" is used as the default; the bundled hotword model covers this phrase out of the box.
- Voice interaction is supported in English and Portuguese (Brazil) for MVP. Additional languages are out of scope for this spec.
- Local transcription quality is sufficient for English and Portuguese (BR) requests without internet connectivity.
- Task complexity classification uses a lightweight on-device model, not a cloud API call. The default tier assignments are: Simple (open browser, read file), Medium (create file, install package), Complex (write code, commit changes, delete files). Users may override these defaults per task type in settings.
- The OS keychain is available on all supported platforms (Windows Credential Manager, Linux Secret Service via libsecret).
- Ollama must be separately installed by the user before local AI routing is available; JARVIS detects it automatically if present.
- The usage dashboard calculates cost estimates based on each provider's published public pricing at the time of the release; real-time pricing is not fetched.
- Skills are installed from the active AI agent's skill directory; the app manages file placement automatically. The skill catalog surfaces available skills per provider.
- MCP integrations are connected by URL or via the Smithery catalog. The app configures the agent's MCP settings file directly. Each MCP supports either OAuth or API key authentication.
- Distribution is closed-source via signed installer only (.exe for Windows, .AppImage for Linux). Source code is not shipped with the installer.
