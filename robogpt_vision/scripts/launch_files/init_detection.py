#!/usr/bin/env python3

import os, sys
import time
import importlib
import rospy, rospkg
import subprocess 
import multiprocessing


rospack = rospkg.RosPack()
package_path = rospack.get_path('robogpt_vision')  
sys.path.append(package_path)

from scripts.robogpt_perception import object_detection_implementation

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
    object_detection = object_detection_implementation(cam_name = cam_name)
    object_detection._run()
    

if __name__ == '__main__':
    try:
        rospy.init_node("detection_startup",anonymous=True)
        cams = rospy.get_param("number_of_cams",default=1)
        print(cams)
        for i in range(cams):
            i = i + 1 
            cam_name = rospy.get_param("camera_"+str(i), default="camera")
            serial_number = rospy.get_param("serial_no_"+str(i), default="")

            # Define the arguments for each launch file
            args_cams = [f'camera:={cam_name}', f'serial_no:={serial_number}']

            # Launch first file
            process_init_detection = multiprocessing.Process(target=init_obj_detection, args= (cam_name,))

            # Wait for all processes to complete
            process_init_detection.start()


    except KeyboardInterrupt:
        # Terminate all processes if the script is interrupted
        processes = [process_camera_startup]
        #processes = [process_moveit, process_perception]
        close_with_delay(processes, 5)

        print("Processes terminated")

    finally:
        # Ensure all processes are terminated on script exit
        processes = [process_init_detection]
        #processes = [process_moveit, process_perception]
        close_with_delay(processes, 5)


