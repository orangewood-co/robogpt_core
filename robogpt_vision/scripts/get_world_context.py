#!/usr/bin/env python3

import os
import sys
import time
import json
import rospy
import rospkg
import tf2_ros
import numpy as np
from typing import Type, List
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from scipy.spatial.transform import Rotation as R
from tf.transformations import euler_matrix, euler_from_matrix
from robogpt_vision.srv import GetWorldContext, GetWorldContextResponse

# Intrinsic camera matrix
inst_matrix = np.array([
    [909.3656005859375, 0.0, 658.6245727539062],
    [0.0, 908.4342651367188, 359.7082824707031],
    [0, 0, 1.0]
])

##############################################################################

# Global variables for file paths
rospack = rospkg.RosPack()
vision_path = rospack.get_path('robogpt_vision') 
agent_path = rospack.get_path('robogpt_agents') 
detection_results_path = os.path.join(vision_path, "config/detection_results.json")
poses_path = os.path.join(agent_path, "config/robot_config/robot_pose.json")

###############################################################################

class XImgToBaseImplementation:
    """
    Converts image frame coordinates to robot base frame coordinates for a specific object.

    This class provides functionality to transform image coordinates (Ximg) to robot base coordinates (Xbase)
    for a specified object. It considers the transformation matrix between the robot base and the camera,
    as well as the intrinsic matrix of the camera.

    Methods:
        read_json_file(file_name: str) -> dict:
            Reads data from a JSON file and returns it as a dictionary.

        get_home_pose() -> list:
            Retrieves the home pose of the robot from the robot_pose.json file.

        get_T_cam_base(parent_frame: str, camera_name: str) -> list:
            Retrieves the transformation matrix between the camera and the robot base using TF2.

        get_ximg(object_name: str, camera_name: str) -> list:
            Retrieves the object's pose in the image frame.

        get_orientation(object_name: str, parent_frame: str, camera_name: str) -> list or None:
            Retrieves the object's orientation in the robot base frame.

        get_length(object_name: str, parent_frame: str, camera_name: str) -> list or None:
            Retrieves the dimensions and orientation of the object in the robot base frame.

        Ximg2Xbase(Ximg: list, parent_frame: str, camera_name: str) -> np.ndarray:
            Converts image coordinates to robot base coordinates.

        _run(req):
            Service callback to handle conversion requests.

        _arun(ximg: List[str]):
            Async version of _run (not supported).
    """

    def __init__(self):
        """
        Initializes the ROS node and service.
        """
        # rospy.init_node('get_world_context_service')
        service = rospy.Service('get_world_context', GetWorldContext, self._run)
        rospy.loginfo("Service 'get_world_context' is ready")
        self.robot_name = rospy.get_param("/robot_model", default="sim")
        self.return_direct = False  # Flag to handle direct return in case of errors

    def get_package_path(self, package_name: str) -> str:
        """
        Retrieves the file system path of a ROS package.

        Args:
            package_name (str): The name of the ROS package.

        Returns:
            str: The path to the package directory, or None if not found.
        """
        rospack = rospkg.RosPack()
        try:
            package_path = rospack.get_path(package_name)
            return package_path
        except rospkg.ResourceNotFound:
            rospy.logerr(f"Package '{package_name}' not found!")
            return None

    def read_json_file(self, file_name: str) -> dict:
        """
        Reads data from a JSON file and returns it as a dictionary.

        Args:
            file_name (str): Path to the JSON file.

        Returns:
            dict: Parsed JSON data.
        """
        try:
            with open(file_name, 'r') as f:
                data = json.load(f)
            rospy.loginfo(f"Successfully read JSON file: {file_name}")
            return data
        except Exception as e:
            rospy.logerr(f"Error reading JSON file '{file_name}': {e}")
            return {}

    def get_home_pose(self) -> list:
        """
        Retrieves the home pose of the robot from the robot_pose.json file.

        Returns:
            list: Home pose as [x, y, z, roll, pitch, yaw].
        """
        try:
            robot_dict = self.read_json_file(poses_path)
            robot_dict = robot_dict.get(self.robot_name, {})
            home_pose = robot_dict.get("orient", [])
            if not home_pose:
                rospy.logwarn("Home pose not found in JSON.")
            return home_pose
        except Exception as e:
            rospy.logerr(f"Error getting robot home pose: {e}")
            self.return_direct = True
            return []

    def get_T_cam_base(self, parent_frame: str, camera_name: str) -> list:
        """
        Retrieves the transformation matrix between the camera and the robot base using TF2.

        Args:
            parent_frame (str): The parent coordinate frame.
            camera_name (str): The name of the camera.

        Returns:
            list: Transformation matrix as a list, or empty list if failed.
        """
        try:
            tf_buffer = tf2_ros.Buffer()
            listener = tf2_ros.TransformListener(tf_buffer)
            time.sleep(1.0)  # Allow buffer to fill
            rospy.loginfo("TFBuffer connection succeeded")
        except Exception as e:
            rospy.logerr(f"TFBuffer connection failed: {e}")
            return []

        while not rospy.is_shutdown():
            try:
                cam_frame = f"{camera_name}_color_optical_frame"
                trans = tf_buffer.lookup_transform(parent_frame, cam_frame, rospy.Time(0), rospy.Duration(1.0))
                rospy.loginfo(f"Transform found between {parent_frame} and {cam_frame}")
            except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
                rospy.logwarn(f"Transform lookup failed: {e}")
                return []

            # Extract rotation and translation
            q = np.array([
                trans.transform.rotation.x,
                trans.transform.rotation.y,
                trans.transform.rotation.z,
                trans.transform.rotation.w
            ])
            rot = R.from_quat(q)
            r_matrix = rot.as_matrix()
            t_vector = np.array([
                trans.transform.translation.x,
                trans.transform.translation.y,
                trans.transform.translation.z
            ])

            # Construct homogeneous transformation matrix
            T = np.vstack((
                np.hstack((r_matrix, t_vector.reshape(3, 1))),
                np.array([0, 0, 0, 1.0])
            ))

            rospy.loginfo("Transformation matrix successfully constructed.")
            return T.tolist()

    def get_ximg(self, object_name: str, camera_name: str) -> list:
        """
        Retrieves the object's pose in the image frame.

        Args:
            object_name (str): Name of the object.
            camera_name (str): Name of the camera.

        Returns:
            list: Image coordinates [Ximg_x, Ximg_y, Ximg_depth], or empty list if not found.
        """
        try:
            data = self.read_json_file(detection_results_path)
            camera_data = data.get(camera_name, {})

            for obj_id, obj_info in camera_data.items():
                if obj_info.get('detected_object') == object_name:
                    center_pt = obj_info.get('center_pt', [0, 0])
                    depth = obj_info.get('depth_at_center', 0) / 1000.0  # Convert to meters
                    rospy.loginfo(f"Object '{object_name}' found at {center_pt} with depth {depth}m")
                    return [center_pt[0], center_pt[1], depth]
            
            rospy.logwarn(f"Object '{object_name}' not found in camera '{camera_name}' data.")
            return []
        except Exception as e:
            rospy.logerr(f"Error retrieving object pose in image frame: {e}")
            self.return_direct = True
            return []

    def get_orientation(self, object_name: str, parent_frame: str, camera_name: str) -> list:
        """
        Retrieves the object's orientation in the robot base frame.

        Args:
            object_name (str): Name of the object.
            parent_frame (str): Parent coordinate frame.
            camera_name (str): Name of the camera.

        Returns:
            list or None: Orientation as [roll, pitch, yaw], or None if not found.
        """
        try:
            robogpt_vision_path = self.get_package_path('robogpt_vision')
            data = self.read_json_file(detection_results_path)
            camera_data = data.get(camera_name, {})

            for obj_id, obj_info in camera_data.items():
                if obj_info.get('detected_object') == object_name:
                    orientation_euler = obj_info.get("orientation", [0, 0, 0])
                    rotation_matrix = euler_matrix(*orientation_euler, axes="sxyz")
                    T_cam_base = np.round(np.array(self.get_T_cam_base(parent_frame, camera_name))[:3, :3])
                    orientation_base = euler_from_matrix(T_cam_base @ rotation_matrix)
                    rospy.loginfo(f"Orientation in base frame: {orientation_base}")
                    return orientation_base.tolist()
            
            rospy.logwarn(f"Orientation for object '{object_name}' not found.")
            return None
        except Exception as e:
            rospy.logerr(f"Error retrieving object orientation: {e}")
            return None

    def get_length(self, object_name: str, parent_frame: str, camera_name: str) -> list:
        """
        Retrieves the dimensions and orientation of the object in the robot base frame.

        Args:
            object_name (str): Name of the object.
            parent_frame (str): Parent coordinate frame.
            camera_name (str): Name of the camera.

        Returns:
            list or None: Dimensions [length, width, height] and orientation, or None if not found.
        """
        try:
            data = self.read_json_file(detection_results_path)
            camera_data = data.get(camera_name, {})

            for obj_id, obj_info in camera_data.items():
                if obj_info.get('detected_object') == object_name:
                    dimension = obj_info.get('dimension', [0, 0, 0])
                    orientation_euler = obj_info.get("orientation", [0, 0, 0])
                    rotation_matrix = euler_matrix(*orientation_euler, axes="sxyz")
                    T_cam_base = np.round(np.array(self.get_T_cam_base(parent_frame, camera_name))[:3, :3])
                    dim_base = T_cam_base @ np.array(dimension[:3])
                    orientation_base = [0, 0, 0, 1]  # Placeholder for orientation
                    rospy.loginfo(f"Dimensions in base frame: {np.abs(dim_base[:3])}, Orientation: {orientation_base}")
                    return np.abs(dim_base[:3]).tolist(), orientation_base
            rospy.logwarn(f"Dimensions for object '{object_name}' not found.")
            return None
        except Exception as e:
            rospy.logerr(f"Error retrieving object dimensions: {e}")
            return None

    def Ximg2Xbase(self, Ximg: list, parent_frame: str, camera_name: str) -> np.ndarray:
        """
        Converts image coordinates to robot base coordinates.

        Args:
            Ximg (list): Image coordinates [Ximg_x, Ximg_y, Ximg_depth].
            parent_frame (str): Parent coordinate frame.
            camera_name (str): Name of the camera.

        Returns:
            np.ndarray: Robot base coordinates [Xbase_x, Xbase_y, Xbase_z].
        """
        try:
            T_cam_base = self.get_T_cam_base(parent_frame, camera_name)
            if not T_cam_base:
                rospy.logerr("Transformation matrix between camera and base not available.")
                return np.array([0, 0, 0])

            Z = Ximg[2]
            Ximg_homogeneous = np.array([Ximg[0], Ximg[1], 1.0])
            Xcam = Z * np.linalg.inv(inst_matrix) @ Ximg_homogeneous
            Xcam_homogeneous = np.append(Xcam, 1.0)
            Xbase = np.dot(T_cam_base, Xcam_homogeneous)

            rospy.loginfo(f"Converted base coordinates: {Xbase[:3]}")
            return Xbase[:3]
        except Exception as e:
            rospy.logerr(f"Error converting image coordinates to robot base: {e}")
            self.return_direct = True
            return np.array([0, 0, 0])

    def _run(self, req):
        """
        Service callback to handle conversion requests.

        Args:
            req: Service request containing object name, parent frame, camera name, and orientation flag.

        Returns:
            GetWorldContextResponse: Response containing the converted coordinates.
        """
        try:
            rospy.loginfo(f"Received request from robot: {self.robot_name}")
            object_name = req.object_name
            parent_frame = req.parent_frame
            camera_name = req.camera_name
            include_orientation = getattr(req, 'include_ort', False)

            # Retrieve image coordinates of the object
            Ximg = self.get_ximg(object_name, camera_name)
            if not Ximg:
                rospy.logwarn("Image coordinates not found. Returning empty response.")
                return GetWorldContextResponse(Xbase=[])

            # Convert image coordinates to base coordinates
            Xbase = self.Ximg2Xbase(Ximg, parent_frame, camera_name)

            # Retrieve and adjust orientation
            orientation_assumption = self.get_home_pose()
            if orientation_assumption:
                orientation = orientation_assumption[3:]  # Extract [roll, pitch, yaw]
            else:
                orientation = [0, 0, 0]
                rospy.logwarn("Using default orientation due to missing home pose.")

            # Adjust the Z-coordinate with an offset
            Xbase[2] += 0.01  # Apply a fixed offset

            # Prepare the response with position and orientation
            Xbase_extended = [
                Xbase[0],
                Xbase[1],
                Xbase[2],
                orientation[0],
                orientation[1],
                orientation[2]
            ]
            rospy.loginfo(f"Responding with base coordinates and orientation: {Xbase_extended}")
            return GetWorldContextResponse(Xbase=Xbase_extended)

        except Exception as e:
            rospy.logerr(f"ximg2xbase error: {e}")
            return GetWorldContextResponse(Xbase=[])

    def _arun(self, ximg: List[str]):
        """
        Async version of _run (not supported).

        Args:
            ximg (List[str]): Image coordinates.

        Raises:
            NotImplementedError: Always raised as async is not supported.
        """
        raise NotImplementedError("XImgToBaseImplementation does not support async operations.")
    
def main():
    try:
        # Instantiate the service class
        service_instance = XImgToBaseImplementation()
        
        # Keep the node running
        rospy.spin()
    except rospy.ROSInterruptException:
        rospy.loginfo("ROS Interrupt Exception caught. Shutting down.")


if __name__ == "__main__":
    main()