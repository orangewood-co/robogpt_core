#!/usr/bin/env python3

import os
import sys
import time
import importlib
import rospy
import rospkg
import subprocess
import multiprocessing
import pyrealsense2 as rs

# Get the path of the 'robogpt_vision' package and add it to the system path
rospack = rospkg.RosPack()
package_path = rospack.get_path('robogpt_vision')
sys.path.append(package_path)

# Try to import the object detection module
try:
    file_path = 'scripts.robogpt_perception'
    object_detection = importlib.import_module(file_path)
    object_detection = getattr(object_detection, 'ObjectDetectionImplementation')
except Exception as err:
    print("Could not load perception files due to ", err)

class VisionLauncher:
    def __init__(self):
        self.process_camera_startup = None
        self.process_init_detection = None
        self.vision_sim = "off"
        
    def launch_with_delay(self, launch_file, args, delay):
        """
        Launch a ROS launch file with a specified delay.

        Args:
            launch_file (str): The launch file to execute.
            args (list): List of arguments for the launch file.
            delay (int): Delay in seconds before executing the launch file.
        
        Returns:
            process: The subprocess running the launch file.
        """
        command = ['roslaunch'] + launch_file.split() + args
        process = subprocess.Popen(command)
        time.sleep(delay)
        return process

    def close_with_delay(self, processes, delay):
        """
        Terminate a list of processes with a specified delay.

        Args:
            processes (list): List of processes to terminate.
            delay (int): Delay in seconds before terminating each process.
        """
        for process in processes:
            if process:  # Check if process exists before terminating
                process.terminate()
                time.sleep(delay)

    def init_obj_detection(self, cam_name):
        """
        Initialize object detection for a given camera.

        Args:
            cam_name (str): The name of the camera.
        """
        obj_detection = object_detection(cam_name)
        obj_detection._run()

    def check_realsense_cameras(self):
        """
        Check for connected RealSense cameras.

        Returns:
            bool: True if cameras are connected, False otherwise.
        """
        context = rs.context()
        devices = context.query_devices()

        if len(devices) > 0:
            print(f"Number of RealSense cameras connected: {len(devices)}")
            return True
        else:
            rospy.logerr("No RealSense cameras are connected.")
            return False

    def run(self):
        """Main execution method to start vision processes"""
        try:
            # rospy.init_node("start_vision", anonymous=True)
            cams = rospy.get_param("number_of_cams", default=1)
            print(cams)

            for i in range(cams):
                i += 1
                cam_name = rospy.get_param(f"camera_{i}", default="camera")
                serial_number = rospy.get_param(f"serial_no_{i}", default="")
                self.vision_sim = rospy.get_param("vision_sim", default="off")
                camera_type = rospy.get_param("comp_name", default="intel")

                # Define the arguments for each launch file
                args_cams = [f'camera:={cam_name}', f'serial_no:={serial_number}', 'align_depth:=true']
                args_cam_name = [f'camera_name:={cam_name}']

                if self.vision_sim == "on":
                    rospy.loginfo("Starting Detection Module in Simulation")
                    self.process_init_detection = self.launch_with_delay('robogpt_vision detection_bringup.launch', ['camera_name:=camera'], 5)
                    self.process_init_detection.wait()

                if self.vision_sim == "off":
                    if self.check_realsense_cameras():
                        self.process_camera_startup = self.launch_with_delay('realsense2_camera rs_camera.launch', args_cams, 5)
                        self.process_init_detection = self.launch_with_delay('robogpt_vision detection_bringup.launch', args_cam_name, 5)

                        # Wait for all processes to complete
                        self.process_camera_startup.wait()
                        self.process_init_detection.wait()

                    if not self.check_realsense_cameras():
                        rospy.logerr("No Cameras Detected. Please check the connected cameras if connected or switch to Simulation option")
                        rospy.logerr("No Hardware connected and Simulation option is off")
                        rospy.logerr("Exiting Vision Stack")

        except KeyboardInterrupt:
            # Terminate all processes if the script is interrupted
            self.shutdown()
            print("Processes terminated")

        finally:
            # Ensure all processes are terminated on script exit
            self.shutdown()
            
    def shutdown(self):
        """Clean up all processes"""
        if hasattr(self, 'vision_sim') and self.vision_sim == "on":
            if self.process_init_detection:
                self.close_with_delay([self.process_init_detection], 5)
        elif self.check_realsense_cameras():
            processes = [p for p in [self.process_camera_startup, self.process_init_detection] if p]
            self.close_with_delay(processes, 5)

if __name__ == '__main__':
    launcher = VisionLauncher()
    launcher.run()