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

    This class provides functionality for detecting objects in a camera stream, extracting
    relevant features using detection algorithms. It subscribes to an MQTT broker
    to receive color and depth data from a robot's camera, performs object detection using
    specified algorithms, and extracts object features.

    Attributes:
        serial (str): The serial number of the robot's camera.
        client (mqtt_client.Client): MQTT client for communication with the robot.
        color_frame (numpy.ndarray): The last received color frame from the robot's camera.
        depth_frame (numpy.ndarray): The last received depth frame from the robot's camera.
        zero_shot (ZeroShotDetection): An object for zero-shot object detection.
        color_detection (ColorDetection): An object for color-based object detection.

    Methods:
        on_connect(client, userdata, flags, rc):
            Callback function for handling MQTT broker connection.

        on_message(client, userdata, msg):
            Callback function for handling MQTT messages, updating color and depth frames.

        extract_3d_info(detection_result: dict, color_frame: numpy.ndarray, depth_frame: numpy.ndarray) -> dict:
            Extracts dimensions and orientation using 3D point cloud of object and save the results in the detection_result.

        _run():
            Main loop for running object detection algorithms, updating results, and displaying frames.
    """
    def __init__(self):

        self.cam_name = rospy.get_param("/Object_detection_node/camera_name",default="camera")
        rospy.loginfo(f"Name of the camera running:: {self.cam_name}")

        self.bridge = CvBridge()
        self.image_sub = rospy.Subscriber(f"/{self.cam_name}/color/image_raw", Image, self.color_callback)
        self.depth_sub = rospy.Subscriber(f"/{self.cam_name}/depth/image_rect_raw", Image, self.depth_callback)
        self.detect_pub = rospy.Publisher(f"/{self.cam_name}_frame",Image,queue_size=10)
        self.color_frame = None
        self.depth_frame = None

        self.color_detection = ColorDetection()
        self.yolo_detection = YoloV8Detection()
        self.detection_buffer = DetectionBuffer()

    def color_callback(self, data):
        try:
            # Convert the ROS Image message to OpenCV format
            self.color_frame = self.bridge.imgmsg_to_cv2(data, "bgr8")

        except CvBridgeError as e:
            print(e)

    def depth_callback(self, data):
        try:
            # Convert the ROS Image message to OpenCV format
            # Convert the ROS Image message to a CV image
            depth_image = self.bridge.imgmsg_to_cv2(data, desired_encoding="passthrough")
            
            # Normalize the depth image to fall between 0 and 255
            depth_image = cv2.normalize(depth_image, None, 0, 255, cv2.NORM_MINMAX)

            # Convert the depth image to an 8-bit image (from a 32-bit float image)
            self.depth_frame = np.uint8(depth_image)
        except CvBridgeError as e:
            print(e)

    
    def extract_3d_info(self,detection_result,color_frame,depth_frame):
        """
        Extract 3D information from object detection results.

        This method takes object detection results, color and depth frames, and extracts
        3D information for each detected object. It calculates the object's dimensions and 
        orientation in 3D space. The height of the object is estimated based on the
        difference between the minimum and maximum points in the point cloud.

        Args:
            detection_result (dict): A dictionary containing object detection results.
            color_frame (numpy.ndarray): The color frame containing the detected objects.
            depth_frame (numpy.ndarray): The depth frame for the corresponding color frame.

        Returns:
            dict: A modified dictionary of object detection results with added 3D information,
                including dimensions and orientation for each detected object.
        """
    
        if not bool(detection_result): # Check if the detection_result is empty
            return
        
        for id,result in detection_result.items():
            [xmin,ymin,_] = result["xyxy"][0]
            [xmax,ymax,_] = result["xyxy"][1]

            color_img = color_frame[ymin:ymax,xmin:xmax]
            depth_img = depth_frame[ymin:ymax,xmin:xmax]

            # Creating RGBD image and pointcloud using RGB and depth image
            color_obj = o3d.geometry.Image(np.ascontiguousarray(color_img).astype(np.float32))
            depth_obj = o3d.geometry.Image(np.ascontiguousarray(depth_img).astype(np.float32))
            rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(color_obj,depth_obj)
            pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, o3d.camera.PinholeCameraIntrinsic(color_frame.shape[1], color_frame.shape[0], fx = 645.815, fy = 645.815, cx = 645.372, cy = 357.093)) 

            pcl_array = np.asarray(pcd.points)
            if pcl_array.shape[0] == 0: # Check if the pointcloud is empty
                continue
            # Calculate the centroid of the point cloud
            centroid = np.mean(pcl_array, axis=0)

            # Subtract the centroid from the points to make the PCA more robust
            centered_points = pcl_array - centroid

            # Perform Principal Component Analysis (PCA) to get the principal axes
            covariance_matrix = np.dot(centered_points.T, centered_points)/ len(pcl_array)
            eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)

            # The eigenvector corresponding to the smallest eigenvalue is the normal vector
            # of the plane containing the box faces, which gives the orientation of the box
            box_orientation = eigenvectors[:, 0]

            # Define the camera frame axes
            camera_x_axis = np.array([1, 0, 0])
            camera_y_axis = np.array([0, 1, 0])
            camera_z_axis = np.array([0, 0, 1])

            # Calculate the rotation matrix from box_orientation to camera frame
            rotation_matrix = np.column_stack((camera_x_axis, camera_y_axis, box_orientation))

            # Convert the rotation matrix to Euler angles (in degrees)
            r = R.from_matrix(rotation_matrix)
            euler_angles = list(r.as_euler('xyz', degrees=True)) 

            # Length is the maximum eigenvalue (extent along the longest axis)
            # Width is the second maximum eigenvalue (extent along the second longest axis)
            length = 2.0 * np.sqrt(eigenvalues[-1])
            width = 2.0 * np.sqrt(eigenvalues[-2])

            # Height of the object (Subtracting the minimum and maximum height of pointcloud)
            # TODO: The approach would work only if there is a surface like Table, or a board behind the object
            min_point = np.min(pcd.points, axis=0)
            max_point = np.max(pcd.points, axis=0)
            height = max_point[2]-min_point[2]

            detection_result[id]["dimension"] = [length - 0.015, width - 0.015, height - 0.015]
            detection_result[id]["orientation"] = euler_angles
        
        # commented because it fills up the terminal
        # print("DETECTION RESULT:::: ", detection_result)
            
        return detection_result
    

    def merge_and_append_detections(self, data, new_data):
        old_objects = {}  # map "object" to detection keys like "detection_1", "detection_0", etc.

        # Create old_objects dictionary
        for key, value in data["10.42.0.53"].items():
            detected_object = value.get("detected_object")
            if detected_object is not None:
                old_objects[detected_object] = key

        # Find the last big detection key
        last_big_detection_key = max((k for k in data["10.42.0.53"].keys() if k.startswith("detection_")), key=lambda x: int(x.split("_")[1]))

        # Iterate through new_data and append new detections to data
        for new_key, new_value in new_data["10.42.0.53"].items():
            detected_object = new_value.get("detected_object")
            if detected_object is not None:
                if detected_object in old_objects:
                    # Update the existing detection in data
                    old_key = old_objects[detected_object]
                    data["10.42.0.53"][old_key].update(new_value)
                else:
                    # Append new detection with incremented key
                    new_detection_key = "detection_" + str(int(last_big_detection_key.split("_")[1]) + 1)
                    data["10.42.0.53"][new_detection_key] = new_value
                    last_big_detection_key = new_detection_key

        return data
    
    def signal_handler(sig, frame):
        rospy.loginfo("Keyboard interrupt received. Exiting...")
        rospy.signal_shutdown("KeyboardInterrupt")

    def _run(self):
        """
        Execute object detection and feature extraction algorithms in a continuous loop. It is launched with launch.py script.

        This method continuously reads camera data, performs object detection using specified
        algorithms (specified by the user), and extracts object features. The results are updated and displayed in real-time.

        Note:
            The method relies on the `color_frame` and `depth_frame` attributes to receive camera data.
            Ensure that the MQTT client is properly connected and receiving data before calling this method.
        """
        start_time = time.time()
        image_sent = False
        
        while True:

            # Reading algorithm configuration data
            f = open(robot_camera_path)
            robogpt_data = json.loads(f.read())
            algorithm_list = robogpt_data["object_detection_alg"]
            f.close()

            detection_results = {}
            i = 0
            if self.color_frame is None: # If the camera feed is None
                rospy.logerr("No frame detected. Please check the Topic name.") 
                time.sleep(0.1)
                rospy.logerr("Exiting Vision stack")
                break

            color_frame_copy = np.copy(self.color_frame)
            depth_frame_copy = np.copy(self.depth_frame)
            
           
            # Running the algorithms layer specified by the user
            for algorithms in algorithm_list:
                if algorithms == "color_detection":
                    detection_results = self.color_detection.run(detection_results,color_frame_copy,depth_frame_copy)
                elif algorithms == "yolo_detection":
                    detection_results = self.yolo_detection.run(detection_results, color_frame_copy, depth_frame_copy)
            
            # Extracting 3D features of objects detected
            if bool(detection_results):
                detection_results = self.extract_3d_info(detection_results,color_frame_copy,depth_frame_copy)
            
            # Saving the results in detection_results.json
            robot_dict = json.loads(open(detection_results_path).read())
            robot_dict[self.cam_name] = detection_results

            # robot_dict = self.detection_buffer.merge_frames(robot_dict,camera_ip)
            for robot_ip, detections in robot_dict.items():
                for detection_key, detection_data in detections.items():
                    # Check if any value is of non-serializable type (e.g., numpy.ndarray)
                    for key, value in detection_data.items():
                        if isinstance(value, np.ndarray):
                            # Convert numpy arrays to lists
                            detection_data[key] = value.tolist()
                        elif isinstance(value, np.uint16):
                            # Convert uint16 to int
                            detection_data[key] = int(value)

            try:
                with open(f"{detection_results_path}", 'w') as f:
                    json.dump(robot_dict, f)
            except Exception as e:
                print("write to file failed - saving detection results", e)

            # Displaying the bounding boxes and object class on color frame
            if bool(detection_results):
                for _,result in detection_results.items():
                    [[xmin,ymin,_],[xmax,ymax,_]] = result["xyxy"]
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
    signal.signal(signal.SIGINT,object_detection.signal_handler)
    try:
        # Run the object detection implementation
        object_detection._run()
        rospy.spin()

    except rospy.ROSInterruptException:
        rospy.loginfo("ROS Interrupt Exception occurred. Node terminated.")