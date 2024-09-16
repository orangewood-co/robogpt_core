import rospy
import json
import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import simpledialog
from sensor_msgs.msg import CameraInfo, Image
from cv_bridge import CvBridge, CvBridgeError

# Path to the JSON file
json_file_path = "robogpt_v3/robogpt_config/robot_config/robogpt.json"
   


# Global variables
bridge = CvBridge()
current_camera_info = None
current_image = None
window_open = True

def save_camera_info(camera_name, data):
    """Save camera information to the JSON file."""
    try:
        # Extract the necessary data from the CameraInfo message
        camera_info = {
            "frame_id": data.header.frame_id,
            "intrinsic_matrix": data.K,
            "height": data.height,
            "width": data.width
        }

        # Load existing JSON data from the file
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as file:
                json_data = json.load(file)
        else:
            rospy.logerr(f"JSON file {json_file_path} not found.")
            return

        # Save the extracted data under the camera_config section, keyed by camera_name
        if 'camera_config' not in json_data:
            json_data['camera_config'] = {}

        json_data['camera_config'][camera_name] = camera_info

        # Write the updated JSON data back to the file
        with open(json_file_path, 'w') as file:
            json.dump(json_data, file, indent=4)
        rospy.loginfo(f"Camera info for {camera_name} saved successfully.")
    except Exception as e:
        rospy.logerr(f"Failed to save camera info: {e}")

    # Close all OpenCV windows and stop the ROS node
    global window_open
    window_open = False
    cv2.destroyAllWindows()
    rospy.signal_shutdown("Camera info saved, shutting down.")

def camera_info_callback(msg):
    """Callback function to handle received CameraInfo messages."""
    global current_camera_info
    current_camera_info = msg

def image_callback(msg):
    """Callback function to handle received Image messages."""
    global current_image
    try:
        current_image = bridge.imgmsg_to_cv2(msg, "bgr8")
        if window_open:
            display_image(current_image)
    except CvBridgeError as e:
        rospy.logerr(f"CvBridgeError: {e}")

def display_image(image):
    """Display the image using OpenCV and handle key presses."""
    cv2.imshow("Camera Image", image)
    key = cv2.waitKey(1)
    if key == ord('Y') or key == ord('y'):
        enter_camera_name()
    elif key == ord('N') or key == ord('n'):
        rospy.loginfo("Skipping this camera.")
        global window_open
        window_open = False
        cv2.destroyAllWindows()
        rospy.signal_shutdown("Camera skipped, shutting down.")

def enter_camera_name():
    """Display a Tkinter popup to enter the camera name."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    camera_name = simpledialog.askstring("Camera Name", "Enter the name of the camera:")
    root.destroy()

    if camera_name:
        save_camera_info(camera_name, current_camera_info)

def subscribe_to_camera_info():
    """Initialize the ROS node and subscribe to the camera info and image topics."""
    rospy.init_node('camera_info_subscriber', anonymous=True)
    rospy.Subscriber('/camera/color/camera_info', CameraInfo, camera_info_callback)
    rospy.Subscriber('/camera/color/image_raw', Image, image_callback)
    rospy.loginfo("Subscribed to /camera/color/camera_info and /camera/color/image_raw topics.")
    try:
        rospy.spin()
    except KeyboardInterrupt:
        rospy.loginfo("Shutting down.")
    except Exception as e:
        rospy.logerr(f"Error occurred: {e}")
        subscribe_to_camera_info()

if __name__ == '__main__':
    subscribe_to_camera_info()
    cv2.destroyAllWindows()
