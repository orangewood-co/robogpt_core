#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Variables
ROS_INSTALL_SCRIPT_URL="https://raw.githubusercontent.com/orangewood-co/orangewood_sim_stack/main/host_pc_scripts/ros_install_noetic.sh"
WORKSPACE_DIR="$HOME/orangewood_ws"
SRC_DIR="$WORKSPACE_DIR/src"
BASHRC="$HOME/.bashrc"

# Determine the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to display messages
function echo_info {
    echo -e "\e[34m[INFO]\e[0m $1"
}

function echo_success {
    echo -e "\e[32m[SUCCESS]\e[0m $1"
}

function echo_error {
    echo -e "\e[31m[ERROR]\e[0m $1"
}

# Update and upgrade system packages
echo_info "Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# Install necessary dependencies
echo_info "Installing necessary dependencies..."
sudo apt-get install -y wget git curl python3-pip dpkg

# Install ROS Noetic
echo_info "Installing ROS Noetic..."
wget -c $ROS_INSTALL_SCRIPT_URL -O ros_install_noetic.sh
chmod +x ros_install_noetic.sh
./ros_install_noetic.sh
rm ros_install_noetic.sh
echo_success "ROS Noetic installed successfully."

# Setup ROS environment
echo_info "Setting up ROS environment..."
source /opt/ros/noetic/setup.bash
echo "source /opt/ros/noetic/setup.bash" >> $BASHRC

# Create ROS workspace
echo_info "Creating ROS workspace at $WORKSPACE_DIR..."
mkdir -p $SRC_DIR
cd $SRC_DIR

# Clone repositories
echo_info "Cloning RoboGPT repositories..."
declare -a repos=(
    "git@bitbucket.org:owl-dev/robogpt_v3.git"
    "git@bitbucket.org:owl-dev/robot_drivers.git"
    "git@bitbucket.org:owl-dev/robogpt_apps.git"
    "git@bitbucket.org:owl-dev/robogpt_hardware_stack.git"
    "git@bitbucket.org:owl-dev/orangewood_simstack.git"
)

# Clone repositories
echo_info "Cloning RoboGPT repositories..."
declare -a repos=(
    "git@bitbucket.org:owl-dev/robogpt_v3.git"
    "git@bitbucket.org:owl-dev/robot_drivers.git"
    "git@bitbucket.org:owl-dev/robogpt_apps.git"
    "git@bitbucket.org:owl-dev/robogpt_hardware_stack.git"
    "git@bitbucket.org:owl-dev/orangewood_simstack.git"
)

for repo in "${repos[@]}"; do
    # Extract the repository name by removing the .git extension
    repo_name=$(basename "$repo" .git)
    
    # Define the target directory path
    target_dir="$SRC_DIR/$repo_name"
    
    if [ -d "$target_dir" ]; then
        echo_info "Repository '$repo_name' already exists at '$target_dir'. Skipping clone."
    else
        echo_info "Cloning repository '$repo_name'..."
        git clone "$repo" "$target_dir"
        echo_success "Repository '$repo_name' cloned successfully."
    fi
done
echo_success "All repositories processed."


# Install ROS dependencies
echo_info "Initializing rosdep..."
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    sudo rosdep init
fi
rosdep update

echo_info "Installing ROS dependencies using rosdep..."
rosdep install --from-paths $SRC_DIR --ignore-src -r -y

# Build the workspace
echo_info "Building the ROS workspace with catkin_make..."
cd $WORKSPACE_DIR
catkin_make -j1
echo_success "ROS workspace built successfully."

# Source the workspace
echo_info "Sourcing the workspace..."
echo "source $WORKSPACE_DIR/devel/setup.bash" >> $BASHRC
source $BASHRC

# Install Realsense packages
echo_info "Installing Additional ROS packages..."
sudo apt-get install -y ros-noetic-realsense2-camera
sudo apt-get install -y ros-noetic-moveit

# Backend setup (Directly included)
echo_info "Setting up backend dependencies..."

# 1. Install pusher.deb
PUSHER_DEB_PATH="$SCRIPT_DIR/pusher_0.20_linux_386.deb"
if [ -f "$PUSHER_DEB_PATH" ]; then
    echo_info "Installing pusher.deb from $PUSHER_DEB_PATH..."
    sudo dpkg -i "$PUSHER_DEB_PATH"
    # Fix any dependency issues
    sudo apt-get install -f -y
    echo_success "pusher_0.20_linux_386.deb installed successfully."
else
    echo_error "pusher_0.20_linux_386.deb not found in $SCRIPT_DIR. Please ensure the file is present."
    exit 1
fi

# 2. Install Python package 'pusher'
echo_info "Installing Python package 'pusher'..."
pip3 install --user pusher
echo_success "Python package 'pusher' installed successfully."

# 3. Automated Pusher login
echo_info "Logging into Pusher..."

# Define your constant Pusher key
PUSHER_LOGIN_KEY="JD5g-_Uf1u2lu0W9T52kZm812NqEiHe3AIHqLn9ELxI"

# Automate the pusher login by echoing the key and piping it into the command
echo "$PUSHER_LOGIN_KEY" | pusher login || { echo_error "Pusher login failed. Please login manually."; exit 1; }

# Verify Pusher login
echo_success "Logged into Pusher successfully."


# 4. Install additional dependencies
echo_info "Installing additional dependencies..."
sudo apt-get install -y libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0
echo_success "Additional dependencies installed successfully."

# Frontend setup (Optional)
echo_info "Frontend setup is optional and primarily intended for core development."

read -p "Do you want to set up the frontend (RoboGPT-Webapp) on localhost? (y/N): " setup_frontend
setup_frontend=${setup_frontend:-n}

if [[ "$setup_frontend" =~ ^[Yy]$ ]]; then
    echo_info "Setting up frontend..."
    FRONTEND_SETUP_DIR="$SRC_DIR/robogpt_v3/robogpt_bringup/setup/frontend_setup"
    
    # Check if frontend_setup.sh exists
    if [ -f "$FRONTEND_SETUP_DIR/frontend_setup.sh" ] && [ -f "$FRONTEND_SETUP_DIR/pusher_key_update.py" ]; then
        sudo chmod +x "$FRONTEND_SETUP_DIR/frontend_setup.sh" "$FRONTEND_SETUP_DIR/pusher_key_update.py"
        sudo "$FRONTEND_SETUP_DIR/frontend_setup.sh"
        
        # Prompt user for Pusher credentials
        echo_info "Please enter your Pusher credentials."
        read -p "App ID: " PUSHER_APP_ID
        read -p "Key: " PUSHER_KEY
        read -p "Cluster: " PUSHER_CLUSTER
        read -s -p "Secret: " PUSHER_SECRET
        echo
        
        # Automate pusher_key_update.py by passing arguments
        python3 "$FRONTEND_SETUP_DIR/pusher_key_update.py" \
            --app-id "$PUSHER_APP_ID" \
            --key "$PUSHER_KEY" \
            --cluster "$PUSHER_CLUSTER" \
            --secret "$PUSHER_SECRET"
        echo_success "Frontend set up successfully."
    else
        echo_error "Frontend setup scripts not found in $FRONTEND_SETUP_DIR."
    fi
else
    echo_info "Skipping frontend setup."
    echo -e "\e[33m[DISCLAIMER]\e[0m Frontend setup skipped. This is intended for core development purposes only. If you need to run the RoboGPT-Webapp on localhost, please rerun the script or set it up manually later."
fi

# Install pip dependencies
echo_info "Installing Python pip dependencies..."
PIP_REQUIREMENTS="$SRC_DIR/robogpt_v3/robogpt_bringup/setup/requirements.txt"
if [ -f "$PIP_REQUIREMENTS" ]; then
    pip3 install --user -r "$PIP_REQUIREMENTS"
    echo_success "Python dependencies installed successfully."
else
    echo_error "requirements.txt not found at $PIP_REQUIREMENTS."
    exit 1
fi

# Install RoboGPT Application
echo_info "Installing RoboGPT desktop application..."
INSTALL_SCRIPT="$SRC_DIR/robogpt_v3/robogpt_bringup/setup/install_desktop_icon.sh"
if [ -f "$INSTALL_SCRIPT" ]; then
    sudo "$INSTALL_SCRIPT"
    echo_success "RoboGPT desktop application installed successfully."
else
    echo_error "install_desktop_icon.sh not found at $INSTALL_SCRIPT."
    exit 1
fi

echo_success "RoboGPT Stack setup and installation completed successfully!"

# Optional: Source the workspace again
source $BASHRC
