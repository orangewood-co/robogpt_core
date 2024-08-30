import cv2
import json

import tkinter as tk
from tkinter import simpledialog

import sys, os
import numpy as np
import pyrealsense2 as rs
import time


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


def save_to_json_file(data, filename):
    with open(filename, 'r') as file:
        file_data = json.load(file)

    
    file_data["camera_config"] = {}
    file_data["camera_config"].update(data)
    

    with open(filename, 'w') as file:
        json.dump(file_data, file, indent=4)

def get_user_input(title, prompt):
    root = tk.Tk()
    root.withdraw()
    return simpledialog.askstring(title, prompt)

if __name__ == "__main__":
    all_rs_device_info = get_profiles()
    config_out = {}
    for ii, device_info in enumerate(all_rs_device_info):
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
                config_out[camera_name] = {"camera_index": serial, "model": name}
                config_out[camera_name].update(device_info)
                break
            elif key == ord("n"):
                cv2.destroyAllWindows()
                break
    root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

    print(root_path, "root_path")
    # two levels down from owl_robotgpt
    
    json_filename = "robogpt_v3/robogpt_config/robot_config/robogpt.json"
    print(json_filename)
    print(config_out)

    save_to_json_file(config_out, json_filename)

