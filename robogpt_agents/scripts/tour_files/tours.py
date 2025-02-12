import os
import sys
import rospy
import rospkg
import pusher
import time
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from std_msgs.msg import Bool

# Get package path and add it to sys.path
rospack = rospkg.RosPack()
agent_base_path = rospack.get_path('robogpt_agents')
sys.path.append(agent_base_path)
from scripts.agent_utils import ai_formatted_msg

class Pick_N_Place_Tour():
    def __init__(self) -> None:
        # Initialize the ROS node first
        self.pass_bool = False
        # Create subscriber for boolean messages
        self.boolean_subscriber = rospy.Subscriber("/pass_topic", Bool, self.boolean_callback)
        rospy.set_param("/tour_flag",True)
    def boolean_callback(self, msg: Bool):
        rospy.loginfo("Received boolean message: %s", msg.data)
        self.pass_bool = msg.data

    def put_cv_mask(self,switch: bool):
        rospy.set_param("/masking",switch)
        # Placeholder for further implementation

    def wait_for_confirmation(self, prompt: str):
        """
        Resets the confirmation flag and waits until pass_bool becomes True.
        """
        rospy.loginfo(prompt)
        self.pass_bool = False  # Reset the flag before waiting
        time.sleep(2)
        # Wait in a loop until the flag is set to True (by the subscriber callback)
        while not self.pass_bool and not rospy.is_shutdown():
            rospy.sleep(0.1)

    def script(self):
        # Send robot to home position
        time.sleep(3)
        ai_formatted_msg("Let's get Started with this, First Move the robot to home pose. You can just say 'Move robot to home'")
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) for home position...")

        # Instruct user for training a new object
        ai_formatted_msg("Great! Let's move to the next step: training these objects.")
        self.put_cv_mask(switch=True)
        ai_formatted_msg("Open the mask window by clicking on Live Stream and move the robot to center the object in the camera.")
        ai_formatted_msg("For robot motion, enable hand teach mode. Try the prompt 'enable hand teach mode'.If Using simulation just move the object")
        # ai_formatted_msg("Save first waypoint name it scan1")
        # self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after enabling hand teach mode...")
        # ai_formatted_msg("Save first waypoint name it scan2")
        # self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after enabling hand teach mode...")
        # ai_formatted_msg("Save first waypoint name it scan3")
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after enabling hand teach mode...")


        # Instruct user for vision model training
        ai_formatted_msg("Now if object is there let's train this object and get your vision models ready for detection.")
        ai_formatted_msg("Specify a characteristic of the object along with the name you want to give it. Also, set the images and epochs or I will use the default values.")
        ai_formatted_msg("Here is a sample prompt: 'train this black object and name it box. Use 100 images and 65 epochs'.")
        self.put_cv_mask(switch=False)
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after vision model training prompt...")

        # Instruct user to save waypoints for pick action
        ai_formatted_msg("Great! We are ready with the vision models. Let's save the waypoints for the pick action.")
        ai_formatted_msg("First, put the robot in hand teach mode. I taught you how to do that—use that command only.")
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after putting the robot in hand teach mode...")

        ai_formatted_msg("Now, move the robot to the point you want to save, and use this test prompt: 'Save this pose as test'. Replace 'test' with the name you want to save.")
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after saving the pose...")

        ai_formatted_msg("You can save waypoints like this and inform me when you are done.")
    
# if __name__ == "__main__":
#     pnp = Pick_N_Place_Tour()
#     pnp.script()
