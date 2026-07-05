"""JARVIS entry point.

Starts:
1. Local FastAPI REST API (IPC bus)
2. Audio pipeline (hotword → transcriber → TTS)
3. Session state manager
4. System tray icon (UI thread)
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from src.config.settings import load_config
from src.memory.audit import configure_logging, get_logger
from src.memory.session import SessionManager, SessionState
from src.storage.db import init_db

_log = get_logger("main")


async def _run_pipeline(config: object, session_mgr: SessionManager) -> None:
    """Wire up the audio pipeline coroutine."""
    from src.audio.microphone import Microphone
    from src.audio.hotword import HotwordDetector
    from src.audio.transcriber import Transcriber
    from src.audio.tts import TTSEngine
    from src.processing.preprocessor import Preprocessor
    from src.processing.classifier import Classifier
    from src.processing.router import Router
    from src.agents.ollama_agent import OllamaAgent
    from src.agents.claude_agent import ClaudeAgent
    from src.agents.codex_agent import CodexAgent
    from src.agents.gemini_agent import GeminiAgent
    from src.api.routes.pipeline import set_pipeline

    hotword_phrase = config.hotword_config.phrase.replace(" ", "_")
    language_map = {"en-us": "en", "pt-br": "pt"}
    lang_cfg = getattr(getattr(config, "voice", None), "language", "en-us")
    language = language_map.get(lang_cfg, "en")
    gender = getattr(getattr(config, "voice", None), "gender", "female")

    transcriber = Transcriber(model_size="base", language=language)
    tts = TTSEngine(language=lang_cfg, gender=gender)
    hotword = HotwordDetector(phrases=[hotword_phrase], threshold=0.5)
    mic = Microphone()

    preprocessor = Preprocessor()
    classifier = Classifier(overrides={})
    agent_router = Router(agents=[
        OllamaAgent(),
        ClaudeAgent(),
        CodexAgent(),
        GeminiAgent(),
    ])

    set_pipeline(preprocessor, classifier, agent_router, session_mgr)

    last_exchange: dict[str, tuple[str, str]] = {}

    async def on_session_ended(session_id: str) -> None:
        exchange = last_exchange.pop(session_id, None)
        if exchange is None:
            return
        from src.memory.vault_writer import extract_and_write
        prompt, response_text = exchange
        await extract_and_write(
            session_id=session_id, router=agent_router, prompt=prompt, response=response_text
        )

    session_mgr.on_session_ended(on_session_ended)

    async def on_hotword(phrase: str) -> None:
        if session_mgr.state != SessionState.IDLE:
            await session_mgr.end_session()
        await session_mgr.start_session()
        await session_mgr.transition(SessionState.TRANSCRIBING)

        import numpy as np
        audio = np.zeros(16000, dtype=np.float32)  # placeholder for real mic buffer
        transcript = await transcriber.transcribe(audio)
        _log.info("transcript_received", text=transcript.text)

        if not transcript.text:
            await session_mgr.end_session()
            return

        await session_mgr.transition(SessionState.CLASSIFYING)
        cleaned = await preprocessor.clean(transcript.text)
        tier = classifier.classify(cleaned)
        _log.info("task_classified", tier=tier)

        await session_mgr.transition(SessionState.EXECUTING)
        from src.agents.base import AgentRequest, AllProvidersUnavailableError
        from src.memory.vault_context import build_context
        import uuid
        try:
            system_prefix = await build_context(cleaned)
            response = await agent_router.route(
                AgentRequest(prompt=cleaned, request_id=str(uuid.uuid4()), system_prefix=system_prefix)
            )
            last_exchange[session_mgr.session_id] = (cleaned, response.content)
            await session_mgr.transition(SessionState.SPEAKING)
            await tts.speak(response.content)
        except AllProvidersUnavailableError:
            _log.error("all_providers_failed")
            await tts.speak("Sorry, I could not reach any AI provider right now.")

        await session_mgr.end_session()

    hotword.on_detected = on_hotword
    mic.on_chunk(hotword.process_chunk)
    mic.start()

    _log.info("pipeline_running", hotword=hotword_phrase, language=language)
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        mic.stop()


def _run_api() -> None:
    from src.api.server import run as run_api
    run_api()


def _run_first_time_wizard() -> bool:
    """Show the first-run wizard if no config exists. Returns True if setup completed."""
    import sys
    from PyQt6.QtWidgets import QApplication
    from src.ui.wizard import FirstRunWizard

    app = QApplication.instance() or QApplication(sys.argv)
    wizard = FirstRunWizard()
    wizard.show()
    result = app.exec()
    return result == 0


def main() -> None:
    default_path = Path.home() / ".jarvis" / "config.yaml"
    fallback_path = Path("config.yaml")
    config_path = default_path if default_path.exists() else (
        fallback_path if fallback_path.exists() else None
    )

    # First-run: show wizard if no config exists
    if config_path is None:
        _log.info("first_run_detected")
        completed = _run_first_time_wizard()
        if not completed:
            _log.info("wizard_aborted")
            return
        config_path = default_path

    try:
        config = load_config(config_path)
    except Exception as exc:
        print(f"[JARVIS] Config error: {exc}. Using defaults where possible.")
        from src.config.settings import JarvisConfig
        config = JarvisConfig(provider="ollama", model="llama3")

    configure_logging(
        level=config.logging.level,
        fmt=config.logging.format,
        file=config.logging.file,
    )

    _log.info("jarvis_starting", provider=config.provider, hotword=config.hotword_config.phrase)

    # Start API server in background thread
    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()

    session_mgr = SessionManager()

    # Run audio pipeline in asyncio event loop
    asyncio.run(_run_pipeline(config, session_mgr))


if __name__ == "__main__":
    main()
