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
from tf.transformations import euler_matrix,euler_from_matrix
from robogpt_vision.srv import GetWorldContext, GetWorldContextResponse


inst_matrix = np.array([[607.379638671875, 0.0, 323.45916748046875],
                        [  0.0, 607.0968627929688, 245.50621032714844],
                        [  0, 0, 1.0]])
                        
##############################################################################

global depth
rospack = rospkg.RosPack()
vision_path = rospack.get_path('robogpt_vision') 
agent_path = rospack.get_path('robogpt_agents') 
detection_results_path = os.path.join(vision_path,"config/detection_results.json")
poses_path = os.path.join(agent_path,"config/robot_config/robot_pose.json")

###############################################################################

class ximg2xbase_implementation():
    """
    Convert image frame coordinates to robot base frame coordinates for a specific object.

    This class provides functionality to convert image coordinates (Ximg) to robot base coordinates (Xbase)
    for a specified object. It takes into account the transformation matrix between the robot base and the camera,
    as well as the intrinsic matrix of the camera.

    Methods:
        read_json_file(file_name: str) -> dict:
            Read data from a JSON file (detection_results.json) and return it as a dictionary.

        get_home_pose() -> list:
            Get the home pose of the robot for the specified robot IP from robot_pose.json.

        get_T_cam_base() -> list:
            Get the transformation matrix between the camera_color_optical_frame and the robot base_link for the specified robot IP using tf2_ros Buffer 
            (NEEDS TO HAVE THE TF BEING PUBLISHED USING RVIZ or TF BROADCASTER).

        get_ximg(object: str) -> list:
            Get the object's pose in the image frame for the specified object and robot IP.

        get_orientation(object: str) -> list or None:
            Get the object's orientation in the robot base frame for the specified object and robot IP.

        get_length(object: str) -> list or None:
            Get the dimensions and orientation of the object in the robot base frame for the specified object and robot IP.

        Ximg2Xbase(Ximg: list) -> np.ndarray:
            Convert image coordinates to robot base coordinates using the transformation matrix and intrinsic matrix.

        _run(object: str, include_ort: bool = False) -> list:
            Convert image coordinates to robot base coordinates for a specific object and robot IP. Returns the pose in [XYZ, RPY] format.

        _arun(ximg: List[str]):
            Async version of _run, (NOT SUPPORTED).
    """

    def __init__(self):
        rospy.init_node('get_world_context_service')
        service = rospy.Service('get_world_context', GetWorldContext, self._run)
        rospy.loginfo("Service 'get_world_context' is ready")
        self.robot_name = rospy.get_param("/robot_model",default="sim")
    
    def get_package_path(self, package_name):
        # Create an instance of the rospkg.RosPack class
        rospack = rospkg.RosPack()

        try:
            # Get the path of the package
            package_path = rospack.get_path(package_name)
            return package_path
        except rospkg.ResourceNotFound:
            print(f"Package '{package_name}' not found!")
            return None

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
        
    def get_orientation_assumption(self):
        """
        Get the home pose of the robot for the specified robot IP from JSON.

        Returns:
            list: The home pose of the robot in a list format [x, y, z, roll, pitch, yaw].
        """
        try:
            robogpt_vision_path = self.get_package_path('robogpt_vision')
            robot_dict = json.loads(open(poses_path).read())
            robot_dict = robot_dict[self.robot_name]
            robot_pose = robot_dict["orient"] # Extract home pose from the JSON
            return robot_pose
        except Exception as e:
            self.return_direct = True
            print("Error getting robot home pose: "+str(e))        
    

    def get_T_base_cam(self, parent_frame: str,camera_name: str):
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
                cam_frame = f"{camera_name}_color_optical_frame"
                trans = tfBuffer.lookup_transform(cam_frame, parent_frame, rospy.Time()) # Check if transform exists
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
    

    def get_T_cam_base(self, parent_frame: str,camera_name: str):
        """
        Get the transformation matrix between the camera and the robot base for the specified robot IP using TF2 Buffer.

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
                cam_frame = f"{camera_name}_color_optical_frame"
                trans = tfBuffer.lookup_transform(parent_frame, cam_frame, rospy.Time()) # Check if transform exists
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

    def get_ximg(self, object_name: str, camera_name: str):
        global depth
        """
        Get the object's pose in the image frame for the specified object and robot IP.

        Args:
            object (str): The name of the object for which to retrieve the pose.
        
        Returns:
            list: The object's pose in the image frame as [Ximg_x, Ximg_y, Ximg_depth].
        """        
        try:
            robogpt_vision_path = self.get_package_path('robogpt_vision')
            data = self.read_json_file(detection_results_path)
            data = data[camera_name]

            for k, v in data.items():
                if v['detected_object'] in object_name:
                    object_Ximg = [v['center_pt'][0], v['center_pt'][1], v['depth_at_center'] / 1000.0]
                    print(f"Object depth at centre (img frame) {v['depth_at_center'] / 1000.0}")
                    depth = v['depth_at_center'] / 1000.0
                    return object_Ximg
                
        except Exception as e:
            self.return_direct = True
            print("Error getting object pose in image frame: "+str(e))
            
    def get_orientation(self, object_name: str, parent_frame: str,camera_name: str):
        """
        Get the object's orientation in the robot base frame for the specified object and robot IP.

        Args:
            object (str): The name of the object for which to retrieve the orientation.

        Returns:
            list or None: The object's orientation in the robot base frame as [roll, pitch, yaw], or None if not found.
        """
        robogpt_vision_path = self.get_package_path('robogpt_vision')
        data = self.read_json_file(os.path.join(robogpt_vision_path,"config/detection_results.json"))
        data = data[camera_name]

        for k, v in data.items():
            if v['detected_object'] in object_name:
                rotation_matrix = euler_matrix(*v["orientation"],axes="sxyz")
                T_cam_base = np.round(np.array(self.get_T_cam_base(parent_frame))[:3,:3])
                ort_base = euler_from_matrix(T_cam_base @ rotation_matrix)
                return ort_base
            
    def get_length(self, object_name: str, parent_frame: str, camera_name: str):
        """
        Get the dimensions and orientation of the object in the robot base frame for the specified object and robot IP.

        Args:
            object (str): The name of the object for which to retrieve the dimensions and orientation.

        Returns:
            list or None: The object's dimensions in the robot base frame as [length, width, height, orientation],
            or None if not found.
        """
        print("in get_ximg")
        
        robogpt_vision_path = self.get_package_path('robogpt_vision')
        data = self.read_json_file(os.path.join(robogpt_vision_path,"config/detection_results.json"))
        data = data[camera_name]

        for k, v in data.items():
            if v['detected_object'] in object_name:
                dimension = v['dimension']
                rotation_matrix = euler_matrix(*v["orientation"],axes="sxyz")
                T_cam_base = np.round(np.array(self.get_T_cam_base(parent_frame))[:3,:3])
                dim_base = T_cam_base @ np.array([dimension[0], dimension[1], dimension[2]])
                print(rotation_matrix)
                print(T_cam_base)
                # ort_base = quaternion_from_matrix(T_cam_base @ rotation_matrix)
                ort_base = [0,0,0,1]
                return np.abs(dim_base[:3]),ort_base

    def Ximg2Xbase(self, Ximg, parent_frame: str,camera_name)->np.ndarray:
        """
        Convert image coordinates to robot base coordinates using the transformation matrix and intrinsic matrix.

        Args:
            Ximg (list): Image coordinates [Ximg_x, Ximg_y, Ximg_depth/1000].

        Returns:
            np.ndarray: The converted coordinates in the robot base frame as [Xbase_x, Xbase_y, Xbase_z].
        """
        try:
            T_cam_base = self.get_T_cam_base(parent_frame,camera_name)
            Z = Ximg[2]
            Ximg = np.array([Ximg[0], Ximg[1], 1.0])
            Xcam = Z * np.linalg.inv(inst_matrix) @ Ximg
            Xbase = T_cam_base @ np.array([Xcam[0], Xcam[1], Xcam[2], 1.0])
            return Xbase[:3]
        except Exception as e:
            self.return_direct = True
            print("Error converting image coordinates to robot base: "+str(e))
    

    def _run(self, req):
        global depth
        """
        Convert image coordinates to robot base coordinates for a specific object and robot IP.

        This method performs the coordinate conversion from image frame (Ximg) to robot base frame (Xbase)
        for a specified object. It includes an option to consider object orientation in the result.

        Args:
            object (str): The name of the object for which to perform the coordinate conversion.
            include_ort (bool): Whether to include object orientation in the result (default: False).
        
        Conditions: 
            Usage of tcp_offsets is only when we are usinf Z compliant gripper. For other grippers we need to 
            change the offset values based on physical dimensions of it. Eventually this will be solved in URDF 
            section but for time being these things need to be rechecked.
            
        Returns:
            list or None: A list of converted coordinates in the robot base frame, or None if an error occurs.
        """
        try:
            rospy.loginfo(f"Current robot in use {self.robot_name}")
            object_name = req.object_name
            parent_frame = req.parent_frame
            camera_name = req.camera_name
            include_ort = req.include_ort if hasattr(req, 'include_ort') else False
            Ximg = self.get_ximg(object_name,camera_name)
            Xbase = self.Ximg2Xbase(Ximg, parent_frame,camera_name)
            T_cam_base = np.round(np.array(self.get_T_cam_base(parent_frame,camera_name))[:3,:3])
            # offset = T_cam_base @ np.array([-0.05, 0.0, -0.04])
            # Xbase += offset[:3]
            orientation_assumption = self.get_orientation_assumption()
            orientation = orientation_assumption[3:]
            Xbase[2] = Xbase[2] + 0.12
            Xbase = [Xbase[0], Xbase[1], Xbase[2], orientation[0], orientation[1], orientation[2]] 
            return GetWorldContextResponse(Xbase=Xbase)
        
        except Exception as e:
            self.return_direct = True
            print("ximg2xbase error : "+str(e))

    def _arun(self,  ximg: List[str]):
        raise NotImplementedError("ximg2xbase_implementation does not support async") 


if __name__ == "__main__":
    try:
        # Instantiate the service class
        service_instance = ximg2xbase_implementation()
        
        # Keep the node running
        rospy.spin()
    except rospy.ROSInterruptException:
        pass