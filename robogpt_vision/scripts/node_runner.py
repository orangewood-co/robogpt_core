#!/usr/bin/env python3

import rospy

import robogpt_perception
import set_realsense_sources
import set_rgb_cam_sources
import web_feed
from vision_startup import VisionLauncher
from get_world_context import XImgToBaseImplementation

rospy.init_node("node_runner")

def perception_run():
    try:
        # Run the object detection process
        robogpt_perception.run()

    except Exception as ex:
        rospy.loginfo(ex)

def realsense_setup():
    try:
        set_realsense_sources.main()
    except Exception as ex:
        rospy.loginfo(ex)

def rgb_setup():
    try:
        set_rgb_cam_sources.main()
    except Exception as ex:
        rospy.loginfo(ex)

def pose_calculator_service():
    try:
        # Instantiate the service class
        service_instance = XImgToBaseImplementation()
    except rospy.ROSInterruptException:
        rospy.loginfo("ROS Interrupt Exception caught. Shutting down.")

def vision_startup():
    launcher = VisionLauncher()
    launcher.run()

def feed():
    web_feed.main()


if __name__=="__main__":
    node = rospy.get_param("~node_name")
    if node == "pose_service":
        pose_calculator_service()
    if node == "vision_startup":
        vision_startup()
    if node == "rgb_setup":
        rgb_setup()
    if node == "realsense_setup":
        realsense_setup()
    if node == "perception":
        perception_run()
    if node == "web_feed":
        feed()