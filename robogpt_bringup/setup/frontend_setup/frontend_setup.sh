#!/bin/bash

# Define the parent directory
parent_dir=~/orangewood_ws/src

# Define the folder to check
folder_name="robogpt-webapp-latest"

# Define the Git repository URL (replace with the actual repository URL)
repo_url="git@bitbucket.org:owl-dev/robogpt-webapp-latest.git"

# Check if the folder exists in the parent directory
if [ -d "$parent_dir/$folder_name" ]; then
    echo "The folder '$folder_name' already exists in the parent directory."
else
    echo "The folder '$folder_name' does not exist. Cloning from Git..."
    # Clone the repository into the parent directory
    git clone "$repo_url" "$parent_dir/$folder_name"
    
    # Check if the clone was successful
    if [ $? -eq 0 ]; then
        echo "Repository successfully cloned into '$parent_dir/$folder_name'."
    else
        echo "Failed to clone the repository."
        exit 1
    fi
fi

# Navigate to the cloned directory
cd "$parent_dir/$folder_name" || { echo "Failed to navigate to '$parent_dir/$folder_name'."; exit 1; }

# Run the commands
echo "Running system updates and installing required packages..."
sudo apt update
sudo apt install -y curl

# Run the curl command to set up Node.js 18.x
echo "Setting up Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# Install Node.js and npm
sudo apt install -y nodejs

# Install npm packages
echo "Installing npm packages..."
npm i

# Check if npm installation was successful
if [ $? -eq 0 ]; then
    echo "npm packages installed successfully."
else
    echo "npm installation failed."
    exit 1
fi

# Run the Python file in the same directory as the script
echo "Running the script to setup pusher for frontend..."
python3 pusher_key_update.py  

# Check if Python script ran successfully
if [ $? -eq 0 ]; then
    echo "Python script executed successfully."
else
    echo "Failed to run the Python script."
    exit 1
fi

