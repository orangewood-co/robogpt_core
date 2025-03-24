#!/usr/bin/env python3

import rospy

from robogpt_perception import object_detection_implementation
import set_realsense_sources
import set_rgb_cam_sources
import web_feed
from vision_startup import VisionLauncher
from get_world_context import ximg2xbase_implementation

rospy.init_node("node_runner")

def perception_run():
    try:
        # Run the object detection process
        object_detection = object_detection_implementation()
        object_detection._run()

    except Exception as ex:
        rospy.loginfo(ex)

def realsense_setup():
    try:
        rospy.loginfo("Running Realsense setup")
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
        service_instance = ximg2xbase_implementation()
        rospy.spin()

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