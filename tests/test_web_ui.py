"""
Unit tests for the Flask web UI routes.
"""

import json
import os
import unittest

from tests.conftest import create_test_db
from tag_manager import TagManager
from web_ui import app


class TestWebUI(unittest.TestCase):
    """Test HTTP routes of the web interface."""

    def setUp(self) -> None:
        self.db_path = create_test_db()
        # Inject test TagManager and a mock SonosClient into the Flask app module
        import web_ui
        from unittest.mock import MagicMock
        web_ui.tag_manager = TagManager(db_path=self.db_path)
        web_ui.sonos = MagicMock()
        web_ui.sonos.get_available_speakers.return_value = ['Living Room', 'Kitchen']

        self.client = app.test_client()
        app.config['TESTING'] = True

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    # -- Index ---------------------------------------------------------

    def test_index_returns_200(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Floppyfy', resp.data)

    def test_index_shows_existing_tags(self):
        resp = self.client.get('/')
        self.assertIn(b'Test Album', resp.data)
        self.assertIn(b'aa:bb:cc:dd', resp.data)

    # -- Add Tag -------------------------------------------------------

    def test_add_tag_redirects(self):
        resp = self.client.post('/add_tag', data={
            'uid': 'new:uid',
            'name': 'New Tag',
            'uri': 'spotify:album:xyz',
            'type': 'spotify',
        })
        self.assertEqual(resp.status_code, 302)

    def test_add_tag_persists_to_db(self):
        self.client.post('/add_tag', data={
            'uid': 'new:uid',
            'name': 'New Tag',
            'uri': 'spotify:album:xyz',
            'type': 'spotify',
        })
        with open(self.db_path) as f:
            data = json.load(f)
        self.assertIn('new:uid', data['tags'])
        self.assertEqual(data['tags']['new:uid']['name'], 'New Tag')

    def test_add_tag_validates_type(self):
        """An invalid type should be rejected (no tag created)."""
        self.client.post('/add_tag', data={
            'uid': 'bad:uid',
            'name': 'Bad',
            'uri': 'spotify:album:xyz',
            'type': 'INVALID',
        })
        with open(self.db_path) as f:
            data = json.load(f)
        self.assertNotIn('bad:uid', data['tags'])

    def test_add_tag_with_shuffle(self):
        self.client.post('/add_tag', data={
            'uid': 'shuf:uid',
            'name': 'Shuffled',
            'uri': 'spotify:playlist:abc',
            'type': 'spotify',
            'shuffle': 'on',
        })
        with open(self.db_path) as f:
            data = json.load(f)
        self.assertTrue(data['tags']['shuf:uid']['shuffle'])

    # -- Delete Tag ----------------------------------------------------

    def test_delete_tag_via_post(self):
        resp = self.client.post('/delete_tag', data={'uid': 'aa:bb:cc:dd'})
        self.assertEqual(resp.status_code, 302)
        with open(self.db_path) as f:
            data = json.load(f)
        self.assertNotIn('aa:bb:cc:dd', data['tags'])

    def test_delete_via_get_not_allowed(self):
        resp = self.client.get('/delete_tag')
        self.assertEqual(resp.status_code, 405)

    # -- Scan API ------------------------------------------------------

    def test_scan_api_returns_json(self):
        resp = self.client.get('/scan_api')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('uid', data)

    # -- Settings ------------------------------------------------------

    def test_settings_returns_200(self):
        resp = self.client.get('/settings')
        self.assertEqual(resp.status_code, 200)

    def test_settings_post_saves_speakers(self):
        self.client.post('/settings', data={
            'coordinator': 'Bedroom',
            'join': 'Kitchen, Bathroom',
        })
        with open(self.db_path) as f:
            data = json.load(f)
        self.assertEqual(data['settings']['speakers']['coordinator'], 'Bedroom')
        self.assertEqual(data['settings']['speakers']['join'], ['Kitchen', 'Bathroom'])


if __name__ == '__main__':
    unittest.main()
