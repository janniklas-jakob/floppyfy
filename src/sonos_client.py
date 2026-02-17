"""
Sonos speaker discovery and playback control via SoCo.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SonosClient:
    """Manage a Sonos speaker group and control playback."""

    def __init__(self) -> None:
        self.coordinator = None
        self.joined_speakers: list = []

    def discover(self, coordinator_name: str, join_names: Optional[list[str]] = None) -> bool:
        """Find the coordinator speaker and optionally group others with it.

        Returns ``True`` if the coordinator was found.
        """
        import soco                          # type: ignore[import-untyped]
        from soco.discovery import by_name   # type: ignore[import-untyped]

        logger.info("Discovering Sonos speakers. Coordinator: %s", coordinator_name)

        self.coordinator = by_name(coordinator_name)
        if not self.coordinator:
            logger.error("Could not find speaker named '%s'", coordinator_name)
            return False

        self.joined_speakers = []
        for name in (join_names or []):
            speaker = by_name(name)
            if speaker and speaker != self.coordinator:
                logger.info("Joining '%s' to '%s'", name, coordinator_name)
                speaker.join(self.coordinator)
                self.joined_speakers.append(speaker)
            elif not speaker:
                logger.warning("Could not find join-target speaker '%s'", name)

        return True

    def play_uri(self, uri: str, shuffle: bool = False) -> None:
        """Clear the queue, enqueue *uri*, and start playback."""
        if not self.coordinator:
            logger.error("No coordinator selected")
            return

        try:
            self.coordinator.stop()
            self.coordinator.clear_queue()
            self.coordinator.add_uri_to_queue(uri)
            self.coordinator.play_mode = 'SHUFFLE' if shuffle else 'NORMAL'
            self.coordinator.play_from_queue(0)
        except Exception as exc:
            logger.error("Error starting playback: %s", exc)

    def pause(self) -> None:
        """Pause the coordinator. Silently ignores errors (e.g. already paused)."""
        if not self.coordinator:
            return
        try:
            self.coordinator.pause()
        except Exception as exc:
            logger.error("Error pausing: %s", exc)

    def resume(self) -> None:
        """Resume playback on the coordinator."""
        if not self.coordinator:
            return
        try:
            self.coordinator.play()
        except Exception as exc:
            logger.error("Error resuming: %s", exc)

    def get_available_speakers(self) -> list[str]:
        """Return sorted names of all Sonos speakers on the network."""
        import soco  # type: ignore[import-untyped]

        speakers: list[str] = []
        try:
            for zone in soco.discover(timeout=5) or []:
                speakers.append(zone.player_name)
        except Exception as exc:
            logger.error("Error discovering speakers: %s", exc)
        return sorted(speakers)
