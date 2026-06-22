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

    hotword_phrase = getattr(config, "hotword", "hey jarvis").replace(" ", "_")
    language_map = {"en-us": "en", "pt-br": "pt"}
    lang_cfg = getattr(getattr(config, "voice", None), "language", "en-us")
    language = language_map.get(lang_cfg, "en")
    gender = getattr(getattr(config, "voice", None), "gender", "female")

    transcriber = Transcriber(model_size="base", language=language)
    tts = TTSEngine(language=lang_cfg, gender=gender)
    hotword = HotwordDetector(phrases=[hotword_phrase], threshold=0.5)
    mic = Microphone()

    async def on_hotword(phrase: str) -> None:
        if session_mgr.state != SessionState.IDLE:
            await session_mgr.end_session()
        await session_mgr.start_session()
        await session_mgr.transition(SessionState.TRANSCRIBING)

        # Capture audio for transcription — in production the mic buffers after hotword
        import numpy as np
        audio = np.zeros(16000, dtype=np.float32)  # placeholder for real buffer
        transcript = await transcriber.transcribe(audio)
        _log.info("transcript_received", text=transcript.text)

        await session_mgr.transition(SessionState.SPEAKING)
        if transcript.text:
            await tts.speak(f"You said: {transcript.text}")
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


def main() -> None:
    config_path = Path("config.yaml")
    try:
        config = load_config(config_path if config_path.exists() else None)
    except Exception as exc:
        print(f"[JARVIS] Config error: {exc}. Using defaults where possible.")
        from src.config.settings import JarvisConfig
        config = JarvisConfig(provider="ollama", model="llama3")

    configure_logging(
        level=config.logging.level,
        fmt=config.logging.format,
        file=config.logging.file,
    )

    _log.info("jarvis_starting", provider=config.provider, hotword=config.hotword)

    # Start API server in background thread
    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()

    session_mgr = SessionManager()

    # Run audio pipeline in asyncio event loop
    asyncio.run(_run_pipeline(config, session_mgr))


if __name__ == "__main__":
    main()
