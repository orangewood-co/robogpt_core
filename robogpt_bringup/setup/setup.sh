#!/bin/bash


# Step 1: Clone Additional Repositories
echo "Creating src directory and cloning additional repositories..."
mkdir -p ~/workspaces/robogpt/robogpt_ws/src
# git clone https://bitbucket.org/owl-dev/robogpt-description ~/workspaces/robogpt/robogpt_ws/src/robogpt-description
# git clone https://bitbucket.org/owl-dev/robogpt-moveit.git ~/workspaces/robogpt/robogpt_ws/src/robogpt-moveit
# git clone https://bitbucket.org/owl-dev/auto-train.git ~/workspaces/robogpt/robogpt-core/core/skills/vision_skills/object_detection/auto_train



# Step 2: Install requirements
echo "Installing requirements..."

# Install Realsense SDK
sh ~/workspaces/robogpt/robogpt-core/setup/install_librealsense.sh

# Install MQTT manager
sh ~/workspaces/robogpt/robogpt-core/setup/mqtt_manager/install_mosquitto_broker.sh

# Backend setup (Including pusher and spacy)
echo "Use this key when it asks for pusher key in next step : ovKvhW_12Ys3d_i_OXdj_OWlXNXaByEA47F7A4L4nag"
sh ~/workspaces/robogpt/robogpt-core/setup/backend_setup.sh

# Install dependencies
pip3 install -r ~/workspaces/robogpt/robogpt-core/setup/requirements.txt

# Step 3: Set Up the Workspace
echo "Setting up the ROS workspace..."
source ~/workspaces/robogpt/robogpt_ws/devel/setup.bash

echo "Setup complete! Please follow any remaining instructions in the README file."
