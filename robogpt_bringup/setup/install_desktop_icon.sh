#!/bin/bash
echo "Installing owlRoboGPT..."
echo "####################################################"

# Determine the directory where the script resides
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "Preparing RoboGPT environment..."
# Add commands here if needed to set up RoboGPT

# Paths to the run script and icon file
path_to_robogpt_run_script="$SCRIPT_DIR/setup/start_robogpt.sh"
path_to_robogpt_icon_file="$SCRIPT_DIR/setup/robot_inverted.png"

# Directories for desktop and applications menu
outputdir1="$HOME/Desktop/"
outputdir2="$HOME/.local/share/applications/"

# Check if the desktop shortcut already exists
if [ -f "$outputdir1/owlRoboGPT.desktop" ]; then
    echo "Desktop shortcut for owlRoboGPT already exists. Please delete it before running this script again."
    exit 0
fi

# Ensure the run script is executable
chmod +x "$path_to_robogpt_run_script"

echo "Creating desktop entry..."

# Create the desktop shortcut file
cat << EOF > "$outputdir1/owlRoboGPT.desktop"
[Desktop Entry]
Name=owlRoboGPT
Comment=A shell script to run RoboGPT
Exec=$path_to_robogpt_run_script
Icon=$path_to_robogpt_icon_file
Terminal=true
Type=Application
Categories=Application;
EOF

# Set the appropriate permissions for the desktop file
chmod a+rx "$outputdir1/owlRoboGPT.desktop"

# Optionally copy the desktop file to the applications menu directory
cp "$outputdir1/owlRoboGPT.desktop" "$outputdir2"

# Clear the environment variables
unset outputdir1 outputdir2 path_to_robogpt_run_script path_to_robogpt_icon_file

echo "Installation of owlRoboGPT completed."
