#!/usr/bin/env python3

import os, sys
import time
import importlib
import rospy, rospkg
import subprocess 
import multiprocessing
import pyrealsense2 as rs


rospack = rospkg.RosPack()
package_path = rospack.get_path('robogpt_vision')   
sys.path.append(package_path)
try:
    file_path = f'scripts.robogpt_perception'
    object_detection = importlib.import_module(file_path)
    object_detection = getattr(object_detection, 'object_detection_implementation')
except Exception as err:
    print("Could not load robot due to ",err)


def launch_with_delay(launch_file, args, delay):
    command = ['roslaunch'] + launch_file.split() + args
    process = subprocess.Popen(command)
    time.sleep(delay)
    return process
                                                 
def close_with_delay(processes, delay):
    
    for process in processes:
        process.terminate()
        time.sleep(delay)

def init_obj_detection(cam_name):
    obj_detection = object_detection(cam_name)
    obj_detection._run()
    
def check_realsense_cameras():
    # Create a context object for RealSense devices
    context = rs.context()
    
    # Get a list of all connected devices
    devices = context.query_devices()
    
    # Check if any devices are connected
    if len(devices) > 0:
        print(f"Number of RealSense cameras connected: {len(devices)}")
        for i, device in enumerate(devices):
            print(f"Camera {i + 1}:")
            print(f"  Name: {device.get_info(rs.camera_info.name)}")
            print(f"  Serial Number: {device.get_info(rs.camera_info.serial_number)}")
            print(f"  Firmware Version: {device.get_info(rs.camera_info.firmware_version)}")
        return
    else:
        print("No RealSense cameras are connected.")


if __name__ == '__main__':
    try:
        rospy.init_node("start_vision",anonymous=True)
        cams = rospy.get_param("number_of_cams",default=1)
        print(cams)
        for i in range(cams):
            i = i + 1 
            cam_name = rospy.get_param("camera_"+str(i), default="camera")
            serial_number = rospy.get_param("serial_no_"+str(i), default="")

            # Define the arguments for each launch file
            args_cams = [f'camera:={cam_name}', f'serial_no:={serial_number}']
            args_cam_name =[f'camera_name:={cam_name}']
            # Launch first file
            process_camera_startup = launch_with_delay('realsense2_camera rs_camera.launch ', args_cams, 5)
            process_init_detection = launch_with_delay('robogpt_vision detection_bringup.launch',args_cam_name,5)

            # Wait for all processes to complete
            process_camera_startup.wait()
            process_init_detection.wait()


    except KeyboardInterrupt:
        # Terminate all processes if the script is interrupted
        processes = [process_camera_startup, process_init_detection]
        #processes = [process_moveit, process_perception]
        close_with_delay(processes, 5)

        print("Processes terminated")

    finally:
        # Ensure all processes are terminated on script exit
        processes = [process_camera_startup,process_init_detection]
        #processes = [process_moveit, process_perception]
        close_with_delay(processes, 5)


