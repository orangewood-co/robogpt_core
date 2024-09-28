#!/usr/bin/python3

import rospy
import asyncio
import importlib
import requests
import json
import uuid
import rospkg
import os, sys, json, importlib
from langchain.prompts import PromptTemplate, chat, load_prompt
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
import os,json,requests,sys
import pusher  # For real-time web socket communication
import subprocess
import agent_utils

###################################################################################
#           Initializing keys
###################################################################################
#pusher keys
PUSHER_APP_ID=None
PUSHER_SECRET=None
NEXT_PUBLIC_PUSHER_KEY=None
NEXT_PUBLIC_PUSHER_CLUSTER=None

# openai keys
DEPLOYMENT_NAME=None
OPENAI_API_BASE=None
OPENAI_API_KEY=None  
OPENAI_API_TYPE=None
OPENAI_API_VERSION=None
TEMPERATURE=None

###################################################################################
#          Setting up paths for imports
###################################################################################
rospack = rospkg.RosPack()
agent_base_path = rospack.get_path('robogpt_agents')
robogpt_env_path = os.path.join(agent_base_path,"config",".robogpt_env")
keys = agent_utils.load_env_variables(robogpt_env_path)


# Define base_dir for getting the exact path of skills/applications
base_dir = f"/home/{os.getlogin()}/orangewood_ws/src"
sys.path.append(base_dir)  # Add base directory to system path

# Paths to tool configuration and robot configuration files
skill_path = os.path.join(agent_base_path, "config/tools_config/app_list.json")

###################################################################################
#     Loading the Application 
###################################################################################
use_case = rospy.get_param("/use_case",default="base")
module_name = f'robogpt_apps.scripts.{use_case}_file'
try:
    rospy.loginfo("Starting")                   # Log the start of the function

    # Load the JSON file containing tool configurations
    with open(skill_path) as f:
        data = json.load(f)
    # Retrieve the function names for tools from the loaded data
    skill_list = data["apps"]

    # Dynamically import the applications module
    applications = importlib.import_module(module_name)
    print("Load successful")                    # Confirm successful loading

except Exception as e:
    # Log any exceptions that occur during the loading process
    print(f"Could not load tools due to {e}")

###################################################################################

def agent_run(promt):
    """
    Executes the agent with the provided prompt.

    Args:
        promt (str): The prompt to be processed by the agent.

    Returns:
        The output from the agent after processing the prompt.
    """
    print("prompt::::::", promt)        # Print the prompt for debugging
    return agent.run(f'''{promt}''')    # Run the agent with the prompt


# Rest of your setup and WebSocket connection code
async def connect():
    """
    Establishes a connection to the WebPubSub service and processes incoming prompts.
    """
    print('Initializing Agents')  # Log successful connection
    try:
        # Attempt to retrieve and process a prompt
        try:
            data, id= agent_utils.local_prompt(app_id=keys['PUSHER_APP_ID'])           # Get prompt and ID from local source
            output = agent_run(data)                                           # Run the agent with the retrieved prompt
            print(output)                                                      # Print the output for debugging
            agent_utils.send_msg(pusher_client=pusher_client,message=output)   # Send the output message to the Pusher channel

        except Exception as e:
            print("ERROR in sending prompt", e)  # Log any errors encountered

    except Exception as e:
        import traceback            # Import traceback for error handling
        await connect()             # Attempt to reconnect on error
        traceback.print_exc()       # Print the traceback for debugging
        print("Error:", e)          # Log the error


if __name__=="__main__":

    # Initialize the Pusher client with the provided credentials
    pusher_client = pusher.Pusher(
        app_id=keys['PUSHER_APP_ID'], key=keys['NEXT_PUBLIC_PUSHER_KEY'], secret=keys['PUSHER_SECRET'], cluster=keys['NEXT_PUBLIC_PUSHER_CLUSTER'])
    
    # Initialize the AzureChatOpenAI model with the specified parameters
    llm = AzureChatOpenAI(
        deployment_name=keys['DEPLOYMENT_NAME'],            # The deployment name for the model
        openai_api_base=keys['OPENAI_API_BASE'],            # Base URL for the OpenAI API
        openai_api_key=keys['OPENAI_API_KEY'],              # API key for authentication
        openai_api_type=keys['OPENAI_API_TYPE'],            # Specify Azure as the API type
        openai_api_version=keys['OPENAI_API_VERSION'],      # API version
        temperature=keys['TEMPERATURE'],                     # Sampling temperature for response variability
    )


    # Get the function objects for each tool based on the skill list
    tools = [getattr(applications, name + "_implementation")() for name in skill_list]

    # Initialize the agent with the tools and language model
    agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)

    # Initialize the ROS node for this script
    # Main loop to continuously connect and process prompts
    while True:
        asyncio.get_event_loop().run_until_complete(connect())  # Run the connection process