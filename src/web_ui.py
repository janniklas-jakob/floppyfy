"""
Flask web interface for managing NFC tag mappings and Sonos settings.

Run with: ``python src/web_ui.py``
Accessible at ``http://<pi-ip>:5000``
"""

import requests
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
def settings() -> str:
    """View and update speaker settings."""
    if request.method == 'POST':
        coordinator = request.form.get('coordinator', '').strip()
        # Get all checked join speakers (Flask returns list for multiple values with same name)
        join_speakers = request.form.getlist('join')
        
        tag_manager.set_setting('speakers', {
            'coordinator': coordinator,
            'join': join_speakers,
        })
        return redirect('/')
    
    # GET request
    speaker_cfg = tag_manager.get_setting('speakers', {})
    available_speakers = sonos.get_available_speakers()
    
    return render_template(
        'settings.html',
        available_speakers=available_speakers,
        current_coordinator=speaker_cfg.get('coordinator'),
        current_join=speaker_cfg.get('join', []),
    )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def get_spotify_image(url: str) -> str | None:
    """Fetch cover art URL from Spotify oEmbed."""
    if 'spotify.com' not in url:
        return None
    try:
        # Spotify oEmbed gives us metadata including thumbnail_url
        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        resp = requests.get(oembed_url, timeout=5)
        if resp.ok:
            return resp.json().get('thumbnail_url')
    except Exception:
        pass
    return None


# ------------------------------------------------------------------
# API / Actions
# ------------------------------------------------------------------

@app.route('/scan_api')
def scan_api():
    """Return the UID of the most recently scanned tag (set by main.py)."""
    latest = tag_manager.get_setting('latest_scanned_uid')
    return jsonify({'uid': latest})


@app.route('/now_playing')
def now_playing():
    """Get currently playing track info from Sonos."""
    # Ensure coordinator is discovered if not already
    if not sonos.coordinator:
        speaker_cfg = tag_manager.get_setting('speakers', {})
        coordinator_name = speaker_cfg.get('coordinator')
        if coordinator_name:
            sonos.discover(coordinator_name, join_names=speaker_cfg.get('join', []))
    
    info = sonos.get_current_track_info()
    return jsonify(info)


@app.route('/next', methods=['POST'])
def next_track():
    """Skip to next track."""
    sonos.next_track()
    return jsonify({'status': 'ok'})


@app.route('/previous', methods=['POST'])
def previous_track():
    """Go back to previous track."""
    sonos.previous_track()
    return jsonify({'status': 'ok'})


@app.route('/add_tag', methods=['POST'])
def add_tag():
    """Create or update a tag mapping."""
    uid = request.form.get('uid', '').strip()
    name = request.form.get('name', '').strip()
    uri = request.form.get('uri', '').strip()
    type_ = request.form.get('type', '').strip()
    shuffle = request.form.get('shuffle') == 'on'

    if uid and name and uri and type_ in VALID_TYPES:
        cover_url = None
        if type_ == 'spotify':
            cover_url = get_spotify_image(uri)

        tag_manager.set_tag(uid, {
            'name': name,
            'uri': uri,
            'type': type_,
            'shuffle': shuffle,
            'cover_url': cover_url
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
