#!/usr/bin/env python3

import os
import cv2
import json
import time
import sys
import rospkg
import rospy
import imutils
import tkinter as tk
from tkinter import simpledialog
from imutils.video import VideoStream

rospy.init_node("rgb_camera_setup", anonymous=True)

def find_working_webcams(max_cameras=10):
    """Finds and returns a list of working webcams.

    Args:
        max_cameras (int): The maximum number of cameras to check.

    Returns:
        list: A list of tuples containing the type and index of working webcams.
    """
    working_webcams = []
    for camera_index in range(max_cameras):
        vs = VideoStream(src=camera_index).start()
        frame = vs.read()

        if frame is None:
            vs.stop()
        else:
            working_webcams.append(("rgb", camera_index))
            vs.stop()
        time.sleep(1)

    return working_webcams

def save_to_json_file(data, filename):
    """Saves the given data to a JSON file.

    Args:
        data (dict): The data to save.
        filename (str): The path to the JSON file.
    """
    with open(filename, 'r') as file:
        file_data = json.load(file)

    file_data["camera_config"].update(data)

    with open(filename, 'w') as file:
        json.dump(file_data, file, indent=4)

def get_user_input(title, prompt):
    """Prompts the user for input using a dialog box.

    Args:
        title (str): The title of the dialog box.
        prompt (str): The prompt message for the user.

    Returns:
        str: The user's input.
    """
    root = tk.Tk()
    root.withdraw()
    return simpledialog.askstring(title, prompt)

def main():
    working_webcams = find_working_webcams()
    selected_webcams = {}

    for cam_type, camera_index in working_webcams:
        cap = cv2.VideoCapture(camera_index)
        print(f"Displaying video feed from webcam {camera_index}.")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = imutils.resize(frame, width=640)
            cv2.imshow(f"Webcam {camera_index}", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("y"):
                cap.release()
                cv2.destroyAllWindows()
                camera_name = get_user_input("Camera name", f"Enter a name for camera {camera_index}:")
                height = frame.shape[0]
                width = frame.shape[1]
                selected_webcams[camera_name] = {
                    "camera_index": camera_index,
                    "model": f"rgb_cam_{len(selected_webcams)}",
                    "height": height,
                    "width": width
                }
                break
            elif key == ord("n"):
                cap.release()
                cv2.destroyAllWindows()
                break

    rospack = rospkg.RosPack()
    package_path = rospack.get_path('robogpt_vision')    
    sys.path.append(package_path)

    json_filename = os.path.join(package_path, "config/vision_config.json")

    save_to_json_file(selected_webcams, json_filename)
    print(f"Selected webcams list saved to {json_filename}")


if __name__ == "__main__":
    main()