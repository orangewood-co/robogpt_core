#!/usr/bin/env python3

import cv2
import yaml
import rospy
import sys, os
import rospkg
import numpy as np
import tkinter as tk
import pyrealsense2 as rs
from tkinter import simpledialog

rospy.init_node("stereo_camera_setup", anonymous=True)

def get_profiles():
    ctx = rs.context()
    devices = ctx.query_devices()
    devices_info = []

    for device in devices:
        color_profiles = []
        depth_profiles = []
        name = device.get_info(rs.camera_info.name)
        serial = device.get_info(rs.camera_info.serial_number)
        # sc = device.get_info(rs.camera_info.depth_scale)
        for sensor in device.query_sensors():
            for stream_profile in sensor.get_stream_profiles():
                stream_type = str(stream_profile.stream_type())
                if stream_type in ['stream.color', 'stream.depth']:
                    v_profile = stream_profile.as_video_stream_profile()
                    fmt = stream_profile.format()
                    w, h = v_profile.width(), v_profile.height()
                    fps = v_profile.fps()

                    video_type = stream_type.split('.')[-1]
                    # print('  {}: width={}, height={}, fps={}, fmt={}'.format(
                    #     video_type, w, h, fps, fmt))
                    if video_type == 'color':
                        color_profiles.append((w, h, fps, (fmt.value - 1)))
                    else:
                        depth_profiles.append((w, h, fps, fmt.value))


        devices_info.append({
            'name': name,
            'serial': serial,
            'color_format': [1280, 720, 15, 6],
            'depth_format': [1280, 720, 6, 1],
        })
        print(devices_info[-1])

    return devices_info


# Function to read and modify a YAML file
def modify_yaml_file(filename, camera_name, serial,i):

    rospack = rospkg.RosPack()
    package_path = rospack.get_path('robogpt_vision')   
    sys.path.append(package_path)

    # Construct the full path to the YAML file
    yaml_file_path = os.path.join(package_path,"config/camera_params.yaml")

    rospy.loginfo("Camera Info Saved.")
    
    # Read the existing YAML file
    if not os.path.exists(yaml_file_path):
        rospy.logerr("File not found: %s", yaml_file_path)
        return

    with open(yaml_file_path, 'r') as file:
        data = yaml.safe_load(file)

    # Modify the specific key
    data["camera_"+str(i)] = camera_name
    data["serial_no_"+str(i)] = serial
    data["number_of_cams"] = i

    # Write the modified data back to the same file (or a new file)
    with open(yaml_file_path, 'w') as file:
        yaml.dump(data, file)


def get_user_input(title, prompt):
    root = tk.Tk()
    root.withdraw()
    return simpledialog.askstring(title, prompt)

if __name__ == "__main__":
    all_rs_device_info = get_profiles()
    config_out = {}
    for j, device_info in enumerate(all_rs_device_info):
        i = 1
        name = device_info['name']
        serial = device_info['serial']
        (cw, ch, cfps, cfmt) = device_info['color_format']
        (dw, dh, dfps, dfmt) = device_info['depth_format']

        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_device(serial)
        config.enable_stream(rs.stream.color, cw, ch, rs.format(cfmt), cfps)
        config.enable_stream(rs.stream.depth, dw, dh, rs.format(dfmt), dfps)

        align = rs.align(rs.stream.color)
        profile = pipeline.start(config)

        while True:
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)
            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()
            color_image = np.asanyarray(color_frame.get_data())
            depth_image = np.asanyarray(depth_frame.get_data())

            cv2.imshow('1', color_image) 
            key = cv2.waitKey(1)  & 0xFF
            if key == ord("y"):
                camera_name = get_user_input("Camera name", f"Enter a name for camera {name}-{serial}:")
                modify_yaml_file('camera_params.yaml',camera_name,serial,i)
                break
            elif key == ord("n"):
                cv2.destroyAllWindows()
                break



