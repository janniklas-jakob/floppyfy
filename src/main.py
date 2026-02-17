import time
import logging
from tag_manager import TagManager
from config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI
from nfc_service import NFCService
from sonos_client import SonosClient
from spotify_client import SpotifyClient

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FloppyfyApp:
    def __init__(self):
        self.tag_manager = TagManager()
        self.nfc = NFCService()
        self.sonos = SonosClient()
        self.spotify = SpotifyClient(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI)

        # State
        self.last_tag_uid = None          # UID physically on the reader right now (None if empty)
        self.current_playback_uid = None  # UID of the session that is playing / was last playing
        self.current_playback_source = None  # 'spotify' or 'file'
        self.is_paused = False

        # Debounce: track the moment a tag disappears
        self.tag_gone_since = None
        self.REMOVAL_DEBOUNCE_SEC = 1.5

    def run(self):
        logger.info("Floppyfy Service Started.")

        try:
            while True:
                self.loop()
                time.sleep(0.2)
        except KeyboardInterrupt:
            logger.info("Stopping...")

    def loop(self):
        current_uid = self.nfc.get_uid()

        if current_uid:
            # --- TAG PRESENT ---
            self.tag_gone_since = None  # Reset removal timer

            if current_uid != self.last_tag_uid:
                # Edge: new physical placement (or first read after removal)
                self.tag_manager.set_setting('latest_scanned_uid', current_uid)
                logger.info(f"Tag Detected: {current_uid}")

                if current_uid == self.current_playback_uid and self.is_paused:
                    # Same tag returned → RESUME
                    logger.info("Same tag returned. Resuming.")
                    self.resume_playback()
                else:
                    # Different tag (or first ever) → NEW SESSION
                    logger.info("New tag (or different tag). Starting fresh.")
                    self.start_new_session(current_uid)

                self.last_tag_uid = current_uid
                self.is_paused = False
        else:
            # --- NO TAG ---
            if self.last_tag_uid is not None:
                # Tag was present previously → start / continue debounce
                if self.tag_gone_since is None:
                    self.tag_gone_since = time.time()

                elapsed = time.time() - self.tag_gone_since
                if elapsed >= self.REMOVAL_DEBOUNCE_SEC:
                    logger.info(f"Tag {self.last_tag_uid} removed (after {elapsed:.1f}s debounce).")
                    self.pause_playback()
                    self.is_paused = True
                    self.last_tag_uid = None
                    self.tag_gone_since = None

    # ------------------------------------------------------------------ #
    #  Playback helpers
    # ------------------------------------------------------------------ #

    def start_new_session(self, uid):
        tag_config = self.tag_manager.get_tag(uid)

        if not tag_config:
            logger.warning(f"Unknown Tag {uid}. Ignoring.")
            return

        uri = tag_config.get('uri')
        type_ = tag_config.get('type')
        shuffle = tag_config.get('shuffle', False)

        # Speaker config
        speaker_cfg = self.tag_manager.get_setting('speakers', {})
        coordinator_name = speaker_cfg.get('coordinator')
        join_names = speaker_cfg.get('join', [])

        if not coordinator_name:
            logger.warning("No Sonos Coordinator configured in settings.")
            return

        # Discover & group speakers
        self.sonos.discover(coordinator_name, join_names=join_names)

        # Track session
        self.current_playback_uid = uid
        self.current_playback_source = type_

        if type_ == 'spotify':
            logger.info(f"Starting Spotify: {uri}")
            device_id = self._find_spotify_device(coordinator_name)
            if device_id:
                self.spotify.play(uri, device_id=device_id, shuffle=shuffle)
            else:
                logger.error(f"Sonos device '{coordinator_name}' not found in Spotify Connect devices.")

        elif type_ == 'file':
            logger.info(f"Starting File/Stream: {uri}")
            self.sonos.play_uri(uri, shuffle=shuffle)

    def pause_playback(self):
        logger.info("Pausing Playback...")
        if self.current_playback_source == 'spotify':
            self.spotify.pause()
        else:
            self.sonos.pause()

    def resume_playback(self):
        logger.info("Resuming Playback...")
        if self.current_playback_source == 'spotify':
            self.spotify.resume()
        else:
            self.sonos.resume()

    def _find_spotify_device(self, coordinator_name):
        """Look up the Spotify Connect device ID for a Sonos speaker."""
        devices = self.spotify.get_devices()
        if not devices:
            return None
        for d in devices.get('devices', []):
            if coordinator_name.lower() in d['name'].lower():
                return d['id']
        return None


if __name__ == "__main__":
    app = FloppyfyApp()
    app.run()
