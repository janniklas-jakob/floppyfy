"""
Unit tests for TagManager.

Verifies CRUD operations, atomic saves, and graceful handling of
corrupted or missing database files.
"""

import json
import os
import unittest

from tests.conftest import create_test_db
from tag_manager import TagManager


class TestTagManager(unittest.TestCase):
    """Test persistence and CRUD operations."""

    def setUp(self) -> None:
        self.db_path = create_test_db()
        self.tm = TagManager(db_path=self.db_path)

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    # -- Read ----------------------------------------------------------

    def test_get_existing_tag(self):
        tag = self.tm.get_tag('aa:bb:cc:dd')
        self.assertIsNotNone(tag)
        self.assertEqual(tag['name'], 'Test Album')

    def test_get_nonexistent_tag_returns_none(self):
        self.assertIsNone(self.tm.get_tag('xx:xx:xx:xx'))

    def test_get_all_tags(self):
        tags = self.tm.get_all_tags()
        self.assertEqual(len(tags), 3)
        self.assertIn('ff:ee:dd:cc', tags)

    # -- Write ---------------------------------------------------------

    def test_set_tag_creates_new_entry(self):
        self.tm.set_tag('new:uid', {'name': 'New', 'type': 'file', 'uri': 'http://x'})
        reloaded = TagManager(db_path=self.db_path)
        self.assertIsNotNone(reloaded.get_tag('new:uid'))

    def test_set_tag_overwrites_existing(self):
        self.tm.set_tag('aa:bb:cc:dd', {'name': 'Updated'})
        tag = self.tm.get_tag('aa:bb:cc:dd')
        self.assertEqual(tag['name'], 'Updated')

    # -- Delete --------------------------------------------------------

    def test_delete_existing_tag(self):
        result = self.tm.delete_tag('aa:bb:cc:dd')
        self.assertTrue(result)
        self.assertIsNone(self.tm.get_tag('aa:bb:cc:dd'))

    def test_delete_nonexistent_tag(self):
        result = self.tm.delete_tag('xx:xx:xx:xx')
        self.assertFalse(result)

    # -- Settings ------------------------------------------------------

    def test_get_setting(self):
        speakers = self.tm.get_setting('speakers')
        self.assertEqual(speakers['coordinator'], 'Living Room')

    def test_set_setting_persists(self):
        self.tm.set_setting('custom_key', 42)
        reloaded = TagManager(db_path=self.db_path)
        self.assertEqual(reloaded.get_setting('custom_key'), 42)

    def test_get_setting_default(self):
        self.assertEqual(self.tm.get_setting('nonexistent', 'fallback'), 'fallback')

    # -- Edge cases ----------------------------------------------------

    def test_handles_corrupted_file(self):
        with open(self.db_path, 'w') as f:
            f.write('{invalid json')
        tm = TagManager(db_path=self.db_path)
        self.assertEqual(tm.get_all_tags(), {})

    def test_creates_file_if_missing(self):
        os.unlink(self.db_path)
        tm = TagManager(db_path=self.db_path)
        self.assertTrue(os.path.exists(self.db_path))
        self.assertEqual(tm.get_all_tags(), {})

    def test_atomic_save_produces_valid_json(self):
        self.tm.set_tag('test:uid', {'name': 'Atomic'})
        with open(self.db_path, 'r') as f:
            data = json.load(f)
        self.assertIn('test:uid', data['tags'])

    def test_reload_picks_up_external_edits(self):
        """TagManager should see changes made by other processes (e.g. vim)."""
        with open(self.db_path, 'r') as f:
            data = json.load(f)
        data['tags']['external:uid'] = {'name': 'External'}
        with open(self.db_path, 'w') as f:
            json.dump(data, f)

        tag = self.tm.get_tag('external:uid')
        self.assertIsNotNone(tag)
        self.assertEqual(tag['name'], 'External')


if __name__ == '__main__':
    unittest.main()
