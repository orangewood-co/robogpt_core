#!/bin/bash
echo "Installing robogpt..."
echo "####################################################"

# Determine the directory where the script resides
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "Preparing robogpt environment..."
# Add commands here if needed to set up robogpt

# Paths to the run script and icon file
path_to_robogpt_run_script="$SCRIPT_DIR/run_app.sh"
path_to_robogpt_icon_file="$SCRIPT_DIR/robot.png"

# Directories for desktop and applications menu
outputdir1="$HOME/Desktop/"
outputdir2="$HOME/.local/share/applications/"

# Ensure the desktop directory exists
mkdir -p "$outputdir1"

# Check if the desktop shortcut already exists
if [ -f "$outputdir1/robogpt.desktop" ]; then
    echo "Desktop shortcut for owlrobogpt already exists. Please delete it before running this script again."
    exit 0
fi

# Ensure the run script is executable
chmod +x "$path_to_robogpt_run_script"

echo "Creating desktop entry..."

# Create the desktop shortcut file
cat << EOF > "$outputdir1/robogpt.desktop"
[Desktop Entry]
Name=RoboGPT
Comment=A shell script to run robogpt
Exec=$path_to_robogpt_run_script
Icon=$path_to_robogpt_icon_file
Terminal=true
Type=Application
Categories=Application;
EOF

# Set the appropriate permissions for the desktop file
gio set "$HOME/Desktop/robogpt.desktop" metadata::trusted true
chmod +x "$HOME/Desktop/robogpt.desktop"
chmod a+rx "$outputdir1/robogpt.desktop"

# Optionally copy the desktop file to the applications menu directory
mkdir -p "$outputdir2"
cp "$outputdir1/robogpt.desktop" "$outputdir2"

# Clear the environment variables
unset outputdir1 outputdir2 path_to_robogpt_run_script path_to_robogpt_icon_file

echo "Installation of robogpt completed."
