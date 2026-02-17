import logging
import soco
from soco.discovery import by_name

logger = logging.getLogger(__name__)


class SonosClient:
    def __init__(self):
        self.coordinator = None
        self.joined_speakers = []

    def discover(self, coordinator_name, join_names=None):
        """Discover speakers and set up groups."""
        logger.info(f"Discovering Sonos speakers. Target Coordinator: {coordinator_name}")

        # Find Coordinator
        self.coordinator = by_name(coordinator_name)
        if not self.coordinator:
            logger.error(f"Could not find speaker named '{coordinator_name}'")
            return False

        # Find and Join others
        self.joined_speakers = []
        if join_names:
            for name in join_names:
                speaker = by_name(name)
                if speaker and speaker != self.coordinator:
                    logger.info(f"Joining {name} to {coordinator_name}")
                    speaker.join(self.coordinator)
                    self.joined_speakers.append(speaker)
                elif not speaker:
                    logger.warning(f"Could not find join-target speaker '{name}'")

        return True

    def play_uri(self, uri, shuffle=False):
        """Play a local/HTTP URI on the Sonos queue."""
        if not self.coordinator:
            logger.error("No coordinator selected")
            return

        try:
            self.coordinator.stop()
            self.coordinator.clear_queue()

            self.coordinator.add_uri_to_queue(uri)

            if shuffle:
                self.coordinator.play_mode = 'SHUFFLE'
            else:
                self.coordinator.play_mode = 'NORMAL'

            self.coordinator.play_from_queue(0)
        except Exception as e:
            logger.error(f"Error starting playback: {e}")

    def pause(self):
        if self.coordinator:
            try:
                self.coordinator.pause()
            except Exception as e:
                logger.error(f"Error pausing: {e}")

    def resume(self):
        if self.coordinator:
            try:
                self.coordinator.play()
            except Exception as e:
                logger.error(f"Error resuming: {e}")

    def get_available_speakers(self):
        """Return a list of all discovered Sonos speaker names."""
        speakers = []
        try:
            for zone in soco.discover(timeout=5) or []:
                speakers.append(zone.player_name)
        except Exception as e:
            logger.error(f"Error discovering speakers: {e}")
        return sorted(speakers)
