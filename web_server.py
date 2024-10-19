# web_server.py

from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading
import logging
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max upload size: 16MB

# Global references to settings and game instance
game_settings = None
game_instance = None

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'wav', 'ttf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_available_assets(directory):
    assets = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if allowed_file(file):
                asset_path = os.path.relpath(os.path.join(root, file), directory)
                assets.append(asset_path)
    return assets

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game')
def game():
    # Fetch current game status
    return render_template('game.html')

@app.route('/game_data')
def game_data():
    # Return game data as JSON for live updates
    stats = game_instance.get_game_status()
    return jsonify(stats)

@app.route('/settings', methods=['GET', 'POST'])
def settings_route():
    if request.method == 'POST':
        # Update game settings
        for key in [
            'period_length', 'overtime_length', 'intermission_length',
            'power_up_frequency', 'taunt_frequency',
            'taunts_enabled', 'random_sounds_enabled', 'random_sound_frequency',
            'combo_goals_enabled', 'combo_time_window', 'combo_reward_type', 'combo_max_stack'
        ]:
            value = request.form.get(key)
            if value is not None and hasattr(game_settings, key):
                attr_type = type(getattr(game_settings, key))
                if attr_type is bool:
                    setattr(game_settings, key, value == 'on')
                else:
                    setattr(game_settings, key, attr_type(value))
        game_settings.save_settings()
        logging.info('Game settings updated via web interface')
        return redirect(url_for('settings_route'))
    return render_template('settings.html', settings=vars(game_settings))

@app.route('/system_settings', methods=['GET', 'POST'])
def system_settings():
    if request.method == 'POST':
        # Update system settings
        for key in ['screen_width', 'screen_height', 'bg_color', 'mqtt_broker', 'mqtt_port', 'mqtt_topic', 'web_server_port', 'classic_mode_theme_selection']:
            value = request.form.get(key)
            if value is not None and hasattr(game_settings, key):
                if key == 'bg_color':
                    try:
                        value = tuple(map(int, value.strip('()').split(',')))
                    except:
                        value = (0, 0, 0)  # Default color
                elif key == 'classic_mode_theme_selection':
                    value = value == 'on'
                setattr(game_settings, key, type(getattr(game_settings, key))(value))
        game_settings.save_settings()
        logging.info('System settings updated via web interface')
        return redirect(url_for('system_settings'))
    return render_template('system_settings.html', settings=vars(game_settings))

@app.route('/themes', methods=['GET', 'POST'])
def theme_manager():
    themes_dir = 'assets/themes/'
    assets_dir = 'assets/'
    available_themes = [d for d in os.listdir(themes_dir) if os.path.isdir(os.path.join(themes_dir, d))]
    available_images = get_available_assets(os.path.join(assets_dir, 'common/images'))
    available_sounds = get_available_assets(os.path.join(assets_dir, 'common/sounds'))
    available_fonts = get_available_assets(os.path.join(assets_dir, 'fonts'))

    if request.method == 'POST':
        if 'theme_name' in request.form:
            # Create a new theme
            theme_name = secure_filename(request.form['theme_name'])
            theme_path = os.path.join(themes_dir, theme_name)
            if os.path.exists(theme_path):
                logging.warning(f"Theme {theme_name} already exists.")
                return redirect(url_for('theme_manager'))
            os.makedirs(theme_path, exist_ok=True)
            os.makedirs(os.path.join(theme_path, 'images'), exist_ok=True)
            os.makedirs(os.path.join(theme_path, 'sounds'), exist_ok=True)
            os.makedirs(os.path.join(theme_path, 'fonts'), exist_ok=True)
            # Save uploaded files and update theme configuration
            theme_config = {'name': theme_name, 'assets': {}}
            for key in request.form:
                if key.startswith('asset_'):
                    asset_type = key.replace('asset_', '')
                    asset_value = request.form[key]
                    if asset_value != '':
                        theme_config['assets'][asset_type] = asset_value
            for file_field in request.files:
                file = request.files[file_field]
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    if file_field.startswith('upload_image_'):
                        file.save(os.path.join(theme_path, 'images', filename))
                        asset_name = file_field.replace('upload_image_', '')
                        theme_config['assets'][asset_name] = f'images/{filename}'
                    elif file_field.startswith('upload_sound_'):
                        file.save(os.path.join(theme_path, 'sounds', filename))
                        asset_name = file_field.replace('upload_sound_', '')
                        theme_config['assets'][asset_name] = f'sounds/{filename}'
                    elif file_field.startswith('upload_font_'):
                        file.save(os.path.join(theme_path, 'fonts', filename))
                        asset_name = file_field.replace('upload_font_', '')
                        theme_config['assets'][asset_name] = f'fonts/{filename}'
            # Save theme configuration
            with open(os.path.join(theme_path, 'theme.json'), 'w') as f:
                json.dump(theme_config, f, indent=4)
            logging.info(f'Theme {theme_name} created via web interface')
            return redirect(url_for('theme_manager'))
        elif 'selected_theme' in request.form:
            # Activate an existing theme
            selected_theme = request.form.get('selected_theme')
            if selected_theme in available_themes:
                game_settings.current_theme = selected_theme
                game_settings.save_settings()
                if game_instance:
                    game_instance.load_assets()
                logging.info(f'Theme changed to {selected_theme}')
            return redirect(url_for('theme_manager'))
    return render_template('theme_manager.html',
                           themes=available_themes,
                           current_theme=game_settings.current_theme,
                           available_images=available_images,
                           available_sounds=available_sounds,
                           available_fonts=available_fonts)

@app.route('/export_theme/<theme_name>')
def export_theme(theme_name):
    theme_path = os.path.join('assets/themes/', theme_name)
    if not os.path.exists(theme_path):
        return "Theme not found", 404

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for root, dirs, files in os.walk(theme_path):
            for file in files:
                zf.write(os.path.join(root, file), 
                         os.path.relpath(os.path.join(root, file), theme_path))

    memory_file.seek(0)
    return send_file(memory_file, 
                     attachment_filename=f'{theme_name}.zip', 
                     as_attachment=True)

@app.route('/import_theme', methods=['POST'])
def import_theme():
    if 'theme_file' not in request.files:
        return "No file part", 400
    file = request.files['theme_file']
    if file.filename == '':
        return "No selected file", 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        theme_name = os.path.splitext(filename)[0]
        theme_path = os.path.join('assets/themes/', theme_name)
        
        with zipfile.ZipFile(file) as zf:
            zf.extractall(theme_path)
        
        return "Theme imported successfully", 200
    return "Invalid file", 400

@app.route('/theme_preview/<theme_id>')
def theme_preview(theme_id):
    # Load theme data
    theme_path = os.path.join('assets/themes/', theme_id, 'theme.json')
    with open(theme_path, 'r') as f:
        theme_data = json.load(f)
    
    # Render a preview based on theme data
    return render_template('theme_preview.html', theme=theme_data)

def run_web_server(settings, game):
    global game_settings
    global game_instance
    game_settings = settings
    game_instance = game
    app.run(host='0.0.0.0', port=settings.web_server_port)
