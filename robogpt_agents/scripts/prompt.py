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
import spacy



# import robogpt_v3.robogpt_agents.scripts.cloud_auth_and_llm.test_demo_skills as test_skill

nlp = spacy.load('en_core_web_md')

# Add your key, endpoint, and location
key = "4def1954ca074a149e643e2fb8fd9561"
endpoint = "https://api.cognitive.microsofttranslator.com"
location = "centralindia"
import subprocess
import pusher

## Pusher Credentials ##

app_id = "1828565"
key = "7881fafa53083fd8c86b"
secret = "b016ae4c24ad125b4b58"
cluster = "ap2"
###############################


pusher_client = pusher.Pusher(
    app_id=app_id, key=key, secret=secret, cluster=cluster)

###############################

# Json file paths
base_dir = f"/home/{os.getlogin()}/orangewood_ws/src"
sys.path.append(base_dir)

tool_path = os.path.join(base_dir,"robogpt_v3/robogpt_config/tools_config/app_list.json")
config_file = os.path.join(base_dir,"robogpt_v3/robogpt_config/robot_config/robogpt.json")
module_name = f'robogpt_apps.scripts.base_applications'


################################
def reload_bot_control():
    try:
        # Load the JSON file
        with open(tool_path) as f:
            data = json.load(f)

        # Retrieve the function names
        tool_names = data["apps"]

        # Importing the trivial skills
        applications = importlib.import_module(module_name)
        importlib.reload(applications)
        return applications, tool_names
    
    except Exception as e:
        print(f"Could not load skills due to {e}")

def local_prompt():
    output_file = os.path.join(base_dir,"robogpt_v3/robogpt_config/tools_config/output.json")
    command = "pusher channels apps subscribe --app-id 1828565 --channel private-chat"

    # Run the command and process the output
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    with open(output_file, "w") as f:
        for line in process.stdout:
            print(line)
            parts = line.split(":")
            # print(parts)
            if len(parts) > 2:
                subparts = parts[2].split('"')
                prompt = subparts[1]
                subid = parts[3].split('"')
                id = subid[1]
                print(prompt)
                
                return prompt , id

def send_msg(message):
    pusher_client = pusher.Pusher(
        app_id=app_id, key=key, secret=secret, cluster=cluster)

    pusher_client.trigger('private-chat', 'evt::test', {'message': message})

def set_speed_factor():
    # Construct the dynamic path to robogpt.json based on the current working directory
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
            # print(robot_data)
            robot_data["velocity_scaling"] = float(speed_req.text) / 100
        with open(robogpt_config, 'w') as t:
            json.dump(robot_data, t)
        print("Speed set to", float(speed_req.text))

def get_user_id(file_path):
    with open(file_path, 'r') as file:
            data = json.load(file)
    return data.get('user_id')

# Function to translate text to English
def translate_text(text_to_translate, to_language="en"):
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

    body = [{
        'text': text_to_translate
    }]

    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()

    if response and response[0]['translations']:
        return response[0]['translations'][0]['text']
    else:
        return None

def check_tool_list(tool_path):

    with open(tool_path) as f:
        data = json.load(f)

    tool_names = data["tools"]
    return tool_names


def agent_run(promt):
    print("prompt::::::", promt)
    
    return agent.run(f'''{promt}''') 

# Rest of your setup and WebSocket connection code
async def connect():
    print('Connected to WebPubSub')

    try:
            try:
                data,id  = local_prompt()
                output = agent_run(data)# data.rstrip('"'))
                print(output)
                send_msg(message=output)

            except Exception as e:
                print("ERROR in sending prompt", e)
                
        # You may want to remove the break below to keep the loop going

    except Exception as e:
        import traceback
        await connect()
        traceback.print_exc()
        print("Error:", e)
        # Reconnect or handle the error

llm = AzureChatOpenAI(
                deployment_name="robotgpt4-test", # The deployment name you chose when you deployed the GPT-35-Turbo or GPT-4 model.
                openai_api_base= "https://robotgpt4-test.openai.azure.com/",
                openai_api_key= "dded2f3a90864ab4a25e25a34cd70f5e",
                openai_api_type="azure",
                openai_api_version="2023-08-01-preview",
                temperature=0.7,
            )

old_number_of_tools = len(check_tool_list(tool_path=tool_path))

data = ""

# Reload the bot_control module
applications,skill_list = reload_bot_control()

# Get the function objects
tools = [getattr(applications, name + "_implementation")() for name in skill_list]

agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)

rospy.init_node("langchain_roboGPT")


while True:
    asyncio.get_event_loop().run_until_complete(connect())

