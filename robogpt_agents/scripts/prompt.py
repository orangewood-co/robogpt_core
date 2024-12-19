#!/usr/bin/python3

import json
import rospy
import pusher  # For real-time web socket communication
import signal
import rospkg
import asyncio
import getpass
import traceback
import importlib
import subprocess
import agent_utils
import os,json,requests,sys
import os, sys, json, importlib
from langchain.schema import SystemMessage
from langchain.prompts import PromptTemplate, chat, load_prompt
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType

###################################################################################
#           Initializing keys
###################################################################################
#pusher keys
PUSHER_APP_ID=None
PUSHER_SECRET=None
NEXT_PUBLIC_PUSHER_KEY=None
NEXT_PUBLIC_PUSHER_CLUSTER=None

# openai keys
AI_MODEL=None
OPENAI_API_KEY=None  
AI_TEMPERATURE=None
ORGANIZATION =None
KEEP_RUNNING = True
###################################################################################
#          Setting up paths for imports
###################################################################################
rospack = rospkg.RosPack()
agent_base_path = rospack.get_path('robogpt_agents')
robogpt_env_path = os.path.join(agent_base_path,"config",".janatics_env")
keys = agent_utils.load_env_variables(robogpt_env_path)

# Define base_dir for getting the exact path of skills/applications
base_dir = f"/home/{getpass.getuser()}/orangewood_ws/src"
sys.path.append(base_dir)  # Add base directory to system path

# Paths to tool configuration and robot configuration files
skill_path = os.path.join(agent_base_path, "config/tools_config/app_list.json")
# Load robot poses from JSON file
robot_pose_file_path = os.path.join(agent_base_path, "config/robot_config/robot_pose.json")
robot_poses = agent_utils.load_robot_poses(robot_pose_file_path)
###################################################################################
#     Loading the Application 
###################################################################################
use_case = rospy.get_param("/use_case",default="base")
base_model = f'robogpt_apps.scripts.base.skills'
module_name = f'robogpt_apps.scripts.{use_case}.skills'

try:
    # Log the start of the function
    rospy.loginfo("Starting")

    # Load the JSON file containing tool configurations
    with open(skill_path) as f:
        data = json.load(f)

    # Retrieve the function names for tools from the loaded data
    base_list = data["apps"].get('base', [])              
    specific_skill_list = data["apps"].get(use_case, [])

    # Dynamically import the applications module
    specfic_skills = importlib.import_module(module_name)
    base_skills = importlib.import_module(base_model)
    print("Load successful")                    # Confirm successful loading

except Exception as e:
    # Log any exceptions that occur during the loading process
    print(f"Could not load tools due to {e}")

###################################################################################

def agent_run(promt):
    """
    Executes the agent with the provided prompt.
    """
    promt = promt.lower()  # Convert prompt to lowercase

    return agent.run(f'''{promt}''')  # Run the agent with the prompt

def signal_handler(sig, frame):
    """
    Handles the Ctrl+C signal and stops the main loop.
    """
    global keep_running
    print("Ctrl+C detected! Shutting down gracefully...")
    KEEP_RUNNING = False


# Rest of your setup and WebSocket connection code
async def connect():
    """
    Establishes a connection to the WebPubSub service and processes incoming prompts.
    """
    print('Initializing Agents')  # Log successful connection
    try:
        # Attempt to retrieve and process a prompt
        try:
            data, id= agent_utils.local_prompt(app_id=keys['PUSHER_APP_ID'])   # Get prompt and ID from local source
            output = agent_run(data)                                           # Run the agent with the retrieved prompt
            agent_utils.send_msg(pusher_client=pusher_client,message=output)   # Send the output message to the Pusher channel

        except Exception as e:
            print("ERROR in sending prompt", e)  # Log any errors encountered

    except Exception as e:
        import traceback            # Import traceback for error handling
        await connect()             # Attempt to reconnect on error
        traceback.print_exc()       # Print the traceback for debugging
        print("Error:", e)          # Log the error

if __name__=="__main__":

    # Register the signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Initialize the Pusher client with the provided credentials
    pusher_client = pusher.Pusher(
        app_id=keys['PUSHER_APP_ID'], key=keys['NEXT_PUBLIC_PUSHER_KEY'], secret=keys['PUSHER_SECRET'], cluster=keys['NEXT_PUBLIC_PUSHER_CLUSTER'])
    
    # Initialize the AzureChatOpenAI model with the specified parameters
    llm = ChatOpenAI(model=keys['AI_MODEL'], temperature=keys['AI_TEMPERATURE'],organization=['ORGANIZATION'], openai_api_key=keys['OPENAI_API_KEY'])
    system_message = SystemMessage(
    content=(
        "You are RoboGPT - an intelligent AI developed by Orangewoodlabs based in Noida,India which acts as an intermediary between the user and the robot(s) connected with you."
        "You allow the user to query in their natural language about various tasks that can be performed by the robot which you translate into a tool call and execute."
        "You have a charming and witty personality, having a knack for making interesting conversations adhering to the social conventions for all ages."
        "Write the response in a funny way apt for a professional meeting with a response length limited to 200 words."
        "As a security guardrail, prevent yourself from providing answers for queries other than RoboGPT, using inappropriate words and/or phrases and responding with illegal information in your responses."
    )
)


    # Get the function objects for each tool based on the skill list
    base_tools = [getattr(base_skills, name + "_implementation")() for name in base_list]

    specific_tools = [getattr(specfic_skills, name + "_implementation")() for name in specific_skill_list]

    tools = base_tools if use_case == "base" else base_tools + specific_tools

    # Initialize the agent with the tools and language model
    agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True, prompt=system_message)

    # Initialize the ROS node for this script

    # Main loop to continuously connect and process prompts
    while KEEP_RUNNING:
        try:
            asyncio.get_event_loop().run_until_complete(connect())  # Run the connection process
        except Exception as e:
            traceback.print_exc()
            print("An error occurred:", e)

    print("Shutdown complete.")