import spacy  # type: ignore
import random
import numpy as np
import time
import math
import subprocess
import zipfile
import sys, os
import json
import rospy
import moveit_commander
import tf2_ros
import logging
import datetime
import tf2_geometry_msgs
import geometry_msgs.msg
import pusher  
import importlib
import open3d as o3d
from difflib import SequenceMatcher
from robogpt_v3.robogpt_agents.scripts.basic_tools.utils import *
from geometry_msgs.msg import Pose
from multiprocessing import Process
from multiprocessing import Queue
from owl_client import OwlClient, Joint
from owl_client import Pose as OwlPose
from langchain.tools import BaseTool
from typing import Type, List, Dict
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive
from pydantic import BaseModel, Field
from tf.transformations import quaternion_from_euler, quaternion_matrix, translation_matrix, euler_matrix, euler_from_matrix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# -----------------------------------------------------------------------------
#                         INITIALIZERS
# -----------------------------------------------------------------------------

# Load the spaCy NLP model 
nlp = spacy.load("en_core_web_md")

# Define file paths for configuration and results

robot_home_file_path = "robogpt_v3/robogpt_config/robot_config/robot_pose.json"
robotgpt_config = "robogpt_v3/robogpt_config/robot_config/robogpt.json"
tool_path = "robogpt_v3/robogpt_config/tools_config/tool_list.json"

# -----------------------------------------------------------------------------
# Loading the robot wrappers

robot_model = rospy.get_param('/robot_model', default="")
robot_model = "sim"
try:
    wrapper_path = f'/robot_drivers/{robot_model}/wrapper'
    bot_control = importlib.import_module(wrapper_path)

except Exception as err:
    print("Could not load robot due to ",err)
    send_msg(message="Error in  loading Robot. Please check the Robot Model")

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
#               SECONDARY FEATURE SKILLS/FUNCTIONS
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
#        GENERAL HELPER FUNCTIONS RELATED TO ROBOT
# -----------------------------------------------------------------------------

# Data model for the 'set_robot_ip' tool
class robot_connection_definition(BaseModel):
    robot_ip_list: List[str] = Field(description="list of IP addresses of the robots to be controlled...")

# Implementation of the 'set_robot_ip' tool
class robot_connection_implementation(BaseTool):
    name = "set_robot_ip"        
    description = "sets the IP address of the robot"
    args_schema: Type[BaseModel] = robot_connection_definition

    def _run(self, robot_ip_list: List[str]) -> None:
        print("Connected to the robot")
        send_msg("I am connected to the robot")
        ROBOT_IP_LIST = robot_ip_list
        
    def _arun(self, robot_ip_list: List[str]):
        return("set_robot_ip_implementation does not support async")

# Data model for the 'get_joint' tool
class get_joint_definition(BaseModel):
    robot_to_use: int = Field(default=1, description="the robot number to use. robot 1 will be the first IP address in the list, robot 2 will be the second IP address in the list and so on.")
    wait: bool = Field(default=True, description="True will allow to return the latest data received from the robot.")

# Implementation of the 'get_joint' tool
class get_joint_implementation(BaseTool):
    """Tool for retrieving joint values of the robot in radians"""
    name = "get_joint"
    description = "returns the current joint values of the robot"
    args_schema: Type[BaseModel] = get_joint_definition

    def _run(self, robot_to_use: int, wait: bool = True) -> list:
        try:
            curr_joint_rads = bot_control.get_joint()
            return curr_joint_rads
        
        except Exception as e:
            self.return_direct = True
            robot_logger.error("get_joint_implementation failed " + str(e))
            return None

    def _arun(self, robot_to_use: int, wait: bool = True):
        return("get_joint does not support async")

# Data model for the 'get_pose' tool
class get_pose_definition(BaseModel):
    robot_to_use: int = Field(default=1, description="the robot number to use. robot 1 will be the first IP address in the list, robot 2 will be the second IP address in the list and so on.")
    wait: bool = Field(default=True, description="True will allow to return the latest data received from the robot.")

# Implementation of the 'get_pose' tool
class get_pose_implementation(BaseTool):
    """Tool for retrieving end effector pose in meters"""
    name = "get_pose"
    description = "returns the current pose of robot end effector"
    args_schema: Type[BaseModel] = get_pose_definition

    def _run(self, robot_to_use: int, wait: bool = True) -> list:
        print("get_pose_implementation")
        try:
            curr_pose = robots[robot_to_use - 1].get_tcp().get_pose()
            return curr_pose
        except Exception as e:
            self.return_direct = True
            robot_logger.error("get_pose_implementation failed " + str(e))
            return None

    def _arun(self, robot_to_use: int, wait: bool = True):
        return("get_joint does not support async")

# Data model for the 'get_zone_pose' tool
class get_zone_pose_definition(BaseModel):
    robot_ip: str = Field(description="IP address of the robot")
    zone_name: str = Field(description="Target pose name where the robot needs to move.")

# Implementation of the 'get_zone_pose' tool
class get_zone_pose_implementation(BaseTool):
    """Tool to get the robot pose at a specific zone"""
    name = "get_zone_pose"
    description = "requests the pose of the robot at a particular zone"
    args_schema: Type[BaseModel] = get_zone_pose_definition

    def _run(self, robot_ip: str, zone_name: str) -> list:

        # Helper function to find the best matching zone name
        def get_best_zone_match(zone_name, robot_dict):
            print("1")

            best_match = None
            best_ratio = 0
            for obj in robot_dict.keys():
                ratio = SequenceMatcher(None, zone_name, obj).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = obj
            print("2")

            return best_match
        
        robot_dict = json.loads(open(robot_home_file_path).read())
        
        try:
            robot_pose = robot_dict[robot_ip]
            zone_match = get_best_zone_match(zone_name, robot_pose)

            return robot_pose[zone_match]
        except Exception as e:
            self.return_direct = True
            print("exception 1")
            robot_logger.error("get_zone_pose_implementation failed " + str(e))
            return None

            
    def _arun(self, robot_ip: str, zone_name: str):
        print("move_to_pose does not support async")

# -----------------------------------------------------------------------------
#                       ROBOT TOOL CONTROL
# -----------------------------------------------------------------------------

# Data model for the 'hand_teach' tool
class hand_teach_definition(BaseModel):
    robot_to_use: int = Field(default=1, description="the robot number to use. robot 1 will be the first IP address in the list, robot 2 will be the second IP address in the list and so on.")
    config: bool = Field(default=False, description="The boolean which decides the robot is in gravity or hand teach mode or not. true puts the robot in hand teach and false switches the gravity /hand teach off")

# Implementation of the 'hand_teach' tool
class hand_teach_implementation(BaseTool):
    '''Tool to put robot in hand teach mode'''
    name = "hand_teach_init"
    description = "It switches the hand teach/gravity mode on or off based on the config bool value"
    args_schema: Type[BaseModel] = hand_teach_definition

    def _run(self, robot_to_use: int = 1, config: bool = False):
        try:
            if config:
                # OwlClient("10.42.0.53").enter_teach_mode()
                response = robots[robot_to_use - 1].enter_teach_mode()
                return response

            if not config:
                # OwlClient("10.42.0.53").end_teach_mode()
                response = robots[robot_to_use - 1].end_teach_mode()
                return response
        except Exception as e:
            print("Robot is unable to switch in Hand teach")

# Data model for the 'control_gripper' tool
class control_gripper_definition(BaseModel):
    '''True to activate or open the gripper and False to deactivate or close the gripper.'''
    switch: bool = Field(description="True to activate or close the gripper and False to deactivate or open the gripper.")
    robot_to_use: int = Field(default=1, description="the robot number to use. robot 1 will be the first IP address in the list, robot 2 will be the second IP address in the list and so on.")
    model: str = Field(default="robotiq", description="the gripper model robot is using for applications")

# Implementation of the 'control_gripper' tool
class control_gripper_implementation(BaseTool):
    """Tool to activate/deactivate the gripper."""
    name = "control_gripper"
    description = "Activates/Deactivates the gripper."
    args_schema: Type[BaseModel] = control_gripper_definition

    def _run(self, switch: bool = True, robot_to_use: int = 1, model: str = "robotiq") -> None:
        print("control_gripper_implementation")
        
        ''' This method for robotiq gripper is a test method but 
            not the right way to control robotiq gripper. Till the robotiq package
            is integrated we will be using this
            Here True closes the gripper and False will open the gripper'''
        
        if model == "robotiq":
            command_close = "rosservice call /robotiq/gripper/close"
            command_source = "source ~/workspace/robogpt/robogpt_ws/devel/setup.bash"
            command_open = "rosservice call /robotiq/gripper/open"
            os.system(command=command_source)

            if switch:
                response = os.system(command=command_close)
            elif not switch:
                response = os.system(command=command_open)
            else:
                pass
        else:
            response = robots[robot_to_use - 1].set_digital_output(3, switch)

        return response
    
    def _arun(self, switch: bool):
        print("activate_gripper does not support async")

# -----------------------------------------------------------------------------
#                      MISC
# -----------------------------------------------------------------------------

# Data model for the 'delay' tool
class delay_definition(BaseModel):
    delay: float = Field(description="Delay in seconds.")

# Implementation of the 'delay' tool
class delay_implementation(BaseTool):
    """Tool to add delay in the script."""
    name = "delay"
    description = "Adds delay in the script."
    args_schema: Type[BaseModel] = delay_definition

    def _run(self, delay: float):
        print("delay_implementation")
        time.sleep(delay)
        return ("added delay for " + str(delay) + " seconds")
    
    def _arun(self, delay: float):
        time.sleep(delay)
        return ("added delay for " + str(delay) + " seconds")
    
# -----------------------------------------------------------------------------
#                   ROBOT AND MOVEIT CONTROL
# -----------------------------------------------------------------------------

# Data model for the 'move_translate' tool
class move_translate_definition(BaseModel):
    robot_to_use: int = Field(default=1, description="the robot number to use. robot 1 will be the first IP address in the list, robot 2 will be the second IP address in the list and so on.")
    x: float = Field(default=0.0, description="the distance in m to which robot needs to translate in x axis")
    y: float = Field(default=0.0, description="the distance in m to which robot needs to translate in y axis")
    z: float = Field(default=0.0, description="the distance in m to which robot needs to translate in z axis")
    toolspeed: int = Field(default=100, description="the speed of robot when it executes the translation")

# Implementation of the 'move_translate' tool
class move_translate_implementation(BaseTool):
    '''Tool to translate the robot in a particular plane or axis'''
    name = "move_translate"
    description = "Tool to translate or move the robot in a particular plane or axis"
    args_schema: Type[BaseModel] = move_translate_definition

    def _run(self, robot_to_use: int = 1, x: float = 0.0, y: float = 0.0, z: float = 0.0, toolspeed: int = 100):
        try:
            response = robots[robot_to_use - 1].move_translate(x, y, z, toolspeed)
            robot_logger.info("Move Translate SUCCEEDED")
            return 
        except Exception as e:
            self.return_direct = True
            robot_logger.error("Move Translate FAILED " + str(e))

# Data model for the 'transform_ee_to_tcp' tool
class transform_ee_to_tcp_definition(BaseModel):
    goal_pose: List[float] = Field(description="Goal pose robot end effector need to achieve.")
    wait: bool = Field(default=True, description="True will make the move call synchronous and wait till move is completed.")
    robot_to_use: int = Field(default=1, description="the robot number to use. robot 1 will be the first IP address in the list, robot 2 will be the second IP address in the list and so on.")

# Implementation of the 'transform_ee_to_tcp' tool
class transform_ee_to_tcp_implementation(BaseTool):
    """Tool to transform the goal pose from end effector frame to tcp frame"""
    name = "transform_ee_to_tcp"
    description = "transforms the goal pose from end effector frame to tcp frame for planning in moveit."
    args_schema: Type[BaseModel] = transform_ee_to_tcp_definition

    def _run(self, goal_pose: List[float], robot_to_use: int = 1, wait: bool = True) -> list:

        tranformation_matrix = get_transform_implementation().get_transform("tcp_ee", "tcp")
        rt_tcp = euler_matrix(goal_pose[3], goal_pose[4], goal_pose[5], "sxyz")
        tm_tcp = translation_matrix((goal_pose[0], goal_pose[1], goal_pose[2])) @ rt_tcp
        goal_pose_tcp = tm_tcp @ tranformation_matrix
        euler_goal = euler_from_matrix(goal_pose_tcp)
        goal = [goal_pose_tcp[0, -1], goal_pose_tcp[1, -1], goal_pose_tcp[2, -1], euler_goal[0], euler_goal[1], euler_goal[2]]

        return goal

# Data model for the 'move_to_joint' tool
class move_to_joint_definition(BaseModel):
    jointPose: List[float] = Field(description="Goal joint in radians robot needs to achieve. It is in the format [base, shoulder, elbow, wrist1, wrist2, wrist3] or [joint1, joint2, joint3, joint4, joint5, joint6]")
    wait: bool = Field(default=True, description="True will make the move call synchronous and wait till move is completed.")
    robot_to_use: int = Field(default=1, description="the robot number to use. robot 1 will be the first IP address in the list, robot 2 will be the second IP address in the list and so on.")
    relative: bool = Field(default=False, description="Move relative to the current robot joint. It will move the joints by the amount specified in jointPose from the current joint position.")

# Implementation of the 'move_to_joint' tool
class move_to_joint_implementation(BaseTool):
    """Tool to move the robot to a specific joint pose"""
    name = "move_to_joint"
    description = "requests the robot server to move to a specific joint pose."
    args_schema: Type[BaseModel] = move_to_joint_definition

    def _run(self, jointPose: List[float], robot_to_use: int = 1, wait: bool = True, relative: bool = False) -> None:
        try:
            joint_goal = Joint(*jointPose)
            response = robots[robot_to_use - 1].move_to_joint(joint_goal, 400, wait, relative)
            robot_logger.info("Motion planning SUCCEEDED")
        except Exception as e:
            self.return_direct = True
            robot_logger.error("Motion planning FAILED " + str(e))

# Data model for the 'move_to_pose' tool
class move_to_pose_definition(BaseModel):
    goal_pose: List[float] = Field(description="Goal pose robot need to achieve")
    robot_to_use: int = Field(default=1, description="the robot number to use. robot 1 will be the first IP address in the list, robot 2 will be the second IP address in the list and so on.")
    use_moveit: bool = Field(default=False, description="the boolean which checks if robot has to use moveit or not")

# Implementation of the 'move_to_pose' tool
class move_to_pose_implementation(BaseTool):
    """Tool to move the robot to a specific pose"""
    name = "move_to_pose"
    description = "requests the robot server to move to a specific pose"
    args_schema: Type[BaseModel] = move_to_pose_definition

    def _run(self, goal_pose: List[float], wait: bool = True, robot_to_use: int = 1, use_moveit: bool = False) -> None:
        f = open(robotgpt_config)
        robogpt_data = json.load(f)
        velcoity_scale = robogpt_data["velocity_scaling"]
        f.close()

        if use_moveit:
            waypoints = []
            waypoints.append(goalPose)
        else:
            try:
                goalPose = OwlPose(*goal_pose)
                response = robots[robot_to_use - 1].move_to_pose(goalPose, velcoity_scale * 1000, wait=wait)
                robot_logger.info(f"Motion planning SUCCEEDED : goal pose - {goal_pose}, velocity scaling factor - {velcoity_scale}")
            except Exception as e:
                self.return_direct = True
                robot_logger.error("Motion planning FAILED " + str(e))

# Data model for the 'move_in_trajactory' tool
class move_in_trajactory_definition(BaseModel):
    waypoints: List[list] = Field(description="list of the waypoints through which robot needs to make a trajactory")
    robot_to_use: int = Field(default=1, description="the robot number to use. robot 1 will be the first IP address in the list, robot 2 will be the second IP address in the list and so on.")

# Implementation of the 'move_in_trajactory' tool
class move_in_trajactory_implementation(BaseTool):
    "tool to run robot in a trajactory"
    name = "move_in_trajactroy"
    description = "the tool to run robot in a particular trajactory"
    args_schema: Type[BaseModel] = move_in_trajactory_definition

    def _run(self, waypoints: List[list]):
        try:
            robot_logger.info(f"Motion planning SUCCEEDED")

        except Exception as e:
            robot_logger.error("Motion planning FAILED " + str(e))

# Data model for the 'zone_selection' tool
class zone_selection_definition(BaseModel):
    robot_ip: str = Field(description="IP address of the robots to be controlled...")
    zone_name: str = Field(description="Target pose name where the robot needs to move.")
    zone_pose: List[float] = Field(default=None, description="Target pose of the robot at the zone")
    use_pointcloud: bool = Field(default=False, description="True to use pointcloud to select zone pose")

# Implementation of the 'zone_selection' tool
class zone_selection_implementation(BaseTool):
    """Tool to add zones in the robot environment"""
    name = "zone_selection"
    description = "adds zones in the robot environment base on user selection"
    args_schema: Type[BaseModel] = zone_selection_definition

    def _run(self, robot_ip: str, zone_name: str, zone_pose: List[float] = None, use_pointcloud: bool = False) -> None:
        
        robot_dict = json.loads(open(robot_home_file_path).read())
        if robot_ip not in robot_dict:
            robot_dict[robot_ip] = {}
        if use_pointcloud:
            zone_pose = self.get_pointcloud_pose()

        robot_dict[robot_ip][zone_name] = zone_pose
        print("zone pose:::::", zone_pose)

        try:
            with open(f"{robot_home_file_path}", 'w') as f:
                json.dump(robot_dict, f)
        except Exception as e:
            self.return_direct = True
            robot_logger.error("write to file failed - setting home pose " + str(e))

    # Helper function to get the zone pose from a pointcloud
    def get_pointcloud_pose(self):
        point_cloud = o3d.io.read_point_cloud("/home/ow-labs/workspaces/robotgpt_6_5/owl_robotgpt/ros_ws/src/utils/final_map.ply")

        # Create an empty list to store selected points
        vis = o3d.visualization.VisualizerWithEditing()
        vis.create_window()
        vis.add_geometry(point_cloud)
        vis.run()
        x = vis.get_picked_points()  # [84, 119, 69]
        points = np.asarray(point_cloud.points)
        return np.average(points[[x]].reshape(-1, 3), axis=0)

# Data model for the 'pick_n_place' tool
class pick_n_place_definition(BaseModel):
    pick_pose: list = Field(description="the pose from where the robot needs to pick")
    int_bf: list = Field(default=None, description="the list of coordinates where robot needs to go before reaching pick pose")
    drop_pose: list = Field(description="the position of where robot needs to drop the object")
    int_af: list = Field(default=None, description="The intermediate poses where robot needs to go after picking object and before going to drop")

# Implementation of the 'pick_n_place' tool
class pick_n_place_implementation(BaseTool):
    "A helper tool for pick_n_place"
    name = "generalized_pick_n_place"
    description = "the tool which takes an object from pick pose to target pose"
    args_schema: Type[BaseModel] = pick_n_place_definition

    def _run(self, pick_pose: list, int_bf: list, drop_pose: list, int_af: list) -> None:

        # Move through intermediate positions before reaching the pick pose
        if len(int_bf) != 0:
            for i in range(len(int_bf)):
                move_to_pose_implementation()._run(goal_pose=int_bf[i], wait=True)
        
        move_to_pose_implementation()._run(goal_pose=pick_pose, wait=True)
        control_gripper_implementation()._run(switch=True, robot_to_use=1)
        
        # Move through intermediate positions after picking the object
        if len(int_af) != 0:
            for i in range(len(int_af)):
                move_to_pose_implementation()._run(goal_pose=int_af[i], wait=True)

        move_to_pose_implementation()._run(goal_pose=drop_pose, wait=True)
        control_gripper_implementation()._run(switch=False, robot_to_use=1)

# Helper class for getting transformation between parent and child frames
class get_transform_implementation():
    """Tool to get transformation between parent frame and child frame"""
    name = "get_transform"
    description = "Get transformation between parent frame and child frame from ros topic."

    def get_transform(self, parent_frame: str, child_frame: str):
        tfBuffer = tf2_ros.Buffer()
        listener = tf2_ros.TransformListener(tfBuffer)
        rate = rospy.Rate(10.0)
        while not rospy.is_shutdown():
            try:
                # Lookup the transform with target_frame as 'tcp' and source_frame as 'camera_colo_optical_frame'
                trans = tfBuffer.lookup_transform(parent_frame, child_frame, rospy.Time())
                
                trans_x = trans.transform.translation.x
                trans_y = trans.transform.translation.y
                trans_z = trans.transform.translation.z

                rot_x = trans.transform.rotation.x
                rot_y = trans.transform.rotation.y
                rot_z = trans.transform.rotation.z
                rot_w = trans.transform.rotation.w

                rotation_matrix = quaternion_matrix((rot_x, rot_y, rot_z, rot_w))
                transformation_matrix = translation_matrix((trans_x, trans_y, trans_z)) @ rotation_matrix

                return transformation_matrix

            except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException):
                rate.sleep()
                robot_logger.warn("Waiting for transform to be published")
                continue

# Data model for the 'pick_object' tool
class pick_object_definition(BaseModel):
    object: str = Field(description="object which the robot needs to pick up")

# Implementation of the 'pick_object' tool
class pick_object_implementation(BaseTool):
    '''Tool to pick objects'''
    name = "pick_object"
    description = "Tool to pick up the object mentioned in the prompt"
    args_schema: Type[BaseModel] = pick_object_definition

    def _run(self, object: str, take_home: bool = True):
        # initializers
        robot_ip = ["10.42.0.53"]

        home = get_zone_pose_implementation()._run(robot_ip=robot_ip[0], zone_name="home")
        move_to_pose_implementation()._run(goal_pose=home, robot_to_use=1, wait=True)

        '''Flow of picking: first it goes towards the object in x Z plane means translate to a pose directly 
        in front of object and then moves towards the object to pick'''

        print("Picking", object)
        control_gripper_implementation()._run(switch=True)

        pose = check_pose_implementation()._run(object=object)

        if pose is None:
            send_msg(message="Unable to detect the object. Please try again!")
            move_to_pose_implementation()._run(goal_pose=home, robot_to_use=1, wait=True)

        pose[0] = pose[0]  # offset in x axis so that gripper properly grasps object
        pose[2] = pose[2] / 2 - 0.01  # picking object from center added a 1 cm down offset can be changed
            
        # Translate towards the object in x axis from current position
        curr_pose = get_pose_implementation()._run(robot_to_use=1)
        move_translate_implementation()._run(x=pose[0] - curr_pose[0], y=0, z=0, toolspeed=150)
           
        # Move to position of object to pick
        move_to_pose_implementation()._run(goal_pose=pose, wait=True)
            
        # Control gripper
        control_gripper_implementation()._run(switch=False)

        # Move to home pose
        if take_home:
            move_to_pose_implementation()._run(goal_pose=home, robot_to_use=1, wait=True)
        return

# Data model for the 'place_object' tool
class place_object_definition(BaseModel):
    drop_pose: list = Field(default=None, description="position of the drop")
    drop_zone: str = Field(default=None, description="The zone/place where we need to put the object")
    drop_object: str = Field(default=None, description="The object on which robot needs to place the already picked up object")

# Implementation of the 'place_object' tool
class place_object_implementation(BaseTool):
    '''Tool to pick objects'''
    name = "place_object"
    description = "Tool to place the object to a particular position mentioned in the prompt"
    args_schema: Type[BaseModel] = place_object_definition

    def _run(self, drop_pose: list = None, drop_zone: str = None, drop_object: str = None):
        robot_ip = ["10.42.0.53"]

        if drop_pose is not None:
            move_to_pose_implementation()._run(goal_pose=drop_pose, wait=True)
            
        if drop_object is not None:
            print(drop_object)
            
        if drop_zone is not None:
            zone_pose = get_zone_pose_implementation()._run(robot_ip=robot_ip[0], zone_name=drop_zone)
            move_to_pose_implementation()._run(goal_pose=zone_pose)

        control_gripper_implementation()._run(switch=False)
        home = get_zone_pose_implementation()._run(robot_ip=robot_ip[0], zone_name="home")
        move_to_pose_implementation()._run(goal_pose=home, robot_to_use=1, wait=True)

        return
    
# Data model for the 'check_pose' tool
class check_pose_definition(BaseModel):
    object: str = Field(default=None, description="the object name whose position is to be determined")
    marker_id: int = Field(default=None, description="the id of the aruco marker whose position we need to find")
    both: bool = Field(default=False, description="The boolean which checks if robots needs to check both the object and marker pose or single thing. True for both of the poses and false for if a single pose is asked")

# Implementation of the 'check_pose' tool
class check_pose_implementation(BaseTool):
    """Tool to tell the position of the object"""
    name = "check_pose"
    description = "To calculate the given object's position in cartesian plane"
    args_schema: Type[BaseModel] = check_pose_definition

    def _run(self, object: str = None, marker_id: int = None, both: bool = False) -> list:
        robot_ip = ["10.42.0.53"]

        if object is not None:
            print(f"The position of {object} is {object_pose}")
            return object_pose
        
        elif marker_id is not None:
            marker_pose = aruco_img_2_base_implementation()._run(marker_id=str(marker_id), robot_ip=robot_ip[0])
            print(f"The position of {marker_id} is {marker_pose}")
            return marker_pose
        
        elif both:
            object = get_best_match_implementation()._run(object=object)
            object_pose = ximg2xbase_implementation()._run(object=object, robot_ip=robot_ip[0], cam=cam)
            marker_pose = aruco_img_2_base_implementation()._run(marker_id=marker_id, robot_ip=robot_ip[0])
            print(f"The position of {object_pose} and {marker_id} is {object_pose}:::::{marker_pose}")
            return object_pose, marker_pose

# -----------------------------------------------------------------------------
#          DEMO SKILLS
# -----------------------------------------------------------------------------


    
