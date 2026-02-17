"""
Flask web interface for managing NFC tag mappings and Sonos settings.

Run with: ``python src/web_ui.py``
Accessible at ``http://<pi-ip>:5000``
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify

from config import PlaybackSource
from sonos_client import SonosClient
from tag_manager import TagManager

app = Flask(__name__)
tag_manager = TagManager()
sonos = SonosClient()

VALID_TYPES = {ps.value for ps in PlaybackSource}


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------

@app.route('/')
def index():
    """Tag overview and add-tag form."""
    tags = tag_manager.get_all_tags()
    return render_template('index.html', tags=tags)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Sonos speaker configuration."""
    if request.method == 'POST':
        coordinator = request.form.get('coordinator', '').strip()
        join_raw = request.form.get('join', '')
        join_list = [s.strip() for s in join_raw.split(',') if s.strip()]
        tag_manager.set_setting('speakers', {
            'coordinator': coordinator or None,
            'join': join_list,
        })
        return redirect(url_for('settings'))

    current_settings = tag_manager.get_setting('speakers', {})
    available_speakers = sonos.get_available_speakers()
    return render_template('settings.html', settings=current_settings, speakers=available_speakers)


# ------------------------------------------------------------------
# API / Actions
# ------------------------------------------------------------------

@app.route('/scan_api')
def scan_api():
    """Return the UID of the most recently scanned tag (set by main.py)."""
    latest = tag_manager.get_setting('latest_scanned_uid')
    return jsonify({'uid': latest})


@app.route('/add_tag', methods=['POST'])
def add_tag():
    """Create or update a tag mapping."""
    uid = request.form.get('uid', '').strip()
    name = request.form.get('name', '').strip()
    uri = request.form.get('uri', '').strip()
    type_ = request.form.get('type', '').strip()
    shuffle = request.form.get('shuffle') == 'on'

    if uid and name and uri and type_ in VALID_TYPES:
        tag_manager.set_tag(uid, {
            'name': name,
            'uri': uri,
            'type': type_,
            'shuffle': shuffle,
        })
    return redirect(url_for('index'))


@app.route('/delete_tag', methods=['POST'])
def delete_tag():
    """Delete a tag mapping. Uses POST to avoid CSRF via GET."""
    uid = request.form.get('uid', '')
    tag_manager.delete_tag(uid)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
