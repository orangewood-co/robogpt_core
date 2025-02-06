import os
import sys
import rospy
import rospkg
import pusher
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from std_msgs.msg import Bool

# Get package path and add it to sys.path
rospack = rospkg.RosPack()
agent_base_path = rospack.get_path('robogpt_agents')
sys.path.append(agent_base_path)
from scripts.agent_utils import load_env_variables, send_msg

class Pick_N_Place_Tour():
    def __init__(self) -> None:
        # Initialize the ROS node first
        rospy.init_node("rosnode_asli_wali")
        self.pass_bool = False

        # Load environment variables and initialize pusher client
        self.robogpt_env_path = os.path.join(agent_base_path, "config", ".janatics_env")
        self.keys = load_env_variables(self.robogpt_env_path)
        self.pusher_client = pusher.Pusher(
            app_id=self.keys['PUSHER_APP_ID'],
            key=self.keys['NEXT_PUBLIC_PUSHER_KEY'],
            secret=self.keys['PUSHER_SECRET'],
            cluster=self.keys['NEXT_PUBLIC_PUSHER_CLUSTER']
        )

        # Create subscriber for boolean messages
        self.boolean_subscriber = rospy.Subscriber("/boolean_topic", Bool, self.boolean_callback)

    def boolean_callback(self, msg: Bool):
        rospy.loginfo("Received boolean message: %s", msg.data)
        self.pass_bool = msg.data

    def ai_formatted_msg(self, message: str) -> str:
        """
        Given an input message string, this method creates a prompt incorporating the current LLM model's name,
        sends the prompt to ChatOpenAI for rephrasing, and returns the formatted (rephrased) string.
        """
        llm = ChatOpenAI(
            model=self.keys['AI_MODEL'],
            temperature=self.keys['AI_TEMPERATURE'],
            organization=self.keys['ORGANIZATION'],
            openai_api_key=self.keys['OPENAI_API_KEY']
        )
        rephrase_template = PromptTemplate(
            template=(
                "Given that the current model is {llm_model}, please rephrase the following system message "
                "to suit the style and capabilities of the model:\n\n"
                "{message}"
            ),
            input_variables=["llm_model", "message"]
        )
        formatted_prompt = rephrase_template.format(
            llm_model=self.keys['AI_MODEL'],
            message=message
        )
        rephrased_response = llm([HumanMessage(content=formatted_prompt)])
        msg_content = rephrased_response.content if hasattr(rephrased_response, "content") else str(rephrased_response)
        # Send the message to the web app
        send_msg(pusher_client=self.pusher_client, message=msg_content)
        return msg_content

    def put_cv_mask(self):
        # Placeholder for further implementation
        pass

    def wait_for_confirmation(self, prompt: str):
        """
        Resets the confirmation flag and waits until pass_bool becomes True.
        """
        rospy.loginfo(prompt)
        self.pass_bool = False  # Reset the flag before waiting
        # Wait in a loop until the flag is set to True (by the subscriber callback)
        while not self.pass_bool and not rospy.is_shutdown():
            rospy.sleep(0.1)

    def start(self):
        # Send robot to home position
        self.ai_formatted_msg("Let's first take the robot to the home position. Try prompting 'Move robot to home' command")
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) for home position...")

        # Instruct user for training a new object
        self.ai_formatted_msg("Great! Let's move to the next step: training these objects.")
        self.put_cv_mask()
        self.ai_formatted_msg("Open the mask window by clicking on Live Stream and move the robot to center the object in the camera.")
        self.ai_formatted_msg("For robot motion, enable hand teach mode. Try the prompt 'enable hand teach mode'.")
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after enabling hand teach mode...")

        # Instruct user for vision model training
        self.ai_formatted_msg("Now let's train this object and get your vision models ready for detection.")
        self.ai_formatted_msg("Specify a characteristic of the object along with the name you want to give it. Also, set the images and epochs or I will use the default values.")
        self.ai_formatted_msg("Here is a sample prompt: 'train this black object and name it box. Use 100 images and 65 epochs'.")
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after vision model training prompt...")

        # Instruct user to save waypoints for pick action
        self.ai_formatted_msg("Great! We are ready with the vision models. Let's save the waypoints for the pick action.")
        self.ai_formatted_msg("First, put the robot in hand teach mode. I taught you how to do that—use that command only.")
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after putting the robot in hand teach mode...")

        self.ai_formatted_msg("Now, move the robot to the point you want to save, and use this test prompt: 'Save this pose as test'. Replace 'test' with the name you want to save.")
        self.wait_for_confirmation("Waiting for confirmation (pass_bool == True) after saving the pose...")

        self.ai_formatted_msg("You can save waypoints like this and inform me when you are done.")
    
if __name__ == "__main__":
    pnp = Pick_N_Place_Tour()
    pnp.start()
