# web_server.py

from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading
import logging
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max upload size: 16MB

# Global references to settings and game instance
game_settings = None
game_instance = None

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'wav', 'ttf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game')
def game():
    # Fetch current game status
    stats = game_instance.get_game_status()
    return render_template('game.html', stats=stats)

@app.route('/game_data')
def game_data():
    # Return game data as JSON for live updates
    stats = game_instance.get_game_status()
    return jsonify(stats)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # Update game settings
        for key in ['period_length', 'overtime_length', 'intermission_length', 'power_up_frequency', 'taunt_frequency']:
            value = request.form.get(key)
            if value is not None and hasattr(game_settings, key):
                setattr(game_settings, key, type(getattr(game_settings, key))(value))
        game_settings.save_settings()
        logging.info('Game settings updated via web interface')
        return redirect(url_for('settings'))
    return render_template('settings.html', settings=vars(game_settings))

@app.route('/system_settings', methods=['GET', 'POST'])
def system_settings():
    if request.method == 'POST':
        # Update system settings
        for key in ['screen_width', 'screen_height', 'bg_color', 'mqtt_broker', 'mqtt_port', 'mqtt_topic', 'web_server_port']:
            value = request.form.get(key)
            if value is not None and hasattr(game_settings, key):
                if key == 'bg_color':
                    value = tuple(map(int, value.strip('()').split(',')))
                setattr(game_settings, key, type(getattr(game_settings, key))(value))
        game_settings.save_settings()
        logging.info('System settings updated via web interface')
        return redirect(url_for('system_settings'))
    return render_template('system_settings.html', settings=vars(game_settings))

@app.route('/themes', methods=['GET', 'POST'])
def theme_manager():
    themes_dir = 'assets/themes/'
    available_themes = [d for d in os.listdir(themes_dir) if os.path.isdir(os.path.join(themes_dir, d))]
    if request.method == 'POST':
        if 'theme_name' in request.form:
            theme_name = secure_filename(request.form['theme_name'])
            theme_path = os.path.join(themes_dir, theme_name)
            os.makedirs(theme_path, exist_ok=True)
            os.makedirs(os.path.join(theme_path, 'images'), exist_ok=True)
            os.makedirs(os.path.join(theme_path, 'sounds'), exist_ok=True)
            os.makedirs(os.path.join(theme_path, 'fonts'), exist_ok=True)
            # Save uploaded files
            for file_field in request.files:
                file = request.files[file_field]
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    if file_field.startswith('image_'):
                        file.save(os.path.join(theme_path, 'images', filename))
                    elif file_field.startswith('sound_'):
                        file.save(os.path.join(theme_path, 'sounds', filename))
                    elif file_field.startswith('font_'):
                        file.save(os.path.join(theme_path, 'fonts', filename))
            logging.info(f'Theme {theme_name} created via web interface')
            return redirect(url_for('theme_manager'))
        elif 'selected_theme' in request.form:
            selected_theme = request.form.get('selected_theme')
            if selected_theme in available_themes:
                game_settings.current_theme = selected_theme
                game_settings.save_settings()
                game_instance.load_assets()
                logging.info(f'Theme changed to {selected_theme}')
            return redirect(url_for('theme_manager'))
    return render_template('theme_manager.html', themes=available_themes, current_theme=game_settings.current_theme)

def run_web_server(settings, game):
    global game_settings
    global game_instance
    game_settings = settings
    game_instance = game
    app.run(host='0.0.0.0', port=settings.web_server_port)
