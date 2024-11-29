#!/bin/bash

echo $PYTHONPATH
echo $ROS_PACKAGE_PATH

# Source ROS and workspace setup files
source /opt/ros/noetic/setup.bash
source ~/orangewood_ws/devel/setup.bash

# Run the Python script using $HOME for the dynamic path
python3 $HOME/orangewood_ws/src/robogpt_v3/robogpt_bringup/scripts/app.py
