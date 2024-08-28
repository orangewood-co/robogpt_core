import json
import os
import sys
import time
import cv2
import rospy
import tf2_ros
import numpy as np
from typing import Type, List
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from scipy.spatial.transform import Rotation as R
from tf.transformations import euler_matrix,euler_from_matrix

robot_home_file_path = os.path.join(os.getcwd(),"config/robot_pose.json")

inst_matrix = np.array([[607.379638671875, 0, 323.45916748046875],
                        [0, 607.0968627929688, 245.50621032714844],
                        [0, 0, 1]])

global marker_data
marker_data = "config/marker.json"
global depth

class aruco_img_2_base_definition(BaseModel):
    marker_id: str = Field(description="aruco marker's id number")
    robot_ip: str = Field(description="ip address of the robot")
    include_ort: bool = Field(default=False,description="if the object orientation needs to considered")

class aruco_img_2_base_implementation(BaseTool):
    """
    Convert image frame coordinates to robot base frame coordinates for a specific object.

    This class provides functionality to convert image coordinates (Ximg) to robot base coordinates (Xbase)
    for a specified object. It takes into account the transformation matrix between the robot base and the camera,
    as well as the intrinsic matrix of the camera.

    Methods:
        read_json_file(file_name: str) -> dict:
            Read data from a JSON file (detection_results.json) and return it as a dictionary.

        get_home_pose(robot_ip: str) -> list:
            Get the home pose of the robot for the specified robot IP from robot_pose.json.

        get_T_cam_base(robot_ip: str) -> list:
            Get the transformation matrix between the camera_color_optical_frame and the robot base_link for the specified robot IP using tf2_ros Buffer 
            (NEEDS TO HAVE THE TF BEING PUBLISHED USING RVIZ or TF BROADCASTER).

        get_ximg(object: str, robot_ip: str) -> list:
            Get the object's pose in the image frame for the specified object and robot IP.

        get_orientation(object: str, robot_ip: str) -> list or None:
            Get the object's orientation in the robot base frame for the specified object and robot IP.

        get_length(object: str, robot_ip: str) -> list or None:
            Get the dimensions and orientation of the object in the robot base frame for the specified object and robot IP.

        Ximg2Xbase(Ximg: list, robot_ip: str) -> np.ndarray:
            Convert image coordinates to robot base coordinates using the transformation matrix and intrinsic matrix.

        _run(object: str, robot_ip: str, include_ort: bool = False) -> list:
            Convert image coordinates to robot base coordinates for a specific object and robot IP. Returns the pose in [XYZ, RPY] format.

        _arun(ximg: List[str]):
            Async version of _run, (NOT SUPPORTED).
    """

    name = "aruco_img_2_base_implementation"
    description = "get the pose of the object with respect to the robot base frame"
    args_schema: Type[BaseModel] = aruco_img_2_base_definition

    def read_json_file(self, file_name):
        """
        Read data from a JSON file and return it as a dictionary.

        Args:
            file_name (str): The path to the JSON file to be read.

        Returns:
            dict: The data read from the JSON file as a dictionary.
        """
        with open(file_name, 'r') as f:
            return json.load(f)
        
    def get_home_pose(self, robot_ip: str):
        """
        Get the home pose of the robot for the specified robot IP from JSON.

        Args:
            robot_ip (str): The IP address of the robot for which to retrieve the home pose.

        Returns:
            list: The home pose of the robot in a list format [x, y, z, roll, pitch, yaw].
        """
        try:
            robot_dict = json.loads(open(robot_home_file_path).read())
            robot_pose = robot_dict[robot_ip]["home_pose"] # Extract home pose from the JSON
            return robot_pose
        except Exception as e:
            self.return_direct = True
            print("Error getting robot home pose: "+str(e))        
    

    def get_T_cam_base(self, robot_ip: str):
        """
        Get the transformation matrix between the camera and the robot base for the specified robot IP using TF2 Buffer.

        Args:
            robot_ip (str): The IP address of the robot for which to retrieve the transformation matrix.

        Returns:
            list: The transformation matrix between the camera and the robot base in list format.
        """
        # Check if the ROS is running
        try:
            tfBuffer = tf2_ros.Buffer()
            listener = tf2_ros.TransformListener(tfBuffer)
            time.sleep(1.0)
            print("tfBuffer connection succeeded")
        except Exception as e:
            print("tfBuffer connection failed.", e)
            return
        
        while not rospy.is_shutdown():
            try:
                trans = tfBuffer.lookup_transform("base_link", "mount_color_optical_frame", rospy.Time()) # Check if transform exists
                # print(f"translation : {trans}")
            except Exception as e:
                print(f"the error is : {e}")
                continue


            q = np.array([trans.transform.rotation.x, trans.transform.rotation.y,
                        trans.transform.rotation.z, trans.transform.rotation.w])
            rot = R.from_quat(q)
            r = rot.as_matrix()
            t = np.array([trans.transform.translation.x,
                        trans.transform.translation.y, trans.transform.translation.z])
            T = np.vstack((
                np.hstack((r, t.reshape(3, 1))),
                np.array([0, 0, 0, 1.0])
            ))

            return T.tolist()


    def get_marker_pose(self,marker_id, robot_ip, file_path):
        """
        Get the marker's pose in the image frame for the specified marker ID and robot IP.

        Args:
            marker_id (str): The ID of the marker for which to retrieve the pose.
            robot_ip (str): The IP address of the robot.
            file_path (str): The path to the JSON file containing detection results.

        Returns:
            dict: The marker's pose data including center point and depth at center.
        """
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            
            if robot_ip not in data:
                raise ValueError(f"Robot IP {robot_ip} not found in data")

            detections = data[robot_ip]
            for key, value in detections.items():
                if key != 'detection_count' and value['marker_id'] == marker_id:
                    pose_data = value['cam_frame_pose']
                    marker_img = [value['center_pt'][0], value['center_pt'][1], int(value['depth_at_center'])/1000]
                    return marker_img, pose_data
                    
        except Exception as e:
            print(f"Error getting marker pose in image frame: {str(e)}")
            return None

   ###################################################################
    def get_marker_orientation_in_base(self, marker_id, robot_ip, file_path,r_matrix):
        """
        Get the marker's orientation in the base frame for the specified marker ID and robot IP.

        Args:
            marker_id (str): The ID of the marker for which to retrieve the orientation.
            robot_ip (str): The IP address of the robot.
            file_path (str): The path to the JSON file containing detection results.

        Returns:
            list: The marker's orientation in the base frame as [roll, pitch, yaw].
        """
        # Read the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        if robot_ip not in data:
            raise ValueError(f"Robot IP {robot_ip} not found in data")
        
        detections = data[robot_ip]
        orientation_cam_frame = None
        
        # Find the marker and get the orientation in the camera frame
        for key, value in detections.items():
            if key != 'detection_count' and value['marker_id'] == str(marker_id):
                orientation_cam_frame = value['cam_frame_pose'][-3:]  # Last three values are the orientation
        
        if orientation_cam_frame is None:
            raise ValueError(f"Marker ID {marker_id} not found for robot IP {robot_ip}")
        
        # Get the transformation matrix from the camera frame to the base frame
        R_cam_base = r_matrix
        rot_cam_matrix = cv2.Rodrigues(np.array(orientation_cam_frame[0]))[0]
        rot_base_matrix = R_cam_base @ rot_cam_matrix
        r = R.from_matrix(rot_base_matrix)
        roll, pitch, yaw = r.as_euler('xyz', degrees=False)
        # roll = orientation_cam_frame[0]
        # pitch = orientation_cam_frame[1]
        # yaw = orientation_cam_frame[2]
        # Return the orientation in the base frame
        return [roll, pitch, yaw]

    
            
 
    def aruco_img_2_base(self, Ximg, robot_ip: str)-> np.ndarray:
        """
        Convert image coordinates to robot base coordinates using the transformation matrix and intrinsic matrix.

        Args:
            aruco_img (list): Image coordinates [Ximg_x, Ximg_y, Ximg_depth/1000].
            robot_ip (str): The IP address of the robot.

        Returns:
            np.ndarray: The converted coordinates in the robot base frame as [Xbase_x, Xbase_y, Xbase_z].
        """
        try:
            T_cam_base = self.get_T_cam_base(robot_ip)
            Z = Ximg[2]
            Ximg = np.array([Ximg[0], Ximg[1], 1.0])
            Xcam = Z * np.linalg.inv(inst_matrix) @ Ximg
            Xbase = T_cam_base @ np.array([Xcam[0], Xcam[1], Xcam[2], 1.0])
    
            return Xbase[:3]
        except Exception as e:
            self.return_direct = True
            print("Error converting image coordinates to robot base: "+str(e))
    
    def _run(self, marker_id: str, robot_ip: str,include_ort: bool = False):
        """
        Convert image coordinates to robot base coordinates for a specific object and robot IP.

        This method performs the coordinate conversion from image frame (Ximg) to robot base frame (Xbase)
        for a specified object. It includes an option to consider object orientation in the result.

        Args:
            object (str): The name of the object for which to perform the coordinate conversion.
            robot_ip (str): The IP address of the robot.
            include_ort (bool): Whether to include object orientation in the result (default: False).
        
        Conditions: 
            Usage of tcp_offsets is only when we are usinf Z compliant gripper. For other grippers we need to 
            change the offset values based on physical dimensions of it. Eventually this will be solved in URDF 
            section but for time being these things need to be rechecked.
            
        Returns:
            list or None: A list of converted coordinates in the robot base frame, or None if an error occurs.
        """
        try:
            print("started")
            Ximg, cam_pose = self.get_marker_pose(marker_id, robot_ip,marker_data)
            print(Ximg)
            Xbase = self.aruco_img_2_base(Ximg, robot_ip)
            print(Xbase)
            R_cam_base = np.array(self.get_T_cam_base(robot_ip))[:3,:3]
            offset =  np.round(R_cam_base) @ np.array([-0.05, 0.0, -0.04])
            Xbase += offset[:3]
            print("running orientation")
            # orientation = self.get_marker_orientation_in_base(marker_id,robot_ip,marker_data,R_cam_base)
            # print(orientation)
            #tcp offsets are the dimensions of the Z-complaint gripper's dimensions
            tcp_offset_z = 0.17 # Height of gripper spring
            tcp_offset_y = 0.15
            # Xbase[2] = Xbase[2] + tcp_offset_z
            Xbase[1] = Xbase[1] + tcp_offset_y
            
            # Xbase = [Xbase[0], Xbase[1], Xbase[2], orientation[0], orientation[1], orientation[2]] 
            Xbase = [Xbase[0], Xbase[1], Xbase[2]]

            return Xbase
        
        except Exception as e:
            self.return_direct = True
            print("ximg2xbase error : "+str(e))

    def _arun(self,  ximg: List[str]):
        raise NotImplementedError("ximg2xbase_implementation does not support async")    
    
