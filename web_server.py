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
    return render_template('game.html')

@app.route('/game_data')
def game_data():
    """Return game data as JSON for live updates"""
    if not game_instance:
        return jsonify({'error': 'Game not initialized'})
        
    # Get basic game status
    stats = game_instance.get_game_status()
    
    # Add analytics data if available
    if hasattr(game_instance, 'current_analysis') and game_instance.current_analysis:
        stats['analytics'] = {
            'win_probability': game_instance.current_analysis['win_probability'],
            'momentum': game_instance.current_analysis['momentum']['current_state'],
            'is_critical_moment': game_instance.current_analysis['is_critical_moment'],
            'patterns': {
                'scoring_runs': game_instance.current_analysis['patterns'].get('scoring_runs', {}),
                'goal_distribution': game_instance.current_analysis['patterns'].get('goal_distribution', {}),
                'timing_patterns': game_instance.current_analysis['patterns'].get('timing_patterns', {})
            }
        }
    
    return jsonify(stats)

@app.route('/analytics/<int:game_id>')
def get_game_analytics(game_id):
    """Get detailed analytics for a specific game"""
    if not game_instance or not game_instance.db:
        return jsonify({'error': 'Database not initialized'})
        
    try:
        # Get analytics history
        analytics_history = game_instance.db.get_analytics_history(game_id)
        
        # Get scoring patterns
        scoring_patterns = game_instance.db.get_scoring_patterns(game_id)
        
        # Get game stats
        game_stats = game_instance.db.get_game_stats(game_id)
        
        return jsonify({
            'analytics_history': analytics_history,
            'scoring_patterns': scoring_patterns,
            'game_stats': game_stats
        })
    except Exception as e:
        logging.error(f"Error getting game analytics: {e}")
        return jsonify({'error': 'Failed to retrieve analytics data'})

@app.route('/settings', methods=['GET', 'POST'])
def settings_route():
    if request.method == 'POST':
        # Update game settings
        for key in [
            'period_length', 'overtime_length', 'intermission_length',
            'power_up_frequency', 'taunt_frequency',
            'taunts_enabled', 'random_sounds_enabled',
            'random_sound_min_interval', 'random_sound_max_interval',
            'combo_goals_enabled', 'combo_time_window', 
            'combo_reward_type', 'combo_max_stack',
            'show_analytics_overlay'  # New setting for analytics display
        ]:
            value = request.form.get(key)
            if value is not None and hasattr(game_settings, key):
                attr_type = type(getattr(game_settings, key))
                if attr_type is bool:
                    setattr(game_settings, key, value == 'on')
                elif attr_type is int:
                    setattr(game_settings, key, int(value))
                elif attr_type is float:
                    setattr(game_settings, key, float(value))
                else:
                    setattr(game_settings, key, value)
                    
        # Update analytics settings
        analytics_config = request.form.get('analytics_config', {})
        if analytics_config:
            try:
                config = json.loads(analytics_config)
                game_settings.analytics_config.update(config)
            except json.JSONDecodeError:
                logging.error("Failed to parse analytics configuration")
                
        game_settings.save_settings()
        logging.info('Game settings updated via web interface')
        return redirect(url_for('settings_route'))
        
    return render_template('settings.html', 
                         settings=vars(game_settings),
                         analytics_config=game_settings.analytics_config 
                         if hasattr(game_settings, 'analytics_config') else {})

@app.route('/system_settings', methods=['GET', 'POST'])
def system_settings():
    if request.method == 'POST':
        # Update system settings
        for key in [
            'screen_width', 'screen_height', 'bg_color',
            'mqtt_broker', 'mqtt_port', 'mqtt_topic',
            'web_server_port', 'classic_mode_theme_selection'
        ]:
            value = request.form.get(key)
            if value is not None and hasattr(game_settings, key):
                if key == 'bg_color':
                    try:
                        value = tuple(map(int, value.strip('()').split(',')))
                    except:
                        value = (0, 0, 0)  # Default color
                elif key == 'classic_mode_theme_selection':
                    value = value == 'on'
                else:
                    attr_type = type(getattr(game_settings, key))
                    if attr_type is int:
                        value = int(value)
                    elif attr_type is float:
                        value = float(value)
                setattr(game_settings, key, value)
                
        # Update analytics system settings
        if hasattr(game_settings, 'analytics_config'):
            for key in [
                'min_games_basic',
                'min_games_advanced',
                'momentum_window',
                'quick_response_window',
                'scoring_run_threshold',
                'cache_size',
                'critical_moment_threshold',
                'close_game_threshold'
            ]:
                value = request.form.get(f'analytics_{key}')
                if value is not None:
                    try:
                        value = int(value) if key != 'critical_moment_threshold' else float(value)
                        game_settings.analytics_config[key] = value
                    except ValueError:
                        logging.error(f"Invalid value for analytics setting {key}: {value}")
                        
        game_settings.save_settings()
        logging.info('System settings updated via web interface')
        return redirect(url_for('system_settings'))
        
    return render_template(
        'system_settings.html',
        settings=vars(game_settings),
        analytics_config=game_settings.analytics_config if hasattr(game_settings, 'analytics_config') else {}
    )

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
            theme_config = {
                'name': theme_name,
                'assets': {},
                'analytics': {
                    'overlay_position': request.form.get('overlay_position', 'top-left'),
                    'show_win_probability': request.form.get('show_win_probability', 'on') == 'on',
                    'show_momentum': request.form.get('show_momentum', 'on') == 'on',
                    'show_patterns': request.form.get('show_patterns', 'on') == 'on'
                }
            }
            
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
            
    return render_template(
        'theme_manager.html',
        themes=available_themes,
        current_theme=game_settings.current_theme,
        available_images=available_images,
        available_sounds=available_sounds,
        available_fonts=available_fonts,
        analytics_config=game_settings.analytics_config if hasattr(game_settings, 'analytics_config') else {}
    )

@app.route('/analytics/download/<int:game_id>')
def download_analytics(game_id):
    """Download analytics data for a game as JSON"""
    if not game_instance or not game_instance.db:
        return jsonify({'error': 'Database not initialized'})
        
    try:
        # Get all analytics data
        analytics_history = game_instance.db.get_analytics_history(game_id)
        scoring_patterns = game_instance.db.get_scoring_patterns(game_id)
        game_stats = game_instance.db.get_game_stats(game_id)
        
        data = {
            'game_id': game_id,
            'analytics_history': analytics_history,
            'scoring_patterns': scoring_patterns,
            'game_stats': game_stats,
            'export_date': datetime.now().isoformat()
        }
        
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error exporting analytics data: {e}")
        return jsonify({'error': 'Failed to export analytics data'})

def run_web_server(settings, game):
    """Run the web server"""
    global game_settings
    global game_instance
    game_settings = settings
    game_instance = game
    app.run(host='0.0.0.0', port=settings.web_server_port)
