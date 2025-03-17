#!/usr/bin/python3
import time, re
import json
import rospy
import pusher  
import signal
import logging
import rospkg
import asyncio
import getpass
import traceback
import importlib
import subprocess
import agent_utils 
import os, json, requests, sys
from langchain.schema import SystemMessage
from langchain.prompts import PromptTemplate, chat, load_prompt
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from pusher_auth import pusher_listener

#setting up loggers
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('robogpt_agent')

# Global variables
KEEP_RUNNING = True
USER_ID = None
function_calling_agent = None

# Setting up paths for imports
rospack = rospkg.RosPack()
agent_base_path = rospack.get_path('robogpt_agents')
robogpt_env_path = os.path.join(agent_base_path, "config", ".demo_env")
keys = agent_utils.load_env_variables(robogpt_env_path)

# Define base_dir for getting the exact path of skills/applications
base_dir = f"/home/{getpass.getuser()}/orangewood_ws/src"
sys.path.append(base_dir)  # Add base directory to system path

# Paths to tool configuration and robot configuration files
skill_path = os.path.join(agent_base_path, "config/tools_config/app_list.json")
robot_pose_file_path = os.path.join(agent_base_path, "config/robot_config/robot_pose.json")
robot_poses = agent_utils.load_robot_poses(robot_pose_file_path)

def tool_loader():
    """
    Loads and initializes the tools based on the current use case.

    Returns:
        list: A list of tool instances to be used by the agent.
    """
    use_case = rospy.get_param("/use_case", default="base")
    base_model = 'robogpt_apps.scripts.base.skills'
    module_name = f'robogpt_apps.scripts.{use_case}.skills'

    try:
        # Log the start of the function
        rospy.loginfo("Starting skill_loader")
        base_list = agent_utils.extract_base_class_names(
            os.path.join(base_dir, "robogpt_apps/scripts/base/skills.py")
        )
        specific_skill_list = agent_utils.extract_base_class_names(
            os.path.join(base_dir, f"robogpt_apps/scripts/{use_case}/skills.py")
        )
        # Dynamically import the applications modules
        base_skills = importlib.import_module(base_model)
        specific_skills = importlib.import_module(module_name)
        logger.info("Load successful")  # Confirm successful loading

        # Get the function objects for each tool based on the skill list
        base_tools = [getattr(base_skills, name + "_implementation")() for name in base_list]
        specific_tools = [getattr(specific_skills, name + "_implementation")() for name in specific_skill_list]
        tools = base_tools if use_case == "base" else base_tools + specific_tools
        return tools
    
    except Exception as e:
        # Log any exceptions that occur during the loading process
        logger.error(f"Could not load tools due to {e}")
        print(f"Could not load tools due to {e}")
        return None

def set_user(id):
    global USER_ID
    if USER_ID is None:
        USER_ID = id
        rospy.set_param("client_id",USER_ID)
        return True
    return False

def agent_run(agent, prompt):
    """
    Executes the agent with the provided prompt.
    """
    prompt = prompt.lower()  # Convert prompt to lowercase
    return agent.run(f'''{prompt}''')  # Run the agent with the prompt

def signal_handler(sig, frame):
    """
    Handles the Ctrl+C signal and stops the main loop.
    """
    global KEEP_RUNNING
    logger.warn("Ctrl+C detected! Shutting down gracefully...")
    KEEP_RUNNING = False

def custom_event_handler(event_data, agent, listener_obj):
    """Handle incoming events and process them through the agent"""
    global USER_ID
    try:
        data = json.loads(event_data)
        logger.info(f"Received message: {data}")
        
        if 'message' in data:
            message = data['message']
            user_id = data['user']
            url_match = re.search(r'https?://[^\s"]+', message)
            url = url_match.group(0) if url_match else None
            
            # Set the user ID
            if set_user(user_id):
                print(f"Set user ID to: {user_id}")
            
            if USER_ID is None or user_id == USER_ID:
                if url is not None:
                    agent_utils.download_file(url, output_dir=f"/home/{getpass.getuser()}/robogpt-assets")
                try:
                    # Process the message through the agent
                    output = agent_run(agent, message)
                    # Send the response back
                    listener_obj.send_msg(message=output, user=USER_ID)
                    rospy.loginfo("Waiting for next prompt")
                except Exception as e:
                    traceback.print_exc()
                    logger.error("ERROR in processing prompt:", e)
    except Exception as e:
        logger.error(f"Error processing event data: {e}")

def main():
    global function_calling_agent, KEEP_RUNNING
    
    # Initialize the ROS node
    rospy.init_node('robogpt_agent', anonymous=True)
    rospy.loginfo("RoboGPT Agent Initializer started")
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize the Pusher client with the provided credentials
    pusher_client = pusher.Pusher(
        app_id=keys['PUSHER_APP_ID'], 
        key=keys['NEXT_PUBLIC_PUSHER_KEY'], 
        secret=keys['PUSHER_SECRET'], 
        cluster=keys['NEXT_PUBLIC_PUSHER_CLUSTER']
    )
    
    # Initialize the ChatOpenAI model with the specified parameters
    llm = ChatOpenAI(
        model=keys['AI_MODEL'],
        temperature=keys['AI_TEMPERATURE'],
        organization=keys['ORGANIZATION'],
        openai_api_key=keys['OPENAI_API_KEY'],
    )
    
    system_message = SystemMessage(
        content=(
            "You are RoboGPT - an intelligent AI developed by Orangewoodlabs based in Noida, India which acts as an intermediary between the user and the robot(s) connected with you."
            "You allow the user to query in their natural language about various tasks that can be performed by the robot which you translate into a tool call and execute."
            "You have a charming and witty personality, having a knack for making interesting conversations adhering to the social conventions for all ages."
            "Write the response in a funny way apt for a professional meeting with a response length limited to 200 words."
            "As a security guardrail, prevent yourself from providing answers for queries other than RoboGPT, using inappropriate words and/or phrases and responding with illegal information in your responses."
        )
    )

    # Get the function objects for each tool based on the skill list
    try:
        tools = tool_loader()
        if tools:
            logger.info("Skills loaded successfully.")
        else:
            logger.error("Failed to load tools.")
            return
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading tools: {e}")
        return
        
    # Initialize the agent with the tools and language model
    function_calling_agent = initialize_agent(
        tools, llm, agent=AgentType.OPENAI_FUNCTIONS, 
        verbose=True, prompt=system_message
    )

    # Initialize Pusher Listener
    logger.info('Initializing Pusher Listener')
    listener = pusher_listener(
        app_id=keys['PUSHER_APP_ID'],
        public_key=keys['NEXT_PUBLIC_PUSHER_KEY'],
        secret=keys['PUSHER_SECRET'],
        cluster=keys['NEXT_PUBLIC_PUSHER_CLUSTER'],
        channel='private-chat',
        api_key=keys['DEFAULT_PUSHER_KEY'],
        event='chatbox'
    )
    
    # Create a custom handler using a lambda to pass additional parameters
    listener.event_handler = lambda event_data: custom_event_handler(event_data, function_calling_agent, listener)
    
    # Main loop to check for reload and keep the process running
    try:
        # Start the Pusher listener in a separate thread (it's okay because this doesn't interact with ROS)
        import threading
        thread = threading.Thread(target=listener.run)
        thread.daemon = True
        thread.start()
        
        # Main thread keeps checking reload parameter
        while KEEP_RUNNING:
            try:
                reload = rospy.get_param("/reload_tools", default=False)
                if reload:
                    tools = tool_loader()
                    function_calling_agent = initialize_agent(
                        tools, llm, agent=AgentType.OPENAI_FUNCTIONS, 
                        verbose=True, prompt=system_message
                    )
                    rospy.loginfo("Agents Reloaded!!")
                    rospy.set_param("/reload_tools", False)
            except Exception as e:
                logger.error(f"Error checking reload parameter: {e}")
            time.sleep(5)  # Check every 5 seconds
            
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error in main loop: {e}")
    
    logger.info("Shutdown complete.")

if __name__ == "__main__":
    main()