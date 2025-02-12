import os
import re
import ast
import sys
import json
import yaml
import uuid
import dotenv
import rospy
import getpass
import rospkg
import pusher
import requests
import subprocess
from urllib.parse import urlsplit, unquote
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage

rospack = rospkg.RosPack()
base_agent = rospack.get_path('robogpt_agents')
sys.path.append(base_agent)
robogpt_env_path = os.path.join(base_agent, "config", ".demo_env")
################################


def load_yaml_env_variables(yaml_file):
    # Load the environment variables from the YAML file into os.environ
    with open(yaml_file, 'r') as file:
        env_vars = yaml.safe_load(file)
    
    # Set the environment variables and return them as a dictionary
    for key, value in env_vars.items():
        os.environ[key] = str(value)  # Ensure values are strings for os.environ
    
    return env_vars

def load_robot_poses(file_path):
    """
    Load robot poses from a JSON file.
    
    Args:
        file_path (str): The path to the robot poses JSON file.
    
    Returns:
        dict: A dictionary containing robot poses.
    """
    with open(file_path, 'r') as f:
        return json.load(f)

def send_msg(pusher_client, message):
    """
    Sends a message to a specified Pusher channel.

    Args:
        pusher_client: The Pusher client instance.
        message (str): The message to send.
    """
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
    Extracts the prompt text, an ID (if present), and any URL found in the prompt text.

    Returns:
        tuple: A tuple containing the prompt text, its associated ID (empty string if not found),
               and the URL (or None if not present).
    """
    output_file = os.path.join(base_agent, "config/tools_config/output.json")
    command = f"pusher channels apps subscribe --app-id {app_id} --channel private-chat"

    # Execute the command to subscribe to the Pusher channel and process the output
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    with open(output_file, "w") as f:
        for line in process.stdout:
            print("Raw line:", line)  # Debug: print the raw line

            # Filter: Only process messages with event 'chatbox'
            if "event=chatbox" not in line:
                continue

            # Use a regex to extract the JSON portion from the line.
            # This looks for the substring starting with 'message=' and then a { ... } block.
            json_match = re.search(r'message=({.*})', line)
            if not json_match:
                continue  # if the JSON block isn't found, skip this line

            json_str = json_match.group(1)
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print("JSON decode error:", e)
                continue

            # Extract the prompt text. In your original message, the prompt is under the "message" key.
            prompt = data.get("message", "")
            # If there is an ID field in the JSON, extract it. Otherwise, default to an empty string.
            id = data.get("id", "")

            # Use a regex to search for a URL in the prompt text.
            # This regex will match http:// or https:// followed by non-whitespace, non-quote characters.
            url_match = re.search(r'https?://[^\s"]+', prompt)
            url = url_match.group(0) if url_match else None

            # Debug prints
            print("Prompt:", prompt)
            return prompt, id, url



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


def extract_base_class_names(file_path, suffixes=None):
    """
    Extracts base class names from a Python file by removing specified suffixes.

    Args:
        file_path (str): Path to the Python file.
        suffixes (list, optional): List of suffixes to remove from class names.

    Returns:
        list: A sorted list of unique base class names.
    """
    if suffixes is None:
        suffixes = ['_implementation']

    with open(file_path, 'r') as file:
        file_content = file.read()

    # Parse the Python file into an AST
    try:
        tree = ast.parse(file_content)
    except SyntaxError as e:
        print(f"Syntax error while parsing {file_path}: {e}")
        return []

    base_class_names = set()

    # Iterate over all nodes in the AST
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            base_name = None
            # Check for each suffix and remove if present
            for suffix in suffixes:
                if class_name.endswith(suffix):
                    potential_base = class_name[:-len(suffix)]
                    if potential_base:  # Ensure base name is not empty
                        base_name = potential_base
                        break
            if base_name:
                base_class_names.add(base_name)
            else:
                # Optionally, handle classes without the specified suffixes
                # For example, you can choose to ignore them or include their full names
                pass  # Currently, we're ignoring classes without the suffixes

    return sorted(base_class_names)  # Sorted for consistency

def download_file(url, output_dir='~/'):
    """
    Downloads a file from the specified URL and saves it using the original file name,
    stripping off any trailing hash that may have been appended to the file name.

    Args:
        url (str): The URL of the file to download.
        output_dir (str, optional): The directory where the file will be saved. Defaults to the current directory.

    Returns:
        str: The path to the downloaded file, or None if an error occurred.
    """
    # Extract the filename from the URL.
    parsed_url = urlsplit(url)
    filename = os.path.basename(parsed_url.path)
    # Decode URL-encoded characters (e.g., %20 becomes a space)
    filename = unquote(filename)

    # Use a regex substitution to remove the trailing hash if present.
    # This pattern looks for an extension (dot followed by letters/digits)
    # followed by at least 8 hexadecimal characters at the end of the filename.
    filename = re.sub(r'(\.[A-Za-z0-9]+)[0-9a-f]{8,}$', r'\1', filename)

    # Ensure the output directory exists.
    os.makedirs(output_dir, exist_ok=True)
    local_filepath = os.path.join(output_dir, filename)

    try:
        # Download the file with streaming enabled.
        with requests.get(url, stream=True) as response:
            response.raise_for_status()  # Raise an error for bad status codes.
            with open(local_filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Filter out keep-alive chunks.
                        file.write(chunk)
        print(f"File downloaded successfully: {local_filepath}")
        rospy.set_param("/attachment_path",local_filepath)
        
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

def ai_formatted_msg(message: str) -> str:
        """
        Given an input message string, this method creates a prompt incorporating the current LLM model's name,
        sends the prompt to ChatOpenAI for rephrasing, and returns the formatted (rephrased) string.
        """
        # Initializing important variables
        keys = load_env_variables(robogpt_env_path)
        pusher_client = pusher.Pusher(
            app_id=keys['PUSHER_APP_ID'],
            key=keys['NEXT_PUBLIC_PUSHER_KEY'],
            secret=keys['PUSHER_SECRET'],
            cluster=keys['NEXT_PUBLIC_PUSHER_CLUSTER']
        )

        llm = ChatOpenAI(
            model=keys['AI_MODEL'],
            temperature=keys['AI_TEMPERATURE'],
            organization=keys['ORGANIZATION'],
            openai_api_key=keys['OPENAI_API_KEY']
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
            llm_model=keys['AI_MODEL'],
            message=message
        )
        rephrased_response = llm([HumanMessage(content=formatted_prompt)])
        msg_content = rephrased_response.content if hasattr(rephrased_response, "content") else str(rephrased_response)
        # Send the message to the web app
        send_msg(pusher_client=pusher_client, message=msg_content)
        return msg_content