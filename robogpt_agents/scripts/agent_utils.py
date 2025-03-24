import os
import re
import ast
import sys
import json
import yaml
import uuid
import dotenv
import rospy
import time
import getpass
import rospkg
import pusher
import requests
import subprocess
from queue import Queue
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
    """
    Load environment variables from a YAML file into os.environ.

    Args:
        yaml_file (str): Path to the YAML file.

    Returns:
        dict: A dictionary of environment variables.
    """
    with open(yaml_file, 'r') as file:
        env_vars = yaml.safe_load(file)
    
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

def load_env_variables(env_file):
    """
    Load environment variables from a .env file into os.environ.

    Args:
        env_file (str): Path to the .env file.

    Returns:
        dict: A dictionary of environment variables.
    """
    dotenv.load_dotenv(env_file)
    
    env_vars = {}
    with open(env_file, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                env_vars[key] = value
                os.environ[key] = value
    
    return env_vars
   
def translate_text(key,endpoint,location,text_to_translate, to_language="en"):
    """
    Translates the given text to the specified language using Azure Translator.

    Args:
        key (str): Azure subscription key.
        endpoint (str): Azure endpoint URL.
        location (str): Azure region.
        text_to_translate (str): The text to translate.
        to_language (str): The target language for translation (default is English).

    Returns:
        str: The translated text if successful, otherwise None.
    """
    path = '/translate'
    constructed_url = endpoint + path
    params = {
        'api-version': '3.0',
        'to': [to_language]
    }
    headers = {
        'Ocp-Apim-Subscription-Key': key,
        'Ocp-Apim-Subscription-Region': location,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    body = [{'text': text_to_translate}]
    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()
    if response and response[0]['translations']:
        return response[0]['translations'][0]['text']
    else:
        return None
    

def set_speed_factor():
    """
    Sets the speed factor for the robot by sending a request to the specified endpoint
    and updating the local configuration file accordingly.
    """
    config_dir = os.path.join(os.getcwd(), "config")
    robogpt_config = os.path.join(config_dir, "robogpt.json")

    s = {"speed": -1}
    speed_req = requests.post("https://robogpt.centralindia.cloudapp.azure.com/speed", json=s)
    print(float(speed_req.text))

    if float(speed_req.text) == -1 or float(speed_req.text) < 10:
        print("Speed not set, Default speed is 30")
    else:
        with open(robogpt_config, 'r') as f:
            robot_data = json.load(f)
            robot_data["velocity_scaling"] = float(speed_req.text) / 100
        with open(robogpt_config, 'w') as t:
            json.dump(robot_data, t)
        print("Speed set to", float(speed_req.text))


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

    try:
        tree = ast.parse(file_content)
    except SyntaxError as e:
        print(f"Syntax error while parsing {file_path}: {e}")
        return []

    base_class_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            base_name = None
            for suffix in suffixes:
                if class_name.endswith(suffix):
                    potential_base = class_name[:-len(suffix)]
                    if potential_base:
                        base_name = potential_base
                        break
            if base_name:
                base_class_names.add(base_name)

    return sorted(base_class_names)

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
    parsed_url = urlsplit(url)
    filename = os.path.basename(parsed_url.path)
    filename = unquote(filename)

    filename = re.sub(r'(\.[A-Za-z0-9]+)[0-9a-f]{8,}$', r'\1', filename)

    os.makedirs(output_dir, exist_ok=True)
    local_filepath = os.path.join(output_dir, filename)

    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with open(local_filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
        print(f"File downloaded successfully: {local_filepath}")
        rospy.set_param("/attachment_path", local_filepath)
        
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
        return msg_content