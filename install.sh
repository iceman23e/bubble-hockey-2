#!/bin/bash

# install.sh

# Set variables
REPO_URL="https://github.com/iceman23e/bubble-hockey-2.git"
PROJECT_DIR="/home/pi/bubble_hockey"
SERVICE_NAME="bubble_hockey.service"
USER="pi"
PYTHON_VERSION="python3"

# Function to display messages
function echo_info() {
    echo -e "\e[32m[INFO]\e[0m $1"
}

function echo_error() {
    echo -e "\e[31m[ERROR]\e[0m $1"
}

# Update and upgrade the system
echo_info "Updating and upgrading the system..."
sudo apt-get update -y && sudo apt-get upgrade -y

# Install system dependencies
echo_info "Installing system dependencies..."
sudo apt-get install -y git $PYTHON_VERSION $PYTHON_VERSION-pip $PYTHON_VERSION-venv $PYTHON_VERSION-dev \
                        libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
                        libportmidi-dev libfreetype6-dev libavformat-dev libswscale-dev \
                        libjpeg-dev libtiff5-dev libx11-dev libxext-dev samba samba-common-bin

# Clone the GitHub repository
if [ -d "$PROJECT_DIR" ]; then
    echo_info "Project directory already exists. Pulling latest changes..."
    cd "$PROJECT_DIR"
    git pull
else
    echo_info "Cloning the repository from GitHub..."
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# Create project directory structure (if not already present)
echo_info "Creating project directory structure..."
mkdir -p assets/{fonts,images,sounds,themes}
mkdir -p assets/images/{volcano_eruption_frames,lava_flow_frames}
mkdir -p assets/themes/default/{images,sounds,fonts}
mkdir -p database logs templates

# Set up Python virtual environment
echo_info "Setting up Python virtual environment..."
$PYTHON_VERSION -m venv venv
source venv/bin/activate

# Upgrade pip
echo_info "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo_info "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo_error "requirements.txt not found!"
    exit 1
fi

# Create empty settings.json if it doesn't exist
if [ ! -f settings.json ]; then
    echo_info "Creating default settings.json..."
    echo '{}' > settings.json
fi

# Initialize the database
if [ ! -f database/bubble_hockey.db ]; then
    echo_info "Initializing the database..."
    python -c "from database import Database; db = Database(); db.close()"
fi

# Set up permissions
echo_info "Setting up file permissions..."
chmod +x main.py

# Set up Samba for asset transfer
echo_info "Configuring Samba for asset transfer..."
sudo smbpasswd -a $USER
SAMBA_CONFIG="[BubbleHockey]
path = $PROJECT_DIR/assets
writable = yes
create mask = 0777
directory mask = 0777
public = no"

if ! grep -q "\[BubbleHockey\]" /etc/samba/smb.conf; then
    echo "$SAMBA_CONFIG" | sudo tee -a /etc/samba/smb.conf > /dev/null
    sudo systemctl restart smbd
else
    echo_info "Samba share already configured."
fi

# Set up systemd service
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"

echo_info "Setting up systemd service..."
if [ ! -f "$SERVICE_FILE" ]; then
    echo "[Unit]
Description=Bubble Hockey Game Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target" | sudo tee "$SERVICE_FILE" > /dev/null
fi

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo_info "Installation complete!"

echo "----------------------------------------"
echo "Next steps:"
echo "1. Transfer your assets (images, sounds, fonts) to the appropriate directories under 'assets/'."
echo "   You can access the 'assets' directory via Samba using the following credentials:"
echo "   - Address: \\\\$(hostname -I | awk '{print $1}')\\BubbleHockey"
echo "   - Username: $USER"
echo "   - Password: [the password you set during Samba configuration]"
echo ""
echo "2. Start the game service:"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "The game is set to run on boot."
echo "----------------------------------------"
