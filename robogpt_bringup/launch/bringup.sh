#!/bin/bash

# Default values for arguments
DEFAULT_TYPE="description"
DEFAULT_ROBOT_NAME="ec63"
DEFAULT_ROBOT_IP="192.168.1.201"
DEFAULT_USE_CASE="base"
DEFAULT_USE_SIM="true"
DEFAULT_SIM_VISION="off"
DEFAULT_DRIVER="none"

# Arguments passed to the script or default values
TYPE=${1:-$DEFAULT_TYPE}
ROBOT_NAME=${2:-$DEFAULT_ROBOT_NAME}
ROBOT_IP=${3:-$DEFAULT_ROBOT_IP}
USE_CASE=${4:-$DEFAULT_USE_CASE}
USE_SIM=${5:-$DEFAULT_USE_SIM}
SIM_VISION=${6:-$DEFAULT_SIM_VISION}
DRIVER=${7:-$DEFAULT_DRIVER}

# Export ROS environment variables
export ROS_MASTER_URI=http://localhost:11311
export ROS_HOSTNAME=localhost

# Function to launch a ROS launch file in a new terminal with a custom title
launch_in_new_terminal() {
  local title=$1
  shift
  gnome-terminal --title="$title" -- bash -c "$*; exec bash"
}

# Start ROS Master if not already running
if ! pgrep -x "roscore" > /dev/null; then
  launch_in_new_terminal "ROS Master" roscore &
  sleep 5  # Ensure roscore is fully initialized
fi

# Launch the bringup file
launch_in_new_terminal "Welcome Message" rosrun --wait robogpt_bringup bringup_art.py &
sleep 2

if [ "$USE_SIM" == "true" ]; then
  # Launch simulation bringup
  launch_in_new_terminal "Simulation Bringup" roslaunch --wait sim_bringup sim_bringup.launch \
    gripper:=robotiq2f85 world:=empty camera:=on sim:=on time:=5 robot_name:=$ROBOT_NAME &
else
  # Launch hardware bringup
  launch_in_new_terminal "Hardware Bringup" roslaunch --wait hardware_bringup bringup.launch \
    type:=$TYPE driver:=$DRIVER time:=5 controller:=simple rviz:=true js_pub:=false robot_name:=$ROBOT_NAME \
    dual_bot:=false camera_model:=d435 gripper_model:=robotiq cams:=one robot_ip:=$ROBOT_IP &
fi
sleep 2

# Launch agents
launch_in_new_terminal "Agent Bringup" roslaunch --wait robogpt_agents agent_bringup.launch \
  robot_name:=$ROBOT_NAME use_case:=$USE_CASE use_sim:=$USE_SIM setup:=janatics &
sleep 2

# Launch web feed
launch_in_new_terminal "Web Feed" rosrun --wait robogpt_vision web_feed.py &
sleep 2

# Launch vision stack
launch_in_new_terminal "Vision Bringup" roslaunch --wait timed_roslaunch timed_roslaunch.launch \
  time:=5 pkg:=robogpt_vision file:=vision_bringup.launch value:="sim_vision:=$SIM_VISION comp_name:=intel" &

# Wait for all processes to finish
wait
