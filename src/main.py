"""
Main application — NFC tag detection loop with playback control.

Polls the NFC reader every :data:`config.NFC_POLL_INTERVAL_SEC` seconds.
When a tag is detected or removed, playback is started / paused / resumed
according to the *Intervening Tag Rule* documented in the implementation
plan.
"""

import logging
import time
from typing import Optional

from config import (
    NFC_POLL_INTERVAL_SEC,
    TAG_REMOVAL_DEBOUNCE_SEC,
    PlaybackSource,
)
from nfc_service import NFCService
from sonos_client import SonosClient
from tag_manager import TagManager

logger = logging.getLogger(__name__)


class FloppyfyApp:
    """Core event loop: detect NFC tags and drive Sonos / Spotify."""

    def __init__(
        self,
        tag_manager: Optional[TagManager] = None,
        nfc: Optional[NFCService] = None,
        sonos: Optional[SonosClient] = None,
    ) -> None:
        self.tag_manager = tag_manager or TagManager()
        self.nfc = nfc or NFCService()
        self.sonos = sonos or SonosClient()

        # --- State machine ---
        self.last_tag_uid: Optional[str] = None
        self.current_playback_uid: Optional[str] = None
        self.current_playback_source: Optional[PlaybackSource] = None
        self.is_paused: bool = False

        # Debounce: timestamp when the tag first disappeared
        self.tag_gone_since: Optional[float] = None
        
        # Track speaker settings to detect changes while tag is present
        self.last_speaker_config: Optional[dict] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Block forever, polling the NFC reader."""
        logger.info("Floppyfy service started.")
        try:
            while True:
                self.tick()
                time.sleep(NFC_POLL_INTERVAL_SEC)
        except KeyboardInterrupt:
            logger.info("Stopping…")

    def tick(self) -> None:
        """Execute one iteration of the event loop (public for testing)."""
        current_uid = self.nfc.get_uid()

        if current_uid:
            self._handle_tag_present(current_uid)
        else:
            self._handle_tag_absent()

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _handle_tag_present(self, uid: str) -> None:
        self.tag_gone_since = None  # reset removal timer

        # Detect if speaker settings changed while the same tag is still present
        speaker_cfg = self.tag_manager.get_setting('speakers', {})
        settings_changed = (speaker_cfg != self.last_speaker_config)

        if uid == self.last_tag_uid:
            if settings_changed and not self.is_paused:
                logger.info("Speaker settings changed — updating groups.")
                self._start_new_session(uid) # Re-run to apply new group config
            return

        # Edge: new physical placement
        self.tag_manager.set_setting('latest_scanned_uid', uid)
        logger.info("Tag detected: %s", uid)

        if uid == self.current_playback_uid and self.is_paused:
            logger.info("Same tag returned — resuming.")
            # If settings changed while paused, we should re-group before resuming
            if settings_changed:
                self._start_new_session(uid)
            else:
                self._resume_playback()
        else:
            logger.info("New session — starting fresh.")
            self._start_new_session(uid)

        self.last_tag_uid = uid
        self.last_speaker_config = speaker_cfg
        self.is_paused = False

    def _handle_tag_absent(self) -> None:
        if self.last_tag_uid is None:
            return  # reader was already empty

        if self.tag_gone_since is None:
            self.tag_gone_since = time.time()

        elapsed = time.time() - self.tag_gone_since
        if elapsed >= TAG_REMOVAL_DEBOUNCE_SEC:
            logger.info("Tag %s removed (%.1fs debounce).", self.last_tag_uid, elapsed)
            self._pause_playback()
            self.is_paused = True
            self.last_tag_uid = None
            self.tag_gone_since = None

    # ------------------------------------------------------------------
    # Playback helpers
    # ------------------------------------------------------------------

    def _start_new_session(self, uid: str) -> None:
        tag_config = self.tag_manager.get_tag(uid)
        if not tag_config:
            logger.warning("Unknown tag %s — ignoring.", uid)
            return

        uri: str = tag_config['uri']
        source = PlaybackSource(tag_config.get('type', PlaybackSource.SPOTIFY))
        shuffle: bool = tag_config.get('shuffle', False)

        speaker_cfg = self.tag_manager.get_setting('speakers', {})
        coordinator_name: Optional[str] = speaker_cfg.get('coordinator')
        join_names: list[str] = speaker_cfg.get('join', [])

        if not coordinator_name:
            logger.warning("No Sonos coordinator configured — cannot play.")
            return

        self.last_speaker_config = speaker_cfg
        if not self.sonos.discover(coordinator_name, join_names=join_names):
            return

        self.current_playback_uid = uid
        self.current_playback_source = source

        if source is PlaybackSource.SPOTIFY:
            self._play_spotify(uri, coordinator_name, shuffle)
        elif source is PlaybackSource.FILE:
            logger.info("Starting file/stream: %s", uri)
            self.sonos.play_uri(uri, shuffle=shuffle)

    def _play_spotify(self, uri: str, coordinator_name: str, shuffle: bool) -> None:
        logger.info("Starting Spotify via Sonos API: %s", uri)
        self.sonos.play_spotify(uri, shuffle=shuffle)

    def _pause_playback(self) -> None:
        logger.info("Pausing playback…")
        # Since we now drive everything through the Sonos API, 
        # we can use the same pause command for all sources.
        self.sonos.pause()

    def _resume_playback(self) -> None:
        logger.info("Resuming playback…")
        self.sonos.resume()




if __name__ == "__main__":
    FloppyfyApp().run()
