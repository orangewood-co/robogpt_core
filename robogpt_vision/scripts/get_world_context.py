import json
import os
import sys
import time
import rospy
import tf2_ros
import numpy as np
from typing import Type, List
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from scipy.spatial.transform import Rotation as R
from tf.transformations import euler_matrix,euler_from_matrix

robot_home_file_path = os.path.join(os.getcwd(),"config/robot_pose.json")

inst_matrix = np.array([[909.134765625,  0, 654.532836914062 ],
                        [  0,908.667419433594, 372.789794921875],
                        [  0, 0, 1       ]])

global depth

class ximg2xbase_definition(BaseModel):
    object: str = Field(description="object's name")
    robot_ip: str = Field(description="ip address of the robot")
    include_ort: bool = Field(default=False,description="if the object orientation needs to considered")

class ximg2xbase_implementation(BaseTool):
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

    name = "ximg2xbase_implementation"
    description = "get the pose of the object with respect to the robot base frame"
    args_schema: Type[BaseModel] = ximg2xbase_definition

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
            robot_pose = robot_dict[robot_ip]["home"] # Extract home pose from the JSON
            return robot_pose
        except Exception as e:
            self.return_direct = True
            print("Error getting robot home pose: "+str(e))        
    

    def get_T_base_cam(self,robot_ip: str):
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
                trans = tfBuffer.lookup_transform("top_color_optical_frame", "base_link", rospy.Time()) # Check if transform exists
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
                trans = tfBuffer.lookup_transform("base_link", "top_color_optical_frame", rospy.Time()) # Check if transform exists
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

    def get_ximg(self, object: str, robot_ip: str):
        global depth
        """
        Get the object's pose in the image frame for the specified object and robot IP.

        Args:
            object (str): The name of the object for which to retrieve the pose.
            robot_ip (str): The IP address of the robot.

        Returns:
            list: The object's pose in the image frame as [Ximg_x, Ximg_y, Ximg_depth].
        """        
        try:
            data = self.read_json_file(os.path.join(os.getcwd(),"config/detection_results.json"))        
            dets = data[robot_ip]

            for k, v in dets.items():
                if v['detected_object'] in object:
                    object_Ximg = [v['center_pt'][0], v['center_pt'][1], v['depth_at_center'] / 1000.0]
                    print(f"Object depth at centre (img frame) {v['depth_at_center'] / 1000.0}")
                    depth = v['depth_at_center'] / 1000.0
                    return object_Ximg
                
        except Exception as e:
            self.return_direct = True
            print("Error getting object pose in image frame: "+str(e))
            
    def get_orientation(self,object: str, robot_ip: str):
        """
        Get the object's orientation in the robot base frame for the specified object and robot IP.

        Args:
            object (str): The name of the object for which to retrieve the orientation.
            robot_ip (str): The IP address of the robot.

        Returns:
            list or None: The object's orientation in the robot base frame as [roll, pitch, yaw], or None if not found.
        """
        
        data = self.read_json_file(os.path.join(os.getcwd(),"config/detection_results.json"))
        if robot_ip not in data:
            return None
        
        dets = data[robot_ip]

        for k, v in dets.items():
            if v['detected_object'] in object:
                rotation_matrix = euler_matrix(*v["orientation"],axes="sxyz")
                T_cam_base = np.round(np.array(self.get_T_cam_base(robot_ip))[:3,:3])
                ort_base = euler_from_matrix(T_cam_base @ rotation_matrix)
                return ort_base
            
    def get_length(self, object: str, robot_ip: str):
        """
        Get the dimensions and orientation of the object in the robot base frame for the specified object and robot IP.

        Args:
            object (str): The name of the object for which to retrieve the dimensions and orientation.
            robot_ip (str): The IP address of the robot.

        Returns:
            list or None: The object's dimensions in the robot base frame as [length, width, height, orientation],
            or None if not found.
        """
        print("in get_ximg")
        
        data = self.read_json_file(os.path.join(os.getcwd(),"config/detection_results.json"))
        if robot_ip not in data:
            return None
        
        dets = data[robot_ip]

        for k, v in dets.items():
            if v['detected_object'] in object:
                dimension = v['dimension']
                rotation_matrix = euler_matrix(*v["orientation"],axes="sxyz")
                T_cam_base = np.round(np.array(self.get_T_cam_base(robot_ip))[:3,:3])
                dim_base = T_cam_base @ np.array([dimension[0], dimension[1], dimension[2]])
                print(rotation_matrix)
                print(T_cam_base)
                # ort_base = quaternion_from_matrix(T_cam_base @ rotation_matrix)
                ort_base = [0,0,0,1]
                return np.abs(dim_base[:3]),ort_base

    def Ximg2Xbase(self, Ximg, robot_ip: str)->np.ndarray:
        """
        Convert image coordinates to robot base coordinates using the transformation matrix and intrinsic matrix.

        Args:
            Ximg (list): Image coordinates [Ximg_x, Ximg_y, Ximg_depth/1000].
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
    
    def _run(self, object: str, robot_ip: str,include_ort: bool = False):
        global depth
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
            Ximg = self.get_ximg(object, robot_ip)
            Xbase = self.Ximg2Xbase(Ximg, robot_ip)
            T_cam_base = np.round(np.array(self.get_T_cam_base(robot_ip))[:3,:3])
            offset = T_cam_base @ np.array([-0.05, 0.0, -0.04])
            Xbase += offset[:3]
            home_pose = self.get_home_pose(robot_ip)
            orientation = home_pose[3:]
            #tcp offsets are the dimensions of the Z-complaint gripper's dimensions
            tcp_offset_z = 0.17 # Height of gripper spring
            tcp_offset_y = 0.15
            # Xbase[2] = Xbase[2] + tcp_offset_z
            Xbase[1] = Xbase[1] + tcp_offset_y
            

            Xbase = [Xbase[0], Xbase[1], Xbase[2], orientation[0], orientation[1], orientation[2]] 
            return Xbase
        
        except Exception as e:
            self.return_direct = True
            print("ximg2xbase error : "+str(e))

    def _arun(self,  ximg: List[str]):
        raise NotImplementedError("ximg2xbase_implementation does not support async") 