#!/usr/bin/python3

import cv2
import time
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import rospy

class VideoRecord():
    def __init__(self, ros_topic: str, output_file: str, duration: int, frame_width: int = 640, frame_height: int = 480, fps: int = 30):
        self.ros_topic = ros_topic
        self.output_file = output_file
        self.duration = duration
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps = fps

    def record_camera_feed(self):
        """
        Records the camera feed from a ROS topic and saves it to a video file for the given duration.

        Parameters:
            ros_topic (str): ROS topic to subscribe to for the camera feed.
            output_file (str): Path to save the recorded video file.
            duration (int): Duration to record the video in seconds.
            frame_width (int): Width of the video frame (default is 640).
            frame_height (int): Height of the video frame (default is 480).
            fps (int): Frames per second for the recorded video (default is 30).
        """
        rospy.init_node('camera_recorder', anonymous=True)
        
        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'XVID')  # Use 'XVID' for .avi files or 'mp4v' for .mp4 files
        out = cv2.VideoWriter(self.output_file, fourcc, self.fps, (self.frame_width, self.frame_height))

        bridge = CvBridge()
        frames = []

        def image_callback(msg):
            """Callback to process image messages from the ROS topic."""
            try:
                cv_image = bridge.imgmsg_to_cv2(msg, "bgr8")
                frames.append(cv_image)
            except Exception as e:
                rospy.logerr(f"Error converting ROS Image to OpenCV: {e}")

        rospy.Subscriber(self.ros_topic, Image, image_callback)

        print(f"Recording started. Video will be saved to {self.output_file}")

        start_time = time.time()
        rate = rospy.Rate(self.fps)

        while not rospy.is_shutdown() and time.time() - start_time < self.duration:
            if frames:
                frame = frames.pop(0)
                out.write(frame)

                # Show the frame (optional, can be removed if not needed)
                cv2.imshow('Recording', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            rate.sleep()

        # Release resources
        out.release()
        cv2.destroyAllWindows()
        print("Recording completed and saved.")

