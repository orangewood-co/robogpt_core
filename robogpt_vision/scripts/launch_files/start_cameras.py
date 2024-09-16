#!/usr/bin/env python3

import os
import time
import subprocess
import rospy

def launch_with_delay(launch_file, args, delay):
    command = ['roslaunch'] + launch_file.split() + args
    process = subprocess.Popen(command)
    time.sleep(delay)
    return process

def close_with_delay(processes, delay):
    
    for process in processes:
        process.terminate()
        time.sleep(delay)

if __name__ == '__main__':
    try:
        cams = rospy.get_param("number_of_cams",default=1)

        for i in range(cams):
            cam_name = rospy.get_param("camera_"+str(i), default="camera")
            serial_number = rospy.get_param("serial_no_"+str(i), default="")

            # Define the arguments for each launch file
            args_cams = [f'camera:={camera_list[0]}', f'serial_no:={serial_number}']

            # Launch first file
            process_camera_startup = launch_with_delay('realsense2_camera realsense2_camera', args_sim, 5)

            # Wait for all processes to complete
            process_camera_startup.wait()


    except KeyboardInterrupt:
        # Terminate all processes if the script is interrupted
        processes = [process_camera_startup]
        #processes = [process_moveit, process_perception]
        close_with_delay(processes, 5)

        print("Processes terminated")

    finally:
        # Ensure all processes are terminated on script exit
        processes = [process_camera_startup]
        #processes = [process_moveit, process_perception]
        close_with_delay(processes, 5)


