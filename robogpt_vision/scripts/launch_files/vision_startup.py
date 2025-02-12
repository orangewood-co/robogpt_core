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
    print("Could not load perception files due to ",err)


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
    camera_connected = False
    
    # Check if any devices are connected
    if len(devices) > 0:
        camera_connected = True
        print(f"Number of RealSense cameras connected: {len(devices)}")
    else:
        camera_connected = False
        rospy.logerr("No RealSense cameras are connected.")

    return camera_connected


if __name__ == '__main__':
    try:
        rospy.init_node("start_vision",anonymous=True)
        cams = rospy.get_param("number_of_cams",default=1)
        print(cams)
        for i in range(cams):
            i = i + 1 
            cam_name = rospy.get_param("camera_"+str(i), default="camera")
            serial_number = rospy.get_param("serial_no_"+str(i), default="")
            vision_sim = rospy.get_param("vision_sim", default="on")
            camera_type = rospy.get_param("comp_name",default="intel")
            
            # Define the arguments for each launch file
            args_cams = [f'camera:={cam_name}', f'serial_no:={serial_number}','align_depth:=true']
            args_cam_name =[f'camera_name:={cam_name}']

            if vision_sim == "on":
                    rospy.loginfo("Starting Detection Module in Simulation")
                    process_init_detection = launch_with_delay('robogpt_vision detection_bringup.launch',['camera_name:=camera'],5)
                    process_init_detection.wait()

            if vision_sim == "off":
                # Launch first file
                if check_realsense_cameras():

                    process_camera_startup = launch_with_delay('realsense2_camera rs_camera.launch ', args_cams, 5)
                    
                    process_init_detection = launch_with_delay('robogpt_vision detection_bringup.launch',args_cam_name,5)

                    # Wait for all processes to complete
                    process_camera_startup.wait()
                    process_init_detection.wait()

                if not check_realsense_cameras():
                    rospy.logerr("No Cameras Detected. Please check the connected cameras if connected or switch to Simulation option")
                    rospy.logerr("No Hardware connected and Simulation option is off")
                    rospy.logerr("Exiting Vision Stack")
            
                
    except KeyboardInterrupt:
        # Terminate all processes if the script is interrupted
        processes = [process_camera_startup, process_init_detection]
        close_with_delay(processes, 5)

        print("Processes terminated")

    finally:
        # Ensure all processes are terminated on script exit
        if check_realsense_cameras():
            processes = [process_camera_startup,process_init_detection]
            close_with_delay(processes, 5)
        
        if vision_sim == "on":
            processes = [process_init_detection]
            close_with_delay(processes, 5)



