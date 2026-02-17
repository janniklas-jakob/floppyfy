import json
import logging
import os
from config import DB_PATH

logger = logging.getLogger(__name__)

class TagManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._load_db()

    def _load_db(self):
        if not os.path.exists(self.db_path):
            self.data = {"tags": {}, "settings": {}}
            self._save_db()
        else:
            try:
                with open(self.db_path, 'r') as f:
                    self.data = json.load(f)
            except json.JSONDecodeError:
                logger.error("Failed to decode DB.json, creating new empty DB.")
                self.data = {"tags": {}, "settings": {}}

    def _save_db(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_tag(self, uid):
        self._load_db() # Reload to get manual edits
        return self.data.get('tags', {}).get(uid)

    def set_tag(self, uid, data):
        self._load_db()
        if 'tags' not in self.data:
            self.data['tags'] = {}
        self.data['tags'][uid] = data
        self._save_db()

    def get_setting(self, key, default=None):
        self._load_db()
        return self.data.get('settings', {}).get(key, default)

    def set_setting(self, key, value):
        self._load_db()
        if 'settings' not in self.data:
            self.data['settings'] = {}
        self.data['settings'][key] = value
        self._save_db()
    
    def get_all_tags(self):
        self._load_db()
        return self.data.get('tags', {})

    def delete_tag(self, uid):
        self._load_db()
        if 'tags' in self.data and uid in self.data['tags']:
            del self.data['tags'][uid]
            self._save_db()
