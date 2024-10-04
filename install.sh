#!/bin/bash

# Install script for Boiling Point Bubble Hockey

# Exit immediately if a command exits with a non-zero status
set -e

# Function to prompt for input with a default value
prompt() {
    local prompt_message="$1"
    local default_value="$2"
    local var_name="$3"

    # Use /dev/tty to read input from the terminal
    printf "%s [%s]: " "$prompt_message" "$default_value" > /dev/tty
    read input < /dev/tty
    if [[ -z "$input" ]]; then
        input="$default_value"
    fi
    # Use indirect parameter expansion to set the variable
    printf -v "$var_name" '%s' "$input"
}

# Function to get the default Git URL from the current repository
get_default_git_url() {
    if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
        git_url=$(git config --get remote.origin.url)
        if [[ -n "$git_url" ]]; then
            echo "$git_url"
            return
        fi
    fi
    echo "https://github.com/yourusername/bubble_hockey.git"
}

# Function to configure Samba
configure_samba() {
    local PROJECT_DIR="$1"
    local RUN_USER="$2"
    local SERVICE_NAME="$3"

    echo ""
    echo "Configuring Samba for file sharing..."

    # Backup original smb.conf if not already backed up
    if [ ! -f /etc/samba/smb.conf.bak ]; then
        sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
        echo "Backup of original smb.conf created at /etc/samba/smb.conf.bak"
    else
        echo "Backup of smb.conf already exists."
    fi

    # Define Samba share
    sudo tee -a /etc/samba/smb.conf > /dev/null <<EOF

[BubbleHockey]
   path = $PROJECT_DIR/assets
   browseable = yes
   read only = no
   guest ok = no
   valid users = $RUN_USER
   create mask = 0755
   directory mask = 0755
EOF

    # Restart Samba service to apply changes
    sudo systemctl restart smbd

    # Add Samba user (prompt for password)
    echo "Adding Samba user '$RUN_USER'. You will be prompted to set a Samba password."
    sudo smbpasswd -a "$RUN_USER"

    # Ensure the user is enabled in Samba
    sudo smbpasswd -e "$RUN_USER"

    echo ""
    echo "Samba has been configured successfully."
    echo "You can access the shared 'assets' directory from other devices using the following credentials:"
    echo "Username: $RUN_USER"
    echo "Password: (the password you just set)"
    echo ""
    echo "For example, from a Windows machine, navigate to \\\\$(hostname)\\BubbleHockey"
    echo "From a macOS or Linux machine, connect using: smb://$(hostname)/BubbleHockey"
    echo ""
}

# Prompt for variables
echo "Welcome to the Boiling Point Bubble Hockey Installer!"
echo "Please provide the following information or press Enter to accept the defaults."

# Determine the default Git URL
DEFAULT_GIT_URL=$(get_default_git_url)

prompt "Enter the project directory" "/home/pi/bubble_hockey" "PROJECT_DIR"
prompt "Enter the service name" "bubble_hockey" "SERVICE_NAME"
prompt "Enter the user to run the service as" "$USER" "RUN_USER"
prompt "Enter the Git repository URL" "$DEFAULT_GIT_URL" "GIT_URL"
prompt "Enter the Python version to use (e.g., python3)" "python3" "PYTHON_VERSION"

echo ""
echo "Installing with the following settings:"
echo "Project Directory: $PROJECT_DIR"
echo "Service Name: $SERVICE_NAME"
echo "Run User: $RUN_USER"
echo "Git Repository URL: $GIT_URL"
echo "Python Version: $PYTHON_VERSION"
echo ""
read -p "Do you want to configure Samba for file sharing? (y/N): " CONFIGURE_SAMBA
CONFIGURE_SAMBA=${CONFIGURE_SAMBA:-N}

# Update system packages
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
sudo apt-get install -y git python3-pip python3-venv samba

# Clone the repository
echo "Cloning the repository..."
if [ ! -d "$PROJECT_DIR" ]; then
    git clone "$GIT_URL" "$PROJECT_DIR"
else
    echo "Project directory already exists. Pulling latest changes..."
    cd "$PROJECT_DIR"
    git pull
fi

cd "$PROJECT_DIR"

# Check if requirements.txt exists before setting up the Python virtual environment
if [ ! -f "requirements.txt" ]; then
    echo "Error: requirements.txt not found in the project directory."
    exit 1
fi

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
$PYTHON_VERSION -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Deactivate virtual environment
deactivate

# Create necessary directories if they don't exist
echo "Creating necessary directories..."
mkdir -p assets/fonts
mkdir -p assets/sounds
mkdir -p assets/themes
mkdir -p assets/common/images
mkdir -p assets/common/sounds
mkdir -p assets/game_modes/classic/images
mkdir -p assets/game_modes/classic/sounds
mkdir -p assets/game_modes/evolved/images
mkdir -p assets/game_modes/evolved/sounds
mkdir -p assets/game_modes/crazy_play/images
mkdir -p assets/game_modes/crazy_play/sounds

# Set permissions for asset directories
echo "Setting permissions for asset directories..."
chmod -R 755 assets/

# Set ownership for asset directories
echo "Setting ownership for asset directories..."
sudo chown -R "$RUN_USER":"$RUN_USER" assets/

# Create default settings.json if it doesn't exist
if [ ! -f "settings.json" ]; then
    echo "Creating default settings.json..."
    cat << EOF > settings.json
{
    "screen_width": 1480,
    "screen_height": 320,
    "bg_color": [0, 0, 0],
    "mqtt_broker": "localhost",
    "mqtt_port": 1883,
    "mqtt_topic": "bubble_hockey/game_status",
    "web_server_port": 5000,
    "period_length": 180,
    "overtime_length": 180,
    "intermission_length": 60,
    "power_up_frequency": 30,
    "taunt_frequency": 60,
    "taunts_enabled": true,
    "random_sounds_enabled": true,
    "random_sound_frequency": 60,
    "combo_goals_enabled": true,
    "combo_time_window": 30,
    "combo_reward_type": "extra_point",
    "combo_max_stack": 5,
    "current_theme": "default",
    "classic_mode_theme_selection": false,
    "gpio_pins": {
        "goal_sensor_red": 17,
        "goal_sensor_blue": 27,
        "puck_sensor_red": 22,
        "puck_sensor_blue": 23
    }
}
EOF
    chmod 644 settings.json
fi

# Optionally configure Samba
if [[ "$CONFIGURE_SAMBA" =~ ^[Yy]$ ]]; then
    configure_samba "$PROJECT_DIR" "$RUN_USER" "$SERVICE_NAME"
else
    echo ""
    echo "Samba configuration skipped."
    echo "To set up Samba manually in the future, follow these steps:"
    echo "1. Install Samba: sudo apt-get install samba"
    echo "2. Edit the Samba configuration file: sudo nano /etc/samba/smb.conf"
    echo "3. Add a new share definition, for example:"
    echo ""
    echo "[BubbleHockey]"
    echo "   path = $PROJECT_DIR/assets"
    echo "   browseable = yes"
    echo "   read only = no"
    echo "   guest ok = no"
    echo "   valid users = $RUN_USER"
    echo "   create mask = 0755"
    echo "   directory mask = 0755"
    echo ""
    echo "4. Restart Samba service: sudo systemctl restart smbd"
    echo "5. Add Samba user: sudo smbpasswd -a $RUN_USER"
    echo ""
    echo "For more detailed instructions, refer to Samba documentation."
    echo ""
fi

# Set up the update script
echo "Setting up the update script..."
cat << EOF > check_updates.sh
#!/bin/bash

# check_updates.sh
# This script checks if updates are available in the Git repository.

cd "$PROJECT_DIR" || exit

# Fetch updates from the remote repository
git fetch

# Check if the local branch is behind the remote branch
if git status -uno | grep -q 'Your branch is behind'; then
    touch update_available.flag
else
    rm -f update_available.flag
fi
EOF

# Make the update script executable
chmod +x check_updates.sh

# Set up cron job for the update script
echo "Setting up cron job for the update script..."
(crontab -l 2>/dev/null | grep -v "$PROJECT_DIR/check_updates.sh"; echo "*/15 * * * * $PROJECT_DIR/check_updates.sh") | crontab -

# Set up systemd service
echo "Setting up systemd service..."

sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Boiling Point Bubble Hockey Service
After=network.target

[Service]
User=$RUN_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/$PYTHON_VERSION $PROJECT_DIR/main.py
Restart=always
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$RUN_USER/.Xauthority

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon and enable the service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME.service

# Start the service
echo "Starting the service..."
sudo systemctl start $SERVICE_NAME.service

# Provide Samba access information if configured
if [[ "$CONFIGURE_SAMBA" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Samba has been configured and is now running."
    echo "Access the shared 'assets' directory using the following credentials:"
    echo "Username: $RUN_USER"
    echo "Password: (the password you set earlier)"
    echo ""
    echo "Access from Windows: \\\\$(hostname)\\BubbleHockey"
    echo "Access from macOS/Linux: smb://$(hostname)/BubbleHockey"
    echo ""
fi

echo ""
echo "Installation complete! The Boiling Point Bubble Hockey service is now running."
echo "You can check the status of the service using:"
echo "sudo systemctl status $SERVICE_NAME.service"
