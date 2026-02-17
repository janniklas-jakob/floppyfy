"""
Unit tests for the FloppyfyApp state machine logic.

These tests mock the hardware (NFC, Sonos, Spotify) and verify that the
correct actions are taken for each tag event sequence.
"""
import unittest
from unittest.mock import MagicMock, patch
import time
import json
import tempfile
import os

# We need to patch hardware imports before importing main
import sys
# Mock the hardware-only modules so tests can run on any machine
sys.modules['board'] = MagicMock()
sys.modules['busio'] = MagicMock()
sys.modules['digitalio'] = MagicMock()
sys.modules['adafruit_pn532'] = MagicMock()
sys.modules['adafruit_pn532.i2c'] = MagicMock()
sys.modules['soco'] = MagicMock()
sys.modules['soco.discovery'] = MagicMock()

# Now safe to import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from main import FloppyfyApp


class TestFloppyfyStateMachine(unittest.TestCase):
    """Test the tag detection state machine in isolation."""

    def setUp(self):
        # Create a temp db.json
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, 'db.json')
        db_content = {
            "tags": {
                "aa:bb:cc:dd": {
                    "name": "Test Album",
                    "type": "spotify",
                    "uri": "spotify:album:test123",
                    "shuffle": False
                },
                "11:22:33:44": {
                    "name": "Test Playlist",
                    "type": "spotify",
                    "uri": "spotify:playlist:test456",
                    "shuffle": True
                },
                "ff:ee:dd:cc": {
                    "name": "Local File",
                    "type": "file",
                    "uri": "http://192.168.1.10:8080/song.mp3",
                    "shuffle": False
                }
            },
            "settings": {
                "speakers": {
                    "coordinator": "Living Room",
                    "join": ["Kitchen"]
                }
            }
        }
        with open(self.db_path, 'w') as f:
            json.dump(db_content, f)

        # Patch config to use our temp DB
        with patch('tag_manager.DB_PATH', self.db_path):
            with patch('config.DB_PATH', self.db_path):
                self.app = FloppyfyApp()

        # Replace real services with mocks
        self.app.nfc = MagicMock()
        self.app.sonos = MagicMock()
        self.app.spotify = MagicMock()
        self.app.spotify.get_devices.return_value = {
            'devices': [{'name': 'Living Room', 'id': 'device123'}]
        }

        # Override tag_manager to use tmp path
        self.app.tag_manager.db_path = self.db_path

    def tearDown(self):
        os.unlink(self.db_path)
        os.rmdir(self.tmp_dir)

    def test_new_tag_starts_fresh(self):
        """Placing a new tag should start fresh playback."""
        self.app.nfc.get_uid.return_value = 'aa:bb:cc:dd'
        self.app.loop()

        self.app.spotify.play.assert_called_once()
        self.assertEqual(self.app.current_playback_uid, 'aa:bb:cc:dd')
        self.assertEqual(self.app.current_playback_source, 'spotify')
        self.assertFalse(self.app.is_paused)

    def test_same_tag_holding_does_nothing(self):
        """Holding the same tag down should not trigger repeat plays."""
        self.app.nfc.get_uid.return_value = 'aa:bb:cc:dd'
        self.app.loop()  # First detection
        self.app.spotify.play.reset_mock()

        self.app.loop()  # Same tag, still present
        self.app.spotify.play.assert_not_called()

    def test_tag_removal_pauses_after_debounce(self):
        """Removing a tag should pause after debounce period."""
        # Place tag
        self.app.nfc.get_uid.return_value = 'aa:bb:cc:dd'
        self.app.loop()

        # Remove tag (no UID)
        self.app.nfc.get_uid.return_value = None
        self.app.loop()

        # Debounce not elapsed yet → should NOT pause
        self.app.spotify.pause.assert_not_called()

        # Simulate debounce elapsed
        self.app.tag_gone_since = time.time() - 2.0
        self.app.loop()

        self.app.spotify.pause.assert_called_once()
        self.assertTrue(self.app.is_paused)
        self.assertIsNone(self.app.last_tag_uid)

    def test_same_tag_resumes(self):
        """Putting the same tag back should resume playback."""
        # Place tag A
        self.app.nfc.get_uid.return_value = 'aa:bb:cc:dd'
        self.app.loop()

        # Remove tag A (skip debounce)
        self.app.nfc.get_uid.return_value = None
        self.app.tag_gone_since = time.time() - 2.0
        self.app.loop()

        # Place tag A again
        self.app.nfc.get_uid.return_value = 'aa:bb:cc:dd'
        self.app.spotify.resume.reset_mock()
        self.app.loop()

        self.app.spotify.resume.assert_called_once()
        self.assertFalse(self.app.is_paused)

    def test_different_tag_starts_fresh_not_resume(self):
        """After tag B intervenes, putting tag A back should start fresh."""
        # Place tag A
        self.app.nfc.get_uid.return_value = 'aa:bb:cc:dd'
        self.app.loop()

        # Remove A
        self.app.nfc.get_uid.return_value = None
        self.app.tag_gone_since = time.time() - 2.0
        self.app.loop()

        # Place tag B (different)
        self.app.nfc.get_uid.return_value = '11:22:33:44'
        self.app.loop()
        self.assertEqual(self.app.current_playback_uid, '11:22:33:44')

        # Remove B
        self.app.nfc.get_uid.return_value = None
        self.app.tag_gone_since = time.time() - 2.0
        self.app.loop()

        # Place tag A again → should start FRESH (B intervened)
        self.app.nfc.get_uid.return_value = 'aa:bb:cc:dd'
        self.app.spotify.play.reset_mock()
        self.app.spotify.resume.reset_mock()
        self.app.loop()

        self.app.spotify.play.assert_called_once()
        self.app.spotify.resume.assert_not_called()

    def test_file_type_uses_sonos(self):
        """File-type tags should use SonosClient for playback."""
        self.app.nfc.get_uid.return_value = 'ff:ee:dd:cc'
        self.app.loop()

        self.app.sonos.play_uri.assert_called_once()
        self.assertEqual(self.app.current_playback_source, 'file')

    def test_file_type_resume_uses_sonos(self):
        """Resuming a file-type tag should call sonos.resume()."""
        # Place file tag
        self.app.nfc.get_uid.return_value = 'ff:ee:dd:cc'
        self.app.loop()

        # Remove
        self.app.nfc.get_uid.return_value = None
        self.app.tag_gone_since = time.time() - 2.0
        self.app.loop()

        # Place same file tag again
        self.app.nfc.get_uid.return_value = 'ff:ee:dd:cc'
        self.app.sonos.resume.reset_mock()
        self.app.loop()

        self.app.sonos.resume.assert_called_once()
        self.app.spotify.resume.assert_not_called()

    def test_unknown_tag_ignored(self):
        """An unregistered tag UID should be ignored."""
        self.app.nfc.get_uid.return_value = 'xx:xx:xx:xx'
        self.app.loop()

        self.app.spotify.play.assert_not_called()
        self.app.sonos.play_uri.assert_not_called()
        self.assertIsNone(self.app.current_playback_uid)

    def test_shuffle_passed_correctly(self):
        """Shuffle config should be passed through to Spotify."""
        self.app.nfc.get_uid.return_value = '11:22:33:44'
        self.app.loop()

        call_args = self.app.spotify.play.call_args
        self.assertTrue(call_args[1].get('shuffle') or call_args.kwargs.get('shuffle'))


if __name__ == '__main__':
    unittest.main()
