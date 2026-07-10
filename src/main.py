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


_SILENCE_AMPLITUDE_THRESHOLD = 500  # int16 scale (max 32767)
_SILENCE_CHUNKS_TO_STOP = 37  # ~1.2s of silence at 512 frames / 16kHz
_MAX_RECORD_CHUNKS = 250  # ~8s safety cap so a stuck mic can't hang forever


def _is_silent(chunk: "np.ndarray", threshold: int = _SILENCE_AMPLITUDE_THRESHOLD) -> bool:
    """True if a 16-bit PCM chunk's mean absolute amplitude is below threshold."""
    import numpy as np
    return bool(np.abs(chunk).mean() < threshold)


def _generate_chime_samples(sample_rate: int = 16_000) -> "np.ndarray":
    """Short two-tone ascending beep (~180ms) played when the hotword activates."""
    import numpy as np
    tone_duration = 0.09
    t = np.linspace(0, tone_duration, int(sample_rate * tone_duration), endpoint=False)
    tone1 = 0.15 * np.sin(2 * np.pi * 880 * t)
    tone2 = 0.15 * np.sin(2 * np.pi * 1320 * t)
    return np.concatenate([tone1, tone2]).astype(np.float32)


def _play_activation_chime() -> None:
    """Blocking playback of the activation chime. Runs off the event loop."""
    try:
        import sounddevice as sd
        sample_rate = 16_000
        sd.play(_generate_chime_samples(sample_rate), sample_rate)
        sd.wait()
    except Exception as exc:  # pragma: no cover - best-effort UX, never fatal
        _log.warning("activation_chime_failed", error=str(exc))


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
    # Model loading may download files on first run; keep that off the event loop.
    hotword = await asyncio.to_thread(HotwordDetector, phrases=[hotword_phrase], threshold=0.5)
    mic = Microphone()

    preprocessor = Preprocessor()
    classifier = Classifier(overrides={})
    agent_router = Router(agents=[
        OllamaAgent(model="llama3.2:1b"),
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

    # "guarding" covers the moment a wake word fires through the end of the
    # activation chime — openWakeWord has no built-in cooldown and can refire
    # on several consecutive chunks of the same utterance, and nothing must
    # touch the mic/speaker (hotword.process_chunk or another chime) during
    # that window, or concurrent PortAudio calls corrupt native state and
    # crash the process. "active" covers the actual command-recording phase.
    recording = {
        "guarding": False,
        "active": False,
        "chunks": [],
        "silence_run": 0,
        "speech_started": False,
    }
    recording_done = asyncio.Event()

    async def on_audio_chunk(chunk: object) -> None:
        if recording["active"]:
            recording["chunks"].append(chunk)
            if _is_silent(chunk):
                # Leading silence (before the user starts talking) doesn't
                # count toward the cutoff, or recording would end before
                # any speech is captured.
                if recording["speech_started"]:
                    recording["silence_run"] += 1
            else:
                recording["speech_started"] = True
                recording["silence_run"] = 0
            if (
                (recording["speech_started"] and recording["silence_run"] >= _SILENCE_CHUNKS_TO_STOP)
                or len(recording["chunks"]) >= _MAX_RECORD_CHUNKS
            ):
                recording["active"] = False
                recording_done.set()
        elif not recording["guarding"]:
            await hotword.process_chunk(chunk)

    turn_in_progress = {"value": False}

    async def on_hotword(phrase: str) -> None:
        if turn_in_progress["value"] or recording["guarding"] or recording["active"]:
            # Ignore a duplicate wake trigger for as long as any part of the
            # previous turn (recording, transcribing, thinking, or speaking)
            # is still running. SessionManager._session_id and the TTS/mic
            # audio devices are shared, single-owner resources — running two
            # turns concurrently corrupts session logging and makes two
            # sd.play() calls fight over the same output, so nothing plays.
            return
        turn_in_progress["value"] = True
        try:
            await _handle_turn(phrase)
        finally:
            turn_in_progress["value"] = False

    async def _handle_turn(phrase: str) -> None:
        # Set synchronously (no `await` before this point) so chunk-processing
        # tasks already queued for this event-loop tick can't slip past it.
        recording["guarding"] = True

        try:
            # Play the activation chime before we start recording so it isn't
            # picked up by the microphone as part of the user's command.
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _play_activation_chime)

            recording["active"] = True
            recording["chunks"] = []
            recording["silence_run"] = 0
            recording["speech_started"] = False
            recording_done.clear()
            recording["guarding"] = False

            if session_mgr.state != SessionState.IDLE:
                await session_mgr.end_session()
            await session_mgr.start_session()
            await session_mgr.transition(SessionState.TRANSCRIBING)
        except Exception:
            recording["guarding"] = False
            recording["active"] = False
            raise

        import numpy as np
        await recording_done.wait()

        raw = (
            np.concatenate(recording["chunks"])
            if recording["chunks"]
            else np.zeros(1, dtype=np.int16)
        )
        audio = raw.astype(np.float32) / 32768.0
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
    mic.on_chunk(on_audio_chunk)
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

    import sys
    from PyQt6.QtWidgets import QApplication
    from src.ui.tray import JarvisTray

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray = JarvisTray(config, app)

    async def _on_state_change(state: SessionState) -> None:
        tray.state_changed.emit(state)

    session_mgr.on_state_change(_on_state_change)

    # Run the audio pipeline (asyncio) in a background thread so the Qt
    # event loop can own the main thread, as PyQt6 requires.
    pipeline_thread = threading.Thread(
        target=lambda: asyncio.run(_run_pipeline(config, session_mgr)),
        daemon=True,
    )
    pipeline_thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
