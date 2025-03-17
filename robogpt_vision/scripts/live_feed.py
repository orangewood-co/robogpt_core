#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

def main():
    # Initialize the ROS node
    # rospy.init_node('camera_publisher', anonymous=True)

    # Create a publisher for the camera feed
    pub = rospy.Publisher('/live_feed', Image, queue_size=10)

    # Create a CvBridge object for converting OpenCV images to ROS Image messages
    bridge = CvBridge()

    # Open a connection to the camera (0 for the default camera)
    cap = cv2.VideoCapture(4)

    if not cap.isOpened():
        rospy.logerr("Could not open the camera.")
        return

    # Set the publishing rate
    rate = rospy.Rate(10)  # 10 Hz

    while not rospy.is_shutdown():
        # Capture a frame from the camera
        ret, frame = cap.read()

        if not ret:
            rospy.logwarn("Failed to capture image.")
            continue

        try:
            # Convert the OpenCV image to a ROS Image message
            image_msg = bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            # Publish the Image message
            pub.publish(image_msg)

            # Sleep to maintain the publishing rate
            rate.sleep()
        except rospy.ROSInterruptException:
            break
        except Exception as e:
            rospy.logerr(f"Error: {e}")

    # Release the camera resource
    cap.release()

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
