"""Tests for prompt preprocessor (US2). Write first — confirm FAIL before implementing."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


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
    with patch("src.config.keychain.read_credential") as mock_read:
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
