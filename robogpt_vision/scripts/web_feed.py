#!/usr/bin/env python
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2
import threading
import base64
import time
import numpy as np
import rospkg
from azure.messaging.webpubsubservice import WebPubSubServiceClient
import sys

# Get the package path for robogpt_agents
rospack = rospkg.RosPack()
package_path = rospack.get_path('robogpt_agents')
sys.path.append(package_path)

from robogpt_agents.scripts.cloud_auth_and_llm.token_generator import get_connection_string

# Initialize the CvBridge
bridge = CvBridge()

# Azure Web PubSub client initialization
sender = WebPubSubServiceClient.from_connection_string(get_connection_string(), hub="robot_feed")

# Get the camera name based on which the image topic is given to subscirber
cam_name = rospy.get_param("/Object_detection_node/camera_name",default="camera")

# Function to encode and send the image frame to Azure WebPubSub
def encode_and_send_frame(frame):
    # Convert the image frame to JPEG
    encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
    
    # Encode the JPEG image into base64 format
    message = base64.b64encode(buffer)
    
    # Send the base64 encoded message to Azure Web PubSub
    sender.send_to_all(message=message, content_type='application/octet-stream')

    # Add a small delay to simulate a 30 FPS stream (1/30 seconds)
    time.sleep(1/30)

# ROS callback function to handle incoming image messages
def image_callback(msg):
    try:
        # Convert the ROS Image message to an OpenCV image
        cv2_img = bridge.imgmsg_to_cv2(msg, "bgr8")

        # Start a new thread to handle the encoding and sending of the image
        t1 = threading.Thread(target=encode_and_send_frame, args=(cv2_img,))
        t1.start()
    
    except CvBridgeError as e:
        rospy.logerr(f"Error converting ROS Image to OpenCV: {e}")

# Function to subscribe to the detection image topic
def image_listener():
    # Initialize the ROS node
    rospy.init_node('detection_image_subscriber', anonymous=True)
    
    # Subscribeing to the image topic of camera
    rospy.Subscriber(f"/{cam_name}_frame", Image, image_callback)
    
    # Keep the node alive to keep listening to the topic
    rospy.spin()

# Main function to start the ROS node and the WebPubSub client
if __name__ == '__main__':
    try:
        # Start the ROS image subscriber
        v1 = threading.Thread(target=image_listener)
        v1.start()

    except rospy.ROSInterruptException:
        pass
