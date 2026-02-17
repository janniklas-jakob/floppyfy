"""
Unit tests for the FloppyfyApp state machine.

Tests mock all hardware (NFC, Sonos, Spotify) and verify that the
correct actions are taken for each tag-event sequence defined in the
implementation plan's *Intervening Tag Rule*.
"""

import os
import time
import unittest
from unittest.mock import MagicMock

from tests.conftest import create_test_db

# Now safe to import application code (hardware modules are lazy-loaded)
from config import PlaybackSource
from tag_manager import TagManager
from main import FloppyfyApp


class TestFloppyfyStateMachine(unittest.TestCase):
    """Test the tag detection state machine in isolation."""

    def setUp(self) -> None:
        self.db_path = create_test_db()

        nfc = MagicMock()
        sonos = MagicMock()
        spotify = MagicMock()
        spotify.get_devices.return_value = {
            'devices': [{'name': 'Living Room', 'id': 'device123'}],
        }

        self.app = FloppyfyApp(
            tag_manager=TagManager(db_path=self.db_path),
            nfc=nfc,
            sonos=sonos,
            spotify=spotify,
        )

    def tearDown(self) -> None:
        os.unlink(self.db_path)

    # -- helpers -------------------------------------------------------

    def _place(self, uid: str) -> None:
        self.app.nfc.get_uid.return_value = uid
        self.app.tick()

    def _remove_with_debounce(self) -> None:
        self.app.nfc.get_uid.return_value = None
        self.app.tag_gone_since = time.time() - 2.0
        self.app.tick()

    # -- tests ---------------------------------------------------------

    def test_new_tag_starts_fresh(self):
        """Placing a new tag should start fresh playback."""
        self._place('aa:bb:cc:dd')

        self.app.spotify.play.assert_called_once()
        self.assertEqual(self.app.current_playback_uid, 'aa:bb:cc:dd')
        self.assertEqual(self.app.current_playback_source, PlaybackSource.SPOTIFY)
        self.assertFalse(self.app.is_paused)

    def test_same_tag_holding_does_nothing(self):
        """Holding the same tag should not trigger repeat plays."""
        self._place('aa:bb:cc:dd')
        self.app.spotify.play.reset_mock()

        self._place('aa:bb:cc:dd')  # still there
        self.app.spotify.play.assert_not_called()

    def test_tag_removal_debounce(self):
        """Tag must be absent for the debounce period before pausing."""
        self._place('aa:bb:cc:dd')

        # Remove tag — first poll starts debounce
        self.app.nfc.get_uid.return_value = None
        self.app.tick()
        self.app.spotify.pause.assert_not_called()

        # Simulate debounce elapsed
        self.app.tag_gone_since = time.time() - 2.0
        self.app.tick()

        self.app.spotify.pause.assert_called_once()
        self.assertTrue(self.app.is_paused)
        self.assertIsNone(self.app.last_tag_uid)

    def test_same_tag_resumes(self):
        """Putting the same tag back should resume, not restart."""
        self._place('aa:bb:cc:dd')
        self._remove_with_debounce()

        self.app.spotify.resume.reset_mock()
        self._place('aa:bb:cc:dd')

        self.app.spotify.resume.assert_called_once()
        self.assertFalse(self.app.is_paused)

    def test_different_tag_starts_fresh_not_resume(self):
        """After tag B intervenes, tag A must start fresh."""
        self._place('aa:bb:cc:dd')
        self._remove_with_debounce()

        self._place('11:22:33:44')
        self.assertEqual(self.app.current_playback_uid, '11:22:33:44')

        self._remove_with_debounce()

        self.app.spotify.play.reset_mock()
        self.app.spotify.resume.reset_mock()
        self._place('aa:bb:cc:dd')

        self.app.spotify.play.assert_called_once()
        self.app.spotify.resume.assert_not_called()

    def test_file_type_uses_sonos(self):
        """File-type tags should play via SonosClient."""
        self._place('ff:ee:dd:cc')

        self.app.sonos.play_uri.assert_called_once()
        self.assertEqual(self.app.current_playback_source, PlaybackSource.FILE)

    def test_file_type_pause_uses_sonos(self):
        """Pausing a file-type tag should use sonos.pause()."""
        self._place('ff:ee:dd:cc')
        self._remove_with_debounce()

        self.app.sonos.pause.assert_called_once()
        self.app.spotify.pause.assert_not_called()

    def test_file_type_resume_uses_sonos(self):
        """Resuming a file-type tag should use sonos.resume()."""
        self._place('ff:ee:dd:cc')
        self._remove_with_debounce()

        self.app.sonos.resume.reset_mock()
        self._place('ff:ee:dd:cc')

        self.app.sonos.resume.assert_called_once()
        self.app.spotify.resume.assert_not_called()

    def test_unknown_tag_ignored(self):
        """An unregistered tag UID should be ignored."""
        self._place('xx:xx:xx:xx')

        self.app.spotify.play.assert_not_called()
        self.app.sonos.play_uri.assert_not_called()
        self.assertIsNone(self.app.current_playback_uid)

    def test_shuffle_passed_correctly(self):
        """Shuffle config should be forwarded to Spotify."""
        self._place('11:22:33:44')

        _, kwargs = self.app.spotify.play.call_args
        self.assertTrue(kwargs.get('shuffle'))

    def test_join_speakers_forwarded(self):
        """Join speaker names should be forwarded to sonos.discover()."""
        self._place('aa:bb:cc:dd')

        call_kwargs = self.app.sonos.discover.call_args[1]
        self.assertEqual(call_kwargs['join_names'], ['Kitchen'])


if __name__ == '__main__':
    unittest.main()
