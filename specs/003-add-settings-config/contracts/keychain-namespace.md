# Contract: Keychain Namespace

**Feature**: 003-add-settings-config | **Date**: 2026-06-22

## Service Name

All JARVIS credentials use the keychain service name `JARVIS`.

## Key Format

`jarvis/<namespace>/<name>`

## Registered Namespaces

| Namespace | Name | Value | Set by |
|-----------|------|-------|--------|
| `provider` | `claude` | Anthropic API key | Provider section, wizard step 2 |
| `provider` | `openai` | OpenAI API key | Provider section, wizard step 2 |
| `provider` | `gemini` | Google API key | Provider section, wizard step 2 |
| `oauth` | `claude` | OAuth access token | OAuth callback flow |
| `oauth` | `openai` | OAuth access token | OAuth callback flow |
| `mcp` | `<service_name>` | MCP API key or token | MCP manager section |

## Rules

1. Only `src/config/keychain.py` may call `keyring.*` directly. All other modules use `write_credential`, `read_credential`, `delete_credential`.
2. Credentials are NEVER written to `config.yaml`, logs, or any file. Pydantic model `AuthConfig.api_key` must always be empty string in the saved file.
3. On credential deletion (provider removal, MCP disconnect), `delete_credential` is always called even if the key may not exist (it silently ignores missing keys).
4. Adding a new credential type requires registering it here before implementation.
