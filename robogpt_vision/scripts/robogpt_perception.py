#!/usr/bin/env python3
import os
import sys
import cv2
import json
import time
import rospy
import signal
import rospkg
import numpy as np
import open3d as o3d
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from scipy.spatial.transform import Rotation as R

################## CONFIG PATHS #######################################
rospack = rospkg.RosPack()
package_path = rospack.get_path('robogpt_vision')    
sys.path.append(package_path)

from scripts.object_detection.model_instances.yolov8_detect import YoloV8Detection
from scripts.feature_detection.color_detection import ColorDetection
from scripts.object_detection.model_instances.buffer import DetectionBuffer

# Construct the full path to the YAML file
robot_camera_path = os.path.join(package_path,"config/vision_config.json")
detection_results_path = os.path.join(package_path,"config/detection_results.json")


class object_detection_implementation:
    """
    Skill for object detection and feature extraction in a robotic system's scene.

    This class provides functionality for detecting objects in a camera stream and extracting
    relevant features using detection algorithms. It subscribes to a ROS Topic
    to receive color and depth data from a robot's camera, performs object detection using
    specified algorithms, and extracts object features.

    Attributes:
        cam_name (str): Name of the camera connected.
        color_frame (numpy.ndarray): The last received color frame from the robot's camera.
        depth_frame (numpy.ndarray): The last received depth frame from the robot's camera.
        yolov8 (YoloV8Detection): An object for yolov8 based object detection.
        color_detection (ColorDetection): An object for color-based object detection.

    Methods:
        color_callback(data):
            Handles color image data from ROS topic subscription.

        depth_callback(data):
            Handles depth image data from ROS topic subscription.

        extract_3d_info(detection_result: dict, color_frame: numpy.ndarray, depth_frame: numpy.ndarray) -> dict:
            Extracts 3D dimensions and orientation from the point cloud of detected objects.

        _run():
            Main loop for executing object detection algorithms, updating results, and displaying frames.
    """
    def __init__(self):
        # Initialize camera parameters and ROS subscribers/publishers
        self.cam_name = rospy.get_param("/Object_detection_node/camera_name", default="camera")
        rospy.loginfo(f"Name of the camera running:: {self.cam_name}")
        self.vision_sim = rospy.get_param("vision_sim", default="off")
        if self.vision_sim == "off":
            self.topic_suffix = "aligned_depth_to_color"
        if self.vision_sim == "on":
            self.topic_suffix = "depth"
        self.bridge = CvBridge()
        self.image_sub = rospy.Subscriber(f"/{self.cam_name}/color/image_raw", Image, self.color_callback)
        self.depth_sub = rospy.Subscriber(f"/{self.cam_name}/{self.topic_suffix}/image_raw", Image, self.depth_callback)
        self.detect_pub = rospy.Publisher(f"/{self.cam_name}_frame", Image, queue_size=10)
        self.color_frame = None
        self.depth_frame = None

        # Initialize detection algorithms
        self.color_detection = ColorDetection()
        self.yolo_detection = YoloV8Detection()
        self.detection_buffer = DetectionBuffer()

    def color_callback(self, data):
        try:
            # Convert the ROS Image message to OpenCV format for color frames
            self.color_frame = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            print(e)

    def depth_callback(self, data):
        try:
            # Convert the ROS Image message to OpenCV format for depth frames
            self.depth_frame = self.bridge.imgmsg_to_cv2(data, desired_encoding="16UC1")
        except CvBridgeError as e:
            print(e)

    def extract_3d_info(self, detection_result, color_frame, depth_frame):
        """
        Extract 3D information from object detection results.

        This method processes object detection results along with color and depth frames to extract
        3D information for each detected object, including dimensions and orientation.

        Args:
            detection_result (dict): Object detection results.
            color_frame (numpy.ndarray): Color frame with detected objects.
            depth_frame (numpy.ndarray): Depth frame corresponding to the color frame.

        Returns:
            dict: Updated detection results with 3D information.
        """
        if not bool(detection_result):  # Check if detection results are empty
            return
        
        for id, result in detection_result.items():
            [xmin, ymin, _] = result["xyxy"][0]
            [xmax, ymax, _] = result["xyxy"][1]

            color_img = color_frame[ymin:ymax, xmin:xmax]
            depth_img = depth_frame[ymin:ymax, xmin:xmax]

            # Create RGBD image and point cloud from color and depth images
            color_obj = o3d.geometry.Image(np.ascontiguousarray(color_img).astype(np.float32))
            depth_obj = o3d.geometry.Image(np.ascontiguousarray(depth_img).astype(np.float32))
            rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(color_obj, depth_obj)
            pcd = o3d.geometry.PointCloud.create_from_rgbd_image(
                rgbd_image, 
                o3d.camera.PinholeCameraIntrinsic(
                    color_frame.shape[1], color_frame.shape[0], 
                    fx=645.815, fy=645.815, cx=645.372, cy=357.093
                )
            )

            pcl_array = np.asarray(pcd.points)
            if pcl_array.shape[0] == 0:  # Check if the point cloud is empty
                continue

            # Calculate the centroid of the point cloud
            centroid = np.mean(pcl_array, axis=0)

            # Center the points for PCA
            centered_points = pcl_array - centroid

            # Perform PCA to get principal axes
            covariance_matrix = np.dot(centered_points.T, centered_points) / len(pcl_array)
            eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)

            # Determine box orientation from PCA results
            box_orientation = eigenvectors[:, 0]

            # Define camera frame axes
            camera_x_axis = np.array([1, 0, 0])
            camera_y_axis = np.array([0, 1, 0])
            camera_z_axis = np.array([0, 0, 1])

            # Calculate rotation matrix from box orientation to camera frame
            rotation_matrix = np.column_stack((camera_x_axis, camera_y_axis, box_orientation))

            # Convert rotation matrix to Euler angles
            r = R.from_matrix(rotation_matrix)
            euler_angles = list(r.as_euler('xyz', degrees=True))

            # Calculate object dimensions
            length = 2.0 * np.sqrt(eigenvalues[-1])
            width = 2.0 * np.sqrt(eigenvalues[-2])

            # Estimate object height
            min_point = np.min(pcd.points, axis=0)
            max_point = np.max(pcd.points, axis=0)
            height = max_point[2] - min_point[2]

            detection_result[id]["dimension"] = [length - 0.015, width - 0.015, height - 0.015]
            detection_result[id]["orientation"] = euler_angles
        
        return detection_result

    def signal_handler(sig, frame):
        rospy.loginfo("Keyboard interrupt received. Exiting...")
        rospy.signal_shutdown("KeyboardInterrupt")

    def _run(self):
        """
        Execute object detection and feature extraction algorithms in a continuous loop.

        This method continuously reads camera data, performs object detection using specified
        algorithms, and extracts object features. The results are updated and displayed in real-time.
        """
        start_time = time.time()
        image_sent = False
        
        while True:
            # Load algorithm configuration data
            f = open(robot_camera_path)
            robogpt_data = json.loads(f.read())
            algorithm_list = robogpt_data["object_detection_alg"]
            f.close()

            detection_results = {}
            i = 0
            if self.color_frame is None:  # Check if the camera feed is available
                rospy.logerr("No frame detected. Please check the Topic name.") 
                time.sleep(0.1)
                rospy.logerr("Exiting Vision stack")
                break

            color_frame_copy = np.copy(self.color_frame)
            depth_frame_copy = np.copy(self.depth_frame)
            
            # Run detection algorithms specified by the user
            for algorithms in algorithm_list:
                if algorithms == "color_detection":
                    detection_results = self.color_detection.run(detection_results, color_frame_copy, depth_frame_copy)
                elif algorithms == "yolo_detection":
                    detection_results = self.yolo_detection.run(detection_results, color_frame_copy, depth_frame_copy)
            
            # Extract 3D features of detected objects
            if bool(detection_results):
                detection_results = self.extract_3d_info(detection_results, color_frame_copy, depth_frame_copy)
            
            # Save results to detection_results.json
            robot_dict = json.loads(open(detection_results_path).read())
            robot_dict[self.cam_name] = detection_results

            # Convert non-serializable types to serializable ones
            for robot_ip, detections in robot_dict.items():
                for detection_key, detection_data in detections.items():
                    for key, value in detection_data.items():
                        if isinstance(value, np.ndarray):
                            detection_data[key] = value.tolist()
                        elif isinstance(value, np.uint16):
                            detection_data[key] = int(value)

            try:
                with open(f"{detection_results_path}", 'w') as f:
                    json.dump(robot_dict, f)
            except Exception as e:
                print("write to file failed - saving detection results", e)

            # Display bounding boxes and object class on color frame
            if bool(detection_results):
                for _, result in detection_results.items():
                    [[xmin, ymin, _], [xmax, ymax, _]] = result["xyxy"]
                    cv2.rectangle(color_frame_copy, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                    cv2.putText(color_frame_copy, f"{result['detected_object']}", (xmin, ymin), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

            frame_data = color_frame_copy.tobytes()
            cv2.imshow(f'{self.cam_name+"_frame"}', color_frame_copy)
            
            # Convert the OpenCV image (BGR format) to a ROS Image message
            detection_feed = self.bridge.cv2_to_imgmsg(color_frame_copy, "bgr8")
        
            # Publish the ROS Image message
            self.detect_pub.publish(detection_feed)

            elapsed_time = time.time() - start_time
            if not image_sent and elapsed_time > 20:
                image_sent = True
        
            key = cv2.waitKey(1)
            if key == ord('q'):
                break

if __name__ == "__main__":
    # Initialize the ROS node
    rospy.init_node("Object_detection_node")

    # Create an object of your detection class
    object_detection = object_detection_implementation()

    # Handle keyboard interrupt
    signal.signal(signal.SIGINT, object_detection.signal_handler)
    try:
        # Run the object detection implementation
        object_detection._run()
        rospy.spin()

    except rospy.ROSInterruptException:
        rospy.loginfo("ROS Interrupt Exception occurred. Node terminated.")