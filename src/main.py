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
from spotify_client import SpotifyClient
from tag_manager import TagManager

logger = logging.getLogger(__name__)


class FloppyfyApp:
    """Core event loop: detect NFC tags and drive Sonos / Spotify."""

    def __init__(
        self,
        tag_manager: Optional[TagManager] = None,
        nfc: Optional[NFCService] = None,
        sonos: Optional[SonosClient] = None,
        spotify: Optional[SpotifyClient] = None,
    ) -> None:
        self.tag_manager = tag_manager or TagManager()
        self.nfc = nfc or NFCService()
        self.sonos = sonos or SonosClient()
        self.spotify = spotify or SpotifyClient()

        # --- State machine ---
        self.last_tag_uid: Optional[str] = None
        self.current_playback_uid: Optional[str] = None
        self.current_playback_source: Optional[PlaybackSource] = None
        self.is_paused: bool = False

        # Debounce: timestamp when the tag first disappeared
        self.tag_gone_since: Optional[float] = None

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

        if uid == self.last_tag_uid:
            return  # tag is still being held — nothing to do

        # Edge: new physical placement
        self.tag_manager.set_setting('latest_scanned_uid', uid)
        logger.info("Tag detected: %s", uid)

        if uid == self.current_playback_uid and self.is_paused:
            logger.info("Same tag returned — resuming.")
            self._resume_playback()
        else:
            logger.info("New session — starting fresh.")
            self._start_new_session(uid)

        self.last_tag_uid = uid
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

        self.sonos.discover(coordinator_name, join_names=join_names)

        self.current_playback_uid = uid
        self.current_playback_source = source

        if source is PlaybackSource.SPOTIFY:
            self._play_spotify(uri, coordinator_name, shuffle)
        elif source is PlaybackSource.FILE:
            logger.info("Starting file/stream: %s", uri)
            self.sonos.play_uri(uri, shuffle=shuffle)

    def _play_spotify(self, uri: str, coordinator_name: str, shuffle: bool) -> None:
        logger.info("Starting Spotify: %s", uri)
        device_id = self._find_spotify_device(coordinator_name)
        if device_id:
            self.spotify.play(uri, device_id=device_id, shuffle=shuffle)
        else:
            logger.error(
                "Sonos device '%s' not found in Spotify Connect device list.",
                coordinator_name,
            )

    def _pause_playback(self) -> None:
        logger.info("Pausing playback…")
        if self.current_playback_source is PlaybackSource.SPOTIFY:
            self.spotify.pause()
        else:
            self.sonos.pause()

    def _resume_playback(self) -> None:
        logger.info("Resuming playback…")
        if self.current_playback_source is PlaybackSource.SPOTIFY:
            self.spotify.resume()
        else:
            self.sonos.resume()

    def _find_spotify_device(self, coordinator_name: str) -> Optional[str]:
        """Return the Spotify Connect device id for *coordinator_name* caching it."""
        devices = self.spotify.get_devices()
        available_names = []
        
        for dev in devices.get('devices', []):
            available_names.append(dev['name'])
            if coordinator_name.lower() in dev['name'].lower():
                dev_id = dev['id']
                # Cache the ID. Sonos devices often disappear from the active
                # list when they go into standby or TV mode. Transferring 
                # playback to a cached ID wakes them up successfully!
                self.tag_manager.set_setting('spotify_device_id', dev_id)
                return dev_id
                
        cached_id = self.tag_manager.get_setting('spotify_device_id')
        if cached_id:
            logger.info(
                "Sonos '%s' not in active Spotify devices list. Using cached device ID.", 
                coordinator_name
            )
            return cached_id
            
        logger.error(
            "Sonos device '%s' not found. Available Spotify devices: %s. "
            "TIP: Open the Spotify app and play something on the Sonos speaker "
            "once so Floppyfy can learn its device ID!",
            coordinator_name,
            available_names,
        )
        return None


if __name__ == "__main__":
    FloppyfyApp().run()
