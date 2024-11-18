#!/bin/bash

echo $PYTHONPATH
echo $ROS_PACKAGE_PATH
source /opt/ros/noetic/setup.bash
source ~/orangewood_ws/devel/setup.bash
python3 /home/aion/orangewood_ws/src/robogpt_v3/robogpt_bringup/scripts/app.py