import asyncio
import argparse
import importlib
import websockets
import requests
import json
import uuid
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.identity import DefaultAzureCredential
from azure.messaging.webpubsubclient import WebPubSubClient
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.identity import DefaultAzureCredential
import websockets
import os,json,requests,sys
import spacy # type: ignore

parser = argparse.ArgumentParser(description='Run the prompt with a specific setup')
parser.add_argument('--setup', required=True, help='The setup to use for loading skills')
args = parser.parse_args()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import robogpt_agents.scripts.cloud_auth_and_llm as test_skill


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
config_file = "config/owl/robogpt.json"
tool_path = "config/owl/skill_list.json"

################################

def local_prompt():
    output_file = "config/owl/output.json"
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

old_number_of_tools = len(check_tool_list(tool_path=tool_path))
data = ""
# Rest of your setup and WebSocket connection code
async def connect():
    print('Connected to WebPubSub')

    try:

            try:
                new_tools = check_tool_list(tool_path=tool_path)
                if old_number_of_tools != new_tools:
                    importlib.reload(test_skill)
                else:
                    pass    
                data,id  = local_prompt()
                print(id)

                '''This is a hardcoded process for user identification but will be automated in future
                 You need to put the user key the in the if statement by taking it from console of web app
                 steps
                 1. open web app go to console copy the user id in the after sending some random msg
                 2. paste the id in user_id key in robogpt.json in config dir '''
                
                user_id = get_user_id(config_file)
                if id == user_id: # user key 
                    output = test_skill.agent_run(data)# data.rstrip('"'))
                    print(output)
                    send_msg(output)
                    print("Promt sent")

            except Exception as e:
                print("ERROR in sending prompt", e)
                await connect()
                pass
        # You may want to remove the break below to keep the loop going

    except Exception as e:
        import traceback
        await connect()
        traceback.print_exc()
        print("Error:", e)
        # Reconnect or handle the error

while True:
    asyncio.get_event_loop().run_until_complete(connect())
