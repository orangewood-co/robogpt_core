#!/usr/bin/env python3
"""
ROS node runner for vision-related services.
Launches different vision components based on provided parameters.
"""

import sys
from typing import NoReturn

import rospy

# Local imports
from robogpt_perception import object_detection_implementation
from get_world_context import ximg2xbase_implementation
from vision_startup import VisionLauncher
import set_realsense_sources
import set_rgb_cam_sources

def perception_run() -> None:
    """Run the object detection process."""
    try:
        rospy.loginfo("Starting object detection process")
        object_detection = object_detection_implementation()
        object_detection._run()
    except Exception as ex:
        rospy.logerr(f"Error in object detection: {ex}")

def realsense_setup() -> None:
    """Configure RealSense camera sources."""
    try:
        rospy.loginfo("Running RealSense setup")
        set_realsense_sources.main()
        rospy.loginfo("RealSense setup completed successfully")
    except Exception as ex:
        rospy.logerr(f"Error in RealSense setup: {ex}")

def rgb_setup() -> None:
    """Configure RGB camera sources."""
    try:
        rospy.loginfo("Running RGB camera setup")
        set_rgb_cam_sources.main()
        rospy.loginfo("RGB camera setup completed successfully")
    except Exception as ex:
        rospy.logerr(f"Error in RGB camera setup: {ex}")

def pose_calculator_service() -> NoReturn:
    """Start the pose calculator service and keep it running."""
    try:
        rospy.loginfo("Starting pose calculator service")
        service_instance = ximg2xbase_implementation()
        # Keep the service running
        rospy.spin()
    except rospy.ROSInterruptException:
        rospy.loginfo("ROS Interrupt Exception caught. Shutting down pose calculator service.")
    except Exception as ex:
        rospy.logerr(f"Error in pose calculator service: {ex}")

def vision_startup() -> None:
    """Initialize and run the vision system."""
    try:
        rospy.loginfo("Starting vision system")
        launcher = VisionLauncher()
        launcher.run()
        rospy.loginfo("Vision system started successfully")
    except Exception as ex:
        rospy.logerr(f"Error in vision startup: {ex}")

def main() -> int:
    """Main entry point for the node runner."""
    try:
        rospy.init_node("node_runner")
        
        node = rospy.get_param("~node_name")
        rospy.loginfo(f"Starting node: {node}")
        
        if node == "pose_service":
            pose_calculator_service()
        elif node == "vision_startup":
            vision_startup()
        elif node == "rgb_setup":
            rgb_setup()
        elif node == "realsense_setup":
            realsense_setup()
        elif node == "perception":
            perception_run()
        else:
            rospy.logerr(f"Unknown node type: {node}")
            return 1
            
        return 0
    except Exception as ex:
        rospy.logerr(f"Unexpected error in node runner: {ex}")
        return 1

if __name__ == "__main__":
    sys.exit(main())