import cv2
import numpy as np
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

"""
Setting the reference image is necessary for proper usage of ObjectDetector.
For setting it, press 'r' by directing the camera (preferably) towards an empty plain surface.
"""

class ObjectDetector:
    def __init__(self, boundary_rect=(490, 200, 300, 300), image_topic="/camera/color/image_raw"):
        """
        Initializes the ObjectDetector with a ROS image subscriber and a detection boundary.
        boundary_rect is set to (490, 200, 300, 300) by default.
        image_topic: ROS topic from which image messages are received.
        """
        self.boundary_rect = boundary_rect
        self.bridge = CvBridge()
        self.latest_frame = None  # Latest received frame from ROS
        self.reference_gray = None  # Placeholder for the reference background
        self.image_topic = image_topic
        # Subscribe to the ROS image topic
        self.image_sub = rospy.Subscriber(self.image_topic, Image, self.image_callback)
        self.image_pub = rospy.Publisher("/masked_feed",Image,queue_size=10)
        # Wait for the first image message to initialize the reference background
        try:
            rospy.loginfo("Waiting for the first image message to set the reference background...")
            first_msg = rospy.wait_for_message(image_topic, Image, timeout=5.0)
            first_frame = self.bridge.imgmsg_to_cv2(first_msg, desired_encoding="bgr8")
            self.reference_gray = self.preprocess_frame(first_frame)
            rospy.loginfo("Reference background initialized.")
        except rospy.ROSException as e:
            rospy.logerr("Timeout waiting for first image message: %s", e)
            self.reference_gray = None

        # Set image dimensions (width x height)
        self.image_width = 640
        self.image_height = 480

        # Define a slightly smaller boundary rectangle (250x250)
        rect_width = 250
        rect_height = 250

        # Calculate top-left coordinates to center the boundary rectangle
        rect_x = (self.image_width - rect_width) // 2   # (640 - 250)//2 = 195
        rect_y = (self.image_height - rect_height) // 2  # (480 - 250)//2 = 115

        # Set the boundary_rect as a tuple: (x, y, width, height)
        self.boundary_rect = (rect_x, rect_y, rect_width, rect_height)

        # For fail-safe: initialize the display window with fixed dimensions.
        cv2.namedWindow("feed_window", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("feed_window", self.image_width, self.image_height)

    def image_callback(self, msg):
        """
        Callback for the image subscriber. Converts the ROS image message to an OpenCV image.
        """
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            self.latest_frame = cv_image
        except CvBridgeError as e:
            rospy.logerr("CvBridge Error: %s", e)

    def preprocess_frame(self, frame):
        """
        Convert frame to grayscale and apply Gaussian blur.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (21, 21), 0)

    def detect_objects(self, frame):
        """
        Detects objects in the frame by comparing it with the reference background.
        Returns:
            - object_detected: Boolean indicating if an object is found.
            - processed_frame: Frame with drawn boundary and status text.
            - detected_frame: Frame with bounding box and detection label if an object is found.
        """
        if self.reference_gray is None:
            return False, frame, frame
        # Preprocess current frame

        gray = self.preprocess_frame(frame)
        # Compute absolute difference between current frame and reference
        frame_diff = cv2.absdiff(self.reference_gray, gray)
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)  # Fill small gaps

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Default settings
        boundary_color = (0, 0, 255)
        object_detected = False
        detected_frame = frame.copy()  # Copy for saving

        # Check if any contour is inside the boundary
        x, y, w, h = self.boundary_rect
        for cnt in contours:
            if cv2.contourArea(cnt) < 1000:  # Ignore small noise
                continue

            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                if x < cx < x + w and y < cy < y + h:
                    boundary_color = (0, 255, 0)  # Change to green if object detected
                    object_detected = True

                    # Draw bounding box and label
                    cv2.rectangle(detected_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(detected_frame, "Object Found", (x, y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 1)
                    break  # Stop after first detected object

        # Draw boundary rectangle on live frame
        cv2.rectangle(frame, (x, y), (x + w, y + h), boundary_color, 2)

        # Display status
        status_text = "OK" if object_detected else ""
        status_color = (0, 255, 0) if object_detected else (0, 0, 255)
        frame = self.apply_grey_mask(frame)
        cv2.putText(frame, status_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)

        return object_detected, frame, detected_frame

    def save_frame(self, frame, object_detected):
        """
        Save the current frame when 's' is pressed.
        """
        filename = "detected_object.png" if object_detected else "no_object.png"
        cv2.imwrite(filename, frame)
        rospy.loginfo("Image saved as '%s'", filename)

    def reset_background(self):
        """
        Reset the reference background when 'r' is pressed.
        """
        if self.latest_frame is not None:
            self.reference_gray = self.preprocess_frame(self.latest_frame)
            rospy.loginfo("Reference background updated!")
        else:
            rospy.logwarn("No frame available to reset background.")

    def apply_grey_mask(self, frame):
        """
        Overlays a grey mask with slight opacity on the image,
        while leaving the area inside the boundary rectangle unmasked.
        """
        # Create an overlay filled with grey.
        overlay = frame.copy()
        grey_color = (0, 0, 0)  # grey color in BGR.
        alpha = 0.3              # opacity level for the grey mask.

        # Fill the entire overlay with the grey color.
        cv2.rectangle(overlay, (0, 0), (self.image_width, self.image_height), grey_color, thickness=-1)
        
        # "Cut out" the boundary rectangle by restoring the original image in that region.
        x, y, w, h = self.boundary_rect
        overlay[y:y+h, x:x+w] = frame[y:y+h, x:x+w]
        
        # Blend the overlay with the original frame.
        masked_frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        return masked_frame
    
    def run(self):
        """
        Start the object detection loop using frames received from the ROS image topic.
        """
        rate = rospy.Rate(30)  # 30 Hz loop rate
        while not rospy.is_shutdown():
            if self.latest_frame is not None:
                frame = self.latest_frame.copy()
                object_detected, processed_frame, detected_frame = self.detect_objects(frame)
                cv2.imshow("feed_window", processed_frame)
                ros_image = self.bridge.cv2_to_imgmsg(processed_frame, encoding="bgr8")
                self.image_pub.publish(ros_image)
                # Handle keypress events
                key = cv2.waitKey(1) & 0xFF
                if key == ord('s'):
                    self.save_frame(detected_frame if object_detected else processed_frame, object_detected)
                elif key == ord('r'):
                    self.reset_background()
                elif key == ord('q'):
                    break

            rate.sleep()

        cv2.destroyAllWindows()



if __name__ == "__main__":
    rospy.init_node('object_detector', anonymous=True)
    detector = ObjectDetector(image_topic="/camera/image")
    detector.run()