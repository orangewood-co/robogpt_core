import os
import sys
import json
import uuid
import dotenv
import rospkg
import requests
import subprocess

rospack = rospkg.RosPack()
base_agent = rospack.get_path('robogpt_agents')
sys.path.append(base_agent)
################################
def send_msg(pusher_client,message):
    """
    Sends a message to a specified Pusher channel.

    Args:
        message (str): The message to send.
    """
    # Trigger the message event on the Pusher channel
    pusher_client.trigger('private-chat', 'evt::test', {'message': message})

def load_env_variables(env_file):
    # Load the environment variables from the .env file into os.environ
    dotenv.load_dotenv(env_file)
    
    # Extract the environment variables from the .env file dynamically
    env_vars = {}
    with open(env_file, 'r') as file:
        for line in file:
            # Skip comments and blank lines
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                env_vars[key] = value
                os.environ[key] = value  # Set the environment variables
    
    # Return the environment variables as a dictionary
    return env_vars
    
def local_prompt(app_id):
    """
    Subscribes to a Pusher channel and retrieves messages containing prompts.

    Returns:
        tuple: A tuple containing the prompt text and its associated ID.
    """
    output_file = os.path.join(base_agent, "config/tools_config/output.json")
    command = f"pusher channels apps subscribe --app-id {app_id} --channel private-chat"

    # Execute the command to subscribe to the Pusher channel and process the output
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    with open(output_file, "w") as f:
        for line in process.stdout:
            print(line)                                 # Print the output line for debugging
            parts = line.split(":")                     # Split the line by colon
            if len(parts) > 2:                          # Ensure there are enough parts to process
                subparts = parts[2].split('"')          # Extract the prompt
                prompt = subparts[1]                    # Get the prompt text
                subid = parts[3].split('"')             # Extract the ID
                id = subid[1]                           # Get the ID
                print(prompt)                           # Print the prompt for debugging
                
                return prompt, id                       # Return the prompt and ID
            



def translate_text(key,endpoint,location,text_to_translate, to_language="en"):
    """
    Translates the given text to the specified language using Azure Translator.

    Args:
        text_to_translate (str): The text to translate.
        to_language (str): The target language for translation (default is English).

    Returns:
        str: The translated text if successful, otherwise None.
    """
    path = '/translate'
    constructed_url = endpoint + path                   # Construct the full API URL
    params = {
        'api-version': '3.0',
        'to': [to_language]                             # Specify the target language
    }
    headers = {
        'Ocp-Apim-Subscription-Key': key,               # Azure subscription key
        'Ocp-Apim-Subscription-Region': location,       # Azure region
        'Content-type': 'application/json',             # Content type for the request
        'X-ClientTraceId': str(uuid.uuid4())            # Unique trace ID for the request
    }
    body = [{
        'text': text_to_translate                       # The text to be translated
    }]
    # Send the translation request
    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()                           # Parse the JSON response
    # Return the translated text if available
    if response and response[0]['translations']:
        return response[0]['translations'][0]['text']
    else:
        return None                                     # Return None if translation failed
    

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

