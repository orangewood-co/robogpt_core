#!/usr/bin/python3

import rospy
import asyncio
import importlib
import requests
import json
import uuid
import os, sys, json, importlib
from langchain.prompts import PromptTemplate, chat, load_prompt
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
import os,json,requests,sys
import pusher  # For real-time web socket communication
import spacy
import subprocess


# Load the English NLP model from spaCy
nlp = spacy.load('en_core_web_md')

# Azure Cognitive Services credentials for translation
key = "4def1954ca074a149e643e2fb8fd9561"
endpoint = "https://api.cognitive.microsofttranslator.com"
location = "centralindia"

# Import subprocess for executing shell commands

# Define JSON file paths for configuration
base_dir = f"/home/{os.getlogin()}/orangewood_ws/src"
sys.path.append(base_dir)  # Add base directory to system path

# Paths to tool configuration and robot configuration files
skill_path = os.path.join(base_dir, "robogpt_v3/robogpt_agents/config/tools_config/app_list.json")
config_file = os.path.join(base_dir, "robogpt_v3/robogpt_agents/config/robot_config/robogpt.json")
module_name = f'robogpt_apps.scripts.base_applications'

################################
def read_json_file(file_path):
    # Read and load the JSON file
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def extract_keys(data):
    # Extract app_id, key, secret, and cluster from the JSON data
    app_id = data.get("app_id")
    key = data.get("key")
    secret = data.get("secret")
    cluster = data.get("cluster")
    
    return app_id, key, secret, cluster
###############################

# Initialize the Pusher client with the provided credentials
data = read_json_file(config_file)
app_id, key, secret, cluster = extract_keys(data)
pusher_client = pusher.Pusher(
    app_id=app_id, key=key, secret=secret, cluster=cluster)

###############################

def reload_bot_control():
    """
    Reloads the bot control settings by loading tool configurations and 
    importing the necessary application modules.

    Returns:
        tuple: A tuple containing the applications module and the list of tool names.
    """
    try:
        rospy.loginfo("Starting")  # Log the start of the function

        # Load the JSON file containing tool configurations
        with open(skill_path) as f:
            data = json.load(f)

        # Retrieve the function names for tools from the loaded data
        tool_names = data["apps"]

        # Dynamically import the applications module
        applications = importlib.import_module(module_name)
        importlib.reload(applications)  # Reload the module to ensure the latest version is used
        print("Load successful")  # Confirm successful loading
        return applications, tool_names  # Return the applications module and tool names
    
    except Exception as e:
        # Log any exceptions that occur during the loading process
        print(f"Could not load tools due to {e}")

def local_prompt():
    """
    Subscribes to a Pusher channel and retrieves messages containing prompts.

    Returns:
        tuple: A tuple containing the prompt text and its associated ID.
    """
    output_file = os.path.join(base_dir, "robogpt_v3/robogpt_agents/config/tools_config/output.json")
    command = f"pusher channels apps subscribe --app-id {app_id} --channel private-chat"

    # Execute the command to subscribe to the Pusher channel and process the output
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    with open(output_file, "w") as f:
        for line in process.stdout:
            print(line)  # Print the output line for debugging
            parts = line.split(":")  # Split the line by colon
            if len(parts) > 2:  # Ensure there are enough parts to process
                subparts = parts[2].split('"')  # Extract the prompt
                prompt = subparts[1]  # Get the prompt text
                subid = parts[3].split('"')  # Extract the ID
                id = subid[1]  # Get the ID
                print(prompt)  # Print the prompt for debugging
                
                return prompt, id  # Return the prompt and ID

def send_msg(message):
    """
    Sends a message to a specified Pusher channel.

    Args:
        message (str): The message to send.
    """
    # Initialize the Pusher client (if not already done)
    pusher_client = pusher.Pusher(
        app_id=app_id, key=key, secret=secret, cluster=cluster)

    # Trigger the message event on the Pusher channel
    pusher_client.trigger('private-chat', 'evt::test', {'message': message})

def set_speed_factor():
    """
    Sets the speed factor for the robot by sending a request to the specified endpoint
    and updating the local configuration file accordingly.
    """
    # Construct the dynamic path to robogpt.json based on the current working directory
    config_dir = os.path.join(os.getcwd(), "config")
    robogpt_config = os.path.join(config_dir, "robogpt.json")

    # Request to set the speed factor
    s = {"speed": -1}
    speed_req = requests.post("https://robogpt.centralindia.cloudapp.azure.com/speed", json=s)
    print(float(speed_req.text))  # Print the response for debugging

    # Check the response and update the configuration if necessary
    if float(speed_req.text) == -1 or float(speed_req.text) < 10:
        print("Speed not set, Default speed is 30")  # Default speed message
    else:
        with open(robogpt_config, 'r') as f:
            robot_data = json.load(f)  # Load existing robot configuration
            robot_data["velocity_scaling"] = float(speed_req.text) / 100  # Update speed scaling
        with open(robogpt_config, 'w') as t:
            json.dump(robot_data, t)  # Save updated configuration
        print("Speed set to", float(speed_req.text))  # Confirm speed setting

def get_user_id(file_path):
    """
    Retrieves the user ID from a specified JSON file.

    Args:
        file_path (str): The path to the JSON file containing user data.

    Returns:
        str: The user ID if found, otherwise None.
    """
    with open(file_path, 'r') as file:
        data = json.load(file)  # Load user data from the file
    return data.get('user_id')  # Return the user ID

def translate_text(text_to_translate, to_language="en"):
    """
    Translates the given text to the specified language using Azure Translator.

    Args:
        text_to_translate (str): The text to translate.
        to_language (str): The target language for translation (default is English).

    Returns:
        str: The translated text if successful, otherwise None.
    """
    path = '/translate'
    constructed_url = endpoint + path  # Construct the full API URL

    params = {
        'api-version': '3.0',
        'to': [to_language]  # Specify the target language
    }

    headers = {
        'Ocp-Apim-Subscription-Key': key,  # Azure subscription key
        'Ocp-Apim-Subscription-Region': location,  # Azure region
        'Content-type': 'application/json',  # Content type for the request
        'X-ClientTraceId': str(uuid.uuid4())  # Unique trace ID for the request
    }
    
    body = [{
        'text': text_to_translate  # The text to be translated
    }]

    # Send the translation request
    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()  # Parse the JSON response

    # Return the translated text if available
    if response and response[0]['translations']:
        return response[0]['translations'][0]['text']
    else:
        return None  # Return None if translation failed

def check_tool_list(skill_path):
    """
    Checks the list of tools defined in the specified JSON file.

    Args:
        tool_path (str): The path to the tool configuration JSON file.

    Returns:
        list: A list of tool names.
    """
    with open(skill_path) as f:
        data = json.load(f)  # Load the tool configuration data

    tool_names = data["apps"]  # Retrieve the list of tool names
    return tool_names  # Return the list of tools

def agent_run(promt):
    """
    Executes the agent with the provided prompt.

    Args:
        promt (str): The prompt to be processed by the agent.

    Returns:
        The output from the agent after processing the prompt.
    """
    print("prompt::::::", promt)  # Print the prompt for debugging
    
    return agent.run(f'''{promt}''')  # Run the agent with the prompt

# Rest of your setup and WebSocket connection code
async def connect():
    """
    Establishes a connection to the WebPubSub service and processes incoming prompts.
    """
    print('Connected to WebPubSub')  # Log successful connection

    try:
        # Attempt to retrieve and process a prompt
        try:
            data, id = local_prompt()  # Get prompt and ID from local source
            output = agent_run(data)  # Run the agent with the retrieved prompt
            print(output)  # Print the output for debugging
            send_msg(message=output)  # Send the output message to the Pusher channel

        except Exception as e:
            print("ERROR in sending prompt", e)  # Log any errors encountered

    except Exception as e:
        import traceback  # Import traceback for error handling
        await connect()  # Attempt to reconnect on error
        traceback.print_exc()  # Print the traceback for debugging
        print("Error:", e)  # Log the error

# Initialize the AzureChatOpenAI model with the specified parameters
llm = AzureChatOpenAI(
    deployment_name="robotgpt4-test",  # The deployment name for the model
    openai_api_base="https://robotgpt4-test.openai.azure.com/",  # Base URL for the OpenAI API
    openai_api_key="dded2f3a90864ab4a25e25a34cd70f5e",  # API key for authentication
    openai_api_type="azure",  # Specify Azure as the API type
    openai_api_version="2023-08-01-preview",  # API version
    temperature=0.7,  # Sampling temperature for response variability
)

# Check the initial number of tools available
old_number_of_tools = len(check_tool_list(skill_path=skill_path))

data = ""

# Reload the bot_control module to update applications and tool list
applications, skill_list = reload_bot_control()

# Get the function objects for each tool based on the skill list
tools = [getattr(applications, name + "_implementation")() for name in skill_list]

# Initialize the agent with the tools and language model
agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)

# Initialize the ROS node for this script
# Main loop to continuously connect and process prompts
while True:
    asyncio.get_event_loop().run_until_complete(connect())  # Run the connection process