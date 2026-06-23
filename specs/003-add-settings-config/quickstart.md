# Quickstart: Settings & Configuration Module

**Branch**: `003-add-settings-config` | **Date**: 2026-06-22

## Prerequisites

```bash
# Python 3.11+ and uv installed
uv sync --extra ui --extra linux   # Linux
uv sync --extra ui                 # macOS / Windows

# Verify PyQt6 is available
uv run python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
```

## Scenario 1: Run the Unit Tests

This is the primary validation path. All new code must have passing tests before implementation is considered complete.

```bash
uv run pytest tests/unit/config/test_settings.py -v
uv run pytest tests/unit/ui/ -v
```

**Expected outcome**: All tests pass. Coverage for `src/config/settings.py` ≥ 80%. UI tests run headless via `pytest-qt`.

---

## Scenario 2: First-Run Wizard

Verify the wizard launches automatically when no config exists.

```bash
# Temporarily move config away (if it exists)
mv ~/.jarvis/config.yaml ~/.jarvis/config.yaml.bak 2>/dev/null || true

uv run python -c "
from PyQt6.QtWidgets import QApplication
from src.ui.wizard import FirstRunWizard
import sys
app = QApplication(sys.argv)
w = FirstRunWizard()
w.show()
sys.exit(app.exec())
"

# After completing wizard, verify config was written
cat ~/.jarvis/config.yaml

# Restore backup
mv ~/.jarvis/config.yaml.bak ~/.jarvis/config.yaml 2>/dev/null || true
```

**Expected outcome**: Wizard opens at step 0 (Welcome). Completing all steps writes a valid `config.yaml`. Quitting mid-wizard writes `.wizard_state.json` and resumes on relaunch.

---

## Scenario 3: Settings Panel Opens from Tray

Verify the tray icon right-click menu includes "Settings" and opens the panel.

```bash
uv run python -m jarvis.main &
# Right-click the system tray icon → Settings
# Panel opens with 10 tabs, each loading lazily on first click
```

**Expected outcome**: Panel opens in < 1 s. Each tab loads its section within 1 s of first click. "Save" writes config atomically. "Cancel" discards all changes.

---

## Scenario 4: Test Connection Validation

Verify that "Test Connection" blocks saving on failure.

```bash
# Launch settings panel
# Navigate to Provider & Auth tab
# Enter an intentionally wrong API key: "invalid-key-123"
# Click "Test Connection"
```

**Expected outcome**: Error message shown within 10 s. "Save" button remains disabled until a successful connection test is recorded for the current provider and key.

See [contracts/settings-api.md](contracts/settings-api.md) for the `POST /settings/test-connection` endpoint spec.

---

## Scenario 5: Credential Security Check

Verify no credentials appear in `config.yaml` after saving.

```bash
# In the Settings panel, enter a provider API key and save
grep -i "sk-\|api.key\|token\|secret" ~/.jarvis/config.yaml
```

**Expected outcome**: Zero matches. All credential fields in `config.yaml` are absent or empty strings. Run `GET /settings` via the API and confirm credential fields are `null`.

---

## Scenario 6: API Endpoint Validation

Verify the settings REST API works end-to-end.

```bash
# Start JARVIS (must have a valid config.yaml first)
uv run python -m jarvis.main &
sleep 2

# Read current settings
curl -s http://localhost:37420/settings | python3 -m json.tool

# Update theme
curl -s -X PATCH http://localhost:37420/settings \
  -H "Content-Type: application/json" \
  -d '{"theme": "dark"}' | python3 -m json.tool

# Verify theme persisted
python3 -c "
import yaml; c = yaml.safe_load(open('$HOME/.jarvis/config.yaml'))
assert c['theme'] == 'dark', f'Expected dark, got {c[\"theme\"]}'
print('Theme persisted correctly')
"
```

See [contracts/settings-api.md](contracts/settings-api.md) for full endpoint reference.

---

## Scenario 7: Memory Export

Verify the memory export produces a valid ZIP.

```bash
# In the Settings panel → Memory Management → "Export memory"
# Choose a save path (e.g., ~/jarvis-memory-backup.zip)

# Verify the ZIP contents
python3 -c "
import zipfile, sys
with zipfile.ZipFile('$HOME/jarvis-memory-backup.zip') as z:
    names = z.namelist()
    print('Files in export:', names)
    assert 'export_manifest.json' in names, 'Missing manifest'
    print('Export OK')
"
```

**Expected outcome**: ZIP contains `export_manifest.json` and any memory files present. Export completes without error even if no memory exists yet.

---

## Scenario 8: Budget Cap Alert (Manual Simulation)

Verify budget threshold notification triggers correctly.

```bash
# In Settings → Dashboard & Budget:
# Set daily_limit_usd = 1.00, alert_threshold_pct = 80
# Save settings

# Simulate a usage event that crosses $0.80 by patching usage tracking
uv run pytest tests/unit/ui/test_budget.py::test_alert_fires_at_threshold -v
```

**Expected outcome**: Test confirms the notification callback fires when simulated spend crosses 80% of the cap, and execution pauses at 100%.

---

## Data Model Reference

See [data-model.md](data-model.md) for:
- Full `JarvisConfig` extension fields
- Keychain namespace table
- Config save and wizard state transitions

## Contract Reference

| Contract | Description |
|----------|-------------|
| [config-schema.md](contracts/config-schema.md) | Full `config.yaml` schema with all new fields |
| [keychain-namespace.md](contracts/keychain-namespace.md) | Credential key naming conventions |
| [settings-api.md](contracts/settings-api.md) | REST API endpoint specs |
