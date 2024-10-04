#!/bin/bash

# Install script for Boiling Point Bubble Hockey

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

# Prompt for variables
echo "Welcome to the Boiling Point Bubble Hockey Installer!"
echo "Please provide the following information or press Enter to accept the defaults."

prompt "Enter the project directory" "/home/pi/bubble_hockey" "PROJECT_DIR"
prompt "Enter the service name" "bubble_hockey" "SERVICE_NAME"
prompt "Enter the user to run the service as" "$USER" "RUN_USER"
prompt "Enter the Git repository URL" "https://github.com/yourusername/bubble_hockey.git" "GIT_URL"
prompt "Enter the Python version to use (e.g., python3)" "python3" "PYTHON_VERSION"

echo ""
echo "Installing with the following settings:"
echo "Project Directory: $PROJECT_DIR"
echo "Service Name: $SERVICE_NAME"
echo "Run User: $RUN_USER"
echo "Git Repository URL: $GIT_URL"
echo "Python Version: $PYTHON_VERSION"
echo ""

# Update system packages
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
sudo apt-get install -y git python3-pip python3-venv

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
pip install -r requirements.txt

# Deactivate virtual environment
deactivate

# Set permissions for asset directories
echo "Setting permissions for asset directories..."
chmod -R 755 assets/

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
(crontab -l 2>/dev/null; echo "*/15 * * * * $PROJECT_DIR/check_updates.sh") | crontab -

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

echo ""
echo "Installation complete! The Boiling Point Bubble Hockey service is now running."
echo "You can check the status of the service using:"
echo "sudo systemctl status $SERVICE_NAME.service"
