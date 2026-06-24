"""Tests for prompt preprocessor (US2). Write first — confirm FAIL before implementing."""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# ---------------------------------------------------------------------------
# Phase 2: Foundational dataclasses (T003-T005) — must FAIL before T006-T008
# ---------------------------------------------------------------------------

def test_structured_prompt_dataclass_has_required_fields() -> None:
    from src.processing.preprocessor import StructuredPrompt
    sp = StructuredPrompt(
        task="book a flight",
        context="user is in Brazil",
        constraints="economy class only",
        expected_output="flight options list",
    )
    assert sp.task == "book a flight"
    assert sp.context == "user is in Brazil"
    assert sp.constraints == "economy class only"
    assert sp.expected_output == "flight options list"
    assert sp.incomplete is False


def test_structured_prompt_to_dict_matches_schema() -> None:
    from src.processing.preprocessor import StructuredPrompt
    sp = StructuredPrompt(
        task="book a flight",
        context="ctx",
        constraints="cons",
        expected_output="output",
        incomplete=True,
    )
    d = sp.to_dict()
    assert set(d.keys()) == {"task", "context", "constraints", "expected_output", "incomplete"}
    assert isinstance(d["task"], str)
    assert isinstance(d["incomplete"], bool)
    assert d["incomplete"] is True


def test_preprocessor_result_dataclass_has_metadata_fields() -> None:
    from src.processing.preprocessor import StructuredPrompt, PreProcessorResult
    sp = StructuredPrompt(task="t", context="c", constraints="co", expected_output="e")
    result = PreProcessorResult(
        structured_prompt=sp,
        model_used="claude-haiku",
        stage1_latency_ms=10.0,
        stage2_latency_ms=20.0,
        total_latency_ms=30.0,
        stage1_input="raw text",
        stage1_output="clean text",
    )
    assert result.structured_prompt is sp
    assert result.model_used == "claude-haiku"
    assert result.stage1_latency_ms == 10.0
    assert result.stage2_latency_ms == 20.0
    assert result.total_latency_ms == 30.0
    assert result.stage1_input == "raw text"
    assert result.stage1_output == "clean text"
    assert result.error is None


# ---------------------------------------------------------------------------
# Phase 3: User Story 1 — Stage 1 improvements (T009-T012) — must FAIL first
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_empty_input_no_model_call() -> None:
    from src.processing.preprocessor import Preprocessor, PreProcessorResult
    pp = Preprocessor.__new__(Preprocessor)
    with patch("src.processing.preprocessor.Preprocessor._clean_with_model") as mock_clean:
        result = await pp.process("")
    mock_clean.assert_not_called()
    assert isinstance(result, PreProcessorResult)
    assert result.structured_prompt.task == ""
    assert result.stage1_latency_ms == 0.0
    assert result.stage2_latency_ms == 0.0


@pytest.mark.asyncio
async def test_process_provider_reselected_per_call() -> None:
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)

    call_count = {"n": 0}

    def _side_effect(ns, name):
        call_count["n"] += 1
        return "sk-ant-fake" if call_count["n"] <= 2 else None

    with patch("src.processing.preprocessor.read_credential", side_effect=_side_effect):
        with patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="clean"):
            with patch("src.processing.preprocessor.Preprocessor._structure_with_model") as mock_s2:
                from src.processing.preprocessor import StructuredPrompt
                mock_s2.return_value = StructuredPrompt(task="t", context="", constraints="", expected_output="")
                r1 = await pp.process("first call")

    call_count["n"] = 100  # force Ollama path on second call
    with patch("src.processing.preprocessor.read_credential", return_value=None):
        with patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="clean"):
            with patch("src.processing.preprocessor.Preprocessor._structure_with_model") as mock_s2:
                from src.processing.preprocessor import StructuredPrompt
                mock_s2.return_value = StructuredPrompt(task="t", context="", constraints="", expected_output="")
                r2 = await pp.process("second call")

    assert r1.model_used != r2.model_used


@pytest.mark.asyncio
async def test_process_stage1_latency_tracked() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt
    pp = Preprocessor.__new__(Preprocessor)
    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="clean text"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model",
              return_value=StructuredPrompt(task="t", context="", constraints="", expected_output="")),
    ):
        result = await pp.process("hello world")
    assert result.stage1_latency_ms > 0


@pytest.mark.asyncio
async def test_process_stage1_audit_log_emitted() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt

    pp = Preprocessor.__new__(Preprocessor)
    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="cleaned output"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model",
              return_value=StructuredPrompt(task="t", context="", constraints="", expected_output="")),
        patch("src.processing.preprocessor._log") as mock_log,
    ):
        await pp.process("raw input text")

    called_events = [call.args[0] for call in mock_log.info.call_args_list]
    assert "preprocessor_stage1" in called_events
    # Verify key fields present in the stage1 call
    stage1_call = next(c for c in mock_log.info.call_args_list if c.args[0] == "preprocessor_stage1")
    assert stage1_call.kwargs.get("stage1_input") == "raw input text"
    assert stage1_call.kwargs.get("stage1_output") == "cleaned output"


# ---------------------------------------------------------------------------
# Phase 4: User Story 2 — Stage 2 StructuredPrompt (T017-T022) — must FAIL first
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_returns_preprocessor_result() -> None:
    from src.processing.preprocessor import Preprocessor, PreProcessorResult
    pp = Preprocessor.__new__(Preprocessor)
    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="book a flight"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model") as mock_s2,
    ):
        from src.processing.preprocessor import StructuredPrompt
        mock_s2.return_value = StructuredPrompt(task="book a flight", context="", constraints="", expected_output="")
        result = await pp.process("book a flight please")
    assert isinstance(result, PreProcessorResult)
    assert result.structured_prompt is not None


@pytest.mark.asyncio
async def test_process_structured_prompt_has_all_fields() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt
    pp = Preprocessor.__new__(Preprocessor)
    expected_sp = StructuredPrompt(
        task="book a flight",
        context="from São Paulo",
        constraints="economy only",
        expected_output="list of options",
    )
    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="book a flight"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model", return_value=expected_sp),
    ):
        result = await pp.process("book a flight please")
    d = result.structured_prompt.to_dict()
    assert result.structured_prompt.task == "book a flight"
    assert set(d.keys()) == {"task", "context", "constraints", "expected_output", "incomplete"}


@pytest.mark.asyncio
async def test_process_stage2_json_error_retries_once() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt
    pp = Preprocessor.__new__(Preprocessor)
    call_count = {"n": 0}

    async def _mock_structure(text: str) -> StructuredPrompt:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise json.JSONDecodeError("bad json", "", 0)
        return StructuredPrompt(task=text, context="", constraints="", expected_output="")

    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="clean text"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model", side_effect=_mock_structure),
    ):
        result = await pp.process("some request")

    assert call_count["n"] == 2
    assert result.structured_prompt.task == "clean text"


@pytest.mark.asyncio
async def test_process_stage2_double_json_error_returns_incomplete() -> None:
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)

    async def _always_fail(text: str):
        raise json.JSONDecodeError("bad json", "", 0)

    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="clean text"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model", side_effect=_always_fail),
    ):
        result = await pp.process("ambiguous request")

    assert result.structured_prompt.incomplete is True
    assert result.error is not None


@pytest.mark.asyncio
async def test_process_stage2_latency_tracked() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt
    pp = Preprocessor.__new__(Preprocessor)
    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="clean"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model",
              return_value=StructuredPrompt(task="t", context="", constraints="", expected_output="")),
    ):
        result = await pp.process("test input")
    assert result.stage2_latency_ms > 0
    assert result.total_latency_ms >= result.stage1_latency_ms + result.stage2_latency_ms - 1.0


@pytest.mark.asyncio
async def test_process_stage2_audit_log_emitted() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt
    pp = Preprocessor.__new__(Preprocessor)
    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="clean"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model",
              return_value=StructuredPrompt(task="task text", context="", constraints="", expected_output="")),
        patch("src.processing.preprocessor._log") as mock_log,
    ):
        await pp.process("input text")
    called_events = [call.args[0] for call in mock_log.info.call_args_list]
    assert "preprocessor_stage2" in called_events
    stage2_call = next(c for c in mock_log.info.call_args_list if c.args[0] == "preprocessor_stage2")
    assert "incomplete" in stage2_call.kwargs
    assert "task" in stage2_call.kwargs
    assert "latency_ms" in stage2_call.kwargs


# ---------------------------------------------------------------------------
# Phase 5: User Story 3 — incomplete flag surfaced (T027-T028) — must FAIL first
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_incomplete_flag_set_when_diligence_detects_missing_context() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt
    pp = Preprocessor.__new__(Preprocessor)
    incomplete_sp = StructuredPrompt(task="remind me", context="", constraints="", expected_output="", incomplete=True)
    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="remind me"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model", return_value=incomplete_sp),
    ):
        result = await pp.process("um remind me of something")
    assert result.structured_prompt.incomplete is True


@pytest.mark.asyncio
async def test_pipeline_route_includes_structured_prompt_when_incomplete() -> None:
    from httpx import AsyncClient, ASGITransport
    from src.api.server import create_app
    from src.processing.preprocessor import PreProcessorResult, StructuredPrompt
    import src.api.routes.pipeline as pipeline_module

    incomplete_sp = StructuredPrompt(task="remind me", context="", constraints="", expected_output="", incomplete=True)
    incomplete_result = PreProcessorResult(
        structured_prompt=incomplete_sp,
        model_used="ollama:qwen2.5:3b",
        stage1_latency_ms=1.0,
        stage2_latency_ms=1.0,
        total_latency_ms=2.0,
        stage1_input="remind me",
        stage1_output="remind me",
    )

    mock_preprocessor = MagicMock()
    mock_preprocessor.process = AsyncMock(return_value=incomplete_result)

    mock_classifier = MagicMock()
    mock_classifier.classify.return_value = "complex"

    app = create_app()
    with patch.object(pipeline_module, "_pipeline", {
        "preprocessor": mock_preprocessor,
        "classifier": mock_classifier,
        "router": MagicMock(),
        "session": None,
    }):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/voice/command", json={"text": "remind me", "language": "en"})

    assert resp.status_code == 200
    data = resp.json()
    assert "structured_prompt" in data
    assert data["structured_prompt"]["incomplete"] is True


# ---------------------------------------------------------------------------
# Phase 6: User Story 4 — audit log (T031-T032) — must FAIL first
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preprocessor_error_event_logged_on_model_failure() -> None:
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)
    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", side_effect=RuntimeError("model down")),
        patch("src.processing.preprocessor._log") as mock_log,
    ):
        result = await pp.process("do something")

    warning_events = [call.args[0] for call in mock_log.warning.call_args_list]
    assert "preprocessor_error" in warning_events
    error_call = next(c for c in mock_log.warning.call_args_list if c.args[0] == "preprocessor_error")
    assert error_call.kwargs.get("stage") == "stage1"
    assert "error" in error_call.kwargs
    assert "input" in error_call.kwargs


@pytest.mark.asyncio
async def test_audit_log_stage1_contains_input_output_content() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt
    pp = Preprocessor.__new__(Preprocessor)
    with (
        patch("src.processing.preprocessor.read_credential", return_value=None),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model", return_value="cleaned version"),
        patch("src.processing.preprocessor.Preprocessor._structure_with_model",
              return_value=StructuredPrompt(task="t", context="", constraints="", expected_output="")),
        patch("src.processing.preprocessor._log") as mock_log,
    ):
        await pp.process("original raw input")

    stage1_call = next(
        (c for c in mock_log.info.call_args_list if c.args[0] == "preprocessor_stage1"), None
    )
    assert stage1_call is not None
    assert stage1_call.kwargs.get("stage1_input") == "original raw input"
    assert stage1_call.kwargs.get("stage1_output") == "cleaned version"


# ---------------------------------------------------------------------------
# Coverage: model-specific paths in _clean_with_model and _structure_with_model
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_select_model_returns_gpt_when_openai_key() -> None:
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)

    def _cred(ns, name):
        if name == "claude":
            return None
        if name == "codex":
            return "sk-openai-fake"
        return None

    with patch("src.processing.preprocessor.read_credential", side_effect=_cred):
        model_name, client = pp._select_model()
    assert "gpt" in model_name


@pytest.mark.asyncio
async def test_clean_with_model_ollama_path() -> None:
    import httpx as _httpx
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)
    pp._model_name = "ollama:qwen2.5:3b"
    pp._client = None

    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "cleaned text"}

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        result = await pp._clean_with_model("some text")

    assert result == "cleaned text"


@pytest.mark.asyncio
async def test_clean_with_model_claude_path() -> None:
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)
    pp._model_name = "claude-haiku-4-5"

    mock_client = AsyncMock()
    mock_content = MagicMock()
    mock_content.text = "  claude cleaned  "
    mock_client.messages.create = AsyncMock(return_value=MagicMock(content=[mock_content]))
    pp._client = mock_client

    result = await pp._clean_with_model("raw text")
    assert result == "claude cleaned"


@pytest.mark.asyncio
async def test_clean_with_model_gpt_path() -> None:
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)
    pp._model_name = "gpt-4o-mini"

    mock_client = AsyncMock()
    mock_message = MagicMock()
    mock_message.content = "gpt cleaned"
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[MagicMock(message=mock_message)])
    )
    pp._client = mock_client

    result = await pp._clean_with_model("raw text")
    assert result == "gpt cleaned"


@pytest.mark.asyncio
async def test_structure_with_model_claude_path() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt
    pp = Preprocessor.__new__(Preprocessor)
    structured_json = '{"task":"fly","context":"","constraints":"","expected_output":"","incomplete":false}'

    mock_client = AsyncMock()
    mock_content = MagicMock()
    mock_content.text = structured_json
    mock_client.messages.create = AsyncMock(return_value=MagicMock(content=[mock_content]))

    pp._model_name = "claude-haiku-4-5"
    pp._client = mock_client
    result = await pp._structure_with_model("book a flight")

    assert isinstance(result, StructuredPrompt)
    assert result.task == "fly"


@pytest.mark.asyncio
async def test_structure_with_model_gpt_path() -> None:
    from src.processing.preprocessor import Preprocessor, StructuredPrompt
    pp = Preprocessor.__new__(Preprocessor)
    structured_json = '{"task":"search","context":"","constraints":"","expected_output":"results","incomplete":false}'

    mock_client = AsyncMock()
    mock_message = MagicMock()
    mock_message.content = structured_json
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[MagicMock(message=mock_message)])
    )

    pp._model_name = "gpt-4o-mini"
    pp._client = mock_client
    result = await pp._structure_with_model("search for something")

    assert isinstance(result, StructuredPrompt)
    assert result.expected_output == "results"


@pytest.mark.asyncio
async def test_clean_backward_compat() -> None:
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)
    with (
        patch("src.processing.preprocessor.Preprocessor._select_model",
              return_value=("ollama:qwen2.5:3b", None)),
        patch("src.processing.preprocessor.Preprocessor._clean_with_model",
              return_value="clean result"),
    ):
        pp._model_name, pp._client = "ollama:qwen2.5:3b", None
        result = await pp.clean("um like clean this")
    assert result == "clean result"


@pytest.mark.asyncio
async def test_clean_returns_empty_for_blank_input() -> None:
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)
    pp._model_name = "ollama:qwen2.5:3b"
    pp._client = None
    result = await pp.clean("   ")
    assert result == ""


@pytest.mark.asyncio
async def test_clean_handles_model_exception() -> None:
    from src.processing.preprocessor import Preprocessor
    pp = Preprocessor.__new__(Preprocessor)
    pp._model_name = "ollama:qwen2.5:3b"
    pp._client = None
    with patch("src.processing.preprocessor.Preprocessor._clean_with_model",
               side_effect=RuntimeError("model down")):
        result = await pp.clean("hello world")
    assert result == "hello world"


# ---------------------------------------------------------------------------
# Original Stage 1 tests (backward compat)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preprocessor_removes_filler_words() -> None:
    with patch("src.processing.preprocessor.Preprocessor._select_model") as mock_select:
        mock_select.return_value = ("stub", None)
        with patch("src.processing.preprocessor.Preprocessor._clean_with_model") as mock_clean:
            mock_clean.return_value = "open my browser"

            from src.processing.preprocessor import Preprocessor
            pp = Preprocessor()
            result = await pp.clean("um, like, open my browser please")

    assert result == "open my browser"


@pytest.mark.asyncio
async def test_preprocessor_selects_haiku_when_anthropic_key_available() -> None:
    from src.config.keychain import read_credential
    with patch("src.processing.preprocessor.read_credential") as mock_read:
        mock_read.side_effect = lambda ns, name: "sk-ant-fake" if name == "claude" else None

        from src.processing.preprocessor import Preprocessor
        pp = Preprocessor.__new__(Preprocessor)
        model_name, _ = pp._select_model()

    assert "haiku" in model_name.lower()


@pytest.mark.asyncio
async def test_preprocessor_falls_back_to_ollama_when_no_keys() -> None:
    with patch("src.config.keychain.read_credential", return_value=None):
        from src.processing.preprocessor import Preprocessor
        pp = Preprocessor.__new__(Preprocessor)
        model_name, _ = pp._select_model()

    assert "qwen" in model_name.lower() or "ollama" in model_name.lower()
