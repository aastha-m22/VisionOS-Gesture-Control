"""Placeholder for future voice-command control.

Intended design: a lightweight wake-word + command recogniser (e.g. Vosk or the
``speech_recognition`` package) maps spoken phrases ("click", "scroll down",
"screenshot") onto the same action verbs the gesture pipeline already dispatches
through the controllers. Voice and gesture would be complementary input
modalities arbitrated by the application's action dispatcher.
"""

from __future__ import annotations

from typing import Optional

from visionos.utils.logger import get_logger

logger = get_logger("integrations.voice_control")


class VoiceCommander:
    """Stub voice command listener. No-op until implemented."""

    def __init__(self) -> None:
        self.enabled = False
        logger.debug("VoiceCommander stub created (not yet implemented)")

    def poll(self) -> Optional[str]:
        """Return a recognised command string, or None when idle."""
        return None
