from flask import Flask, render_template, request, redirect, url_for, jsonify
from tag_manager import TagManager
from sonos_client import SonosClient

app = Flask(__name__)
tag_manager = TagManager()
sonos = SonosClient()


@app.route('/')
def index():
    tags = tag_manager.get_all_tags()
    return render_template('index.html', tags=tags)


@app.route('/scan_api')
def scan_api():
    latest = tag_manager.get_setting('latest_scanned_uid')
    return jsonify({'uid': latest})


@app.route('/add_tag', methods=['POST'])
def add_tag():
    uid = request.form.get('uid')
    name = request.form.get('name')
    uri = request.form.get('uri')
    type_ = request.form.get('type')
    shuffle = request.form.get('shuffle') == 'on'

    if uid and name and uri:
        tag_manager.set_tag(uid, {
            'name': name,
            'uri': uri,
            'type': type_,
            'shuffle': shuffle
        })
    return redirect(url_for('index'))


@app.route('/delete_tag/<uid>')
def delete_tag(uid):
    tag_manager.delete_tag(uid)
    return redirect(url_for('index'))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        coordinator = request.form.get('coordinator')
        join_raw = request.form.get('join', '')
        join_list = [s.strip() for s in join_raw.split(',') if s.strip()]
        tag_manager.set_setting('speakers', {
            'coordinator': coordinator,
            'join': join_list
        })
        return redirect(url_for('settings'))

    current_settings = tag_manager.get_setting('speakers', {})
    available_speakers = sonos.get_available_speakers()
    return render_template('settings.html', settings=current_settings, speakers=available_speakers)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
