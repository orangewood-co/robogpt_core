from azure.messaging.webpubsubclient import WebPubSubClient
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.identity import DefaultAzureCredential
import json,os,time
import datetime
# promt_string='wss://owl.webpubsub.azure.com/client/hubs/chat?access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJ3c3M6Ly9vd2wud2VicHVic3ViLmF6dXJlLmNvbS9jbGllbnQvaHVicy9jaGF0IiwiaWF0IjoxNjk1MTk2MDcyLCJleHAiOjE2OTUxOTk2NzJ9.tl2d3-C2tnEQerLPRtNYmJ_HrD87QXmHGcEeZxBHqCQ'
# client = WebPubSubClient(promt_string)
connection_string = 'Endpoint=https://owl.webpubsub.azure.com;AccessKey=0+zjxrouqD1voR0sYiJ69vaeLHFGH4iqurlYv0xM3Aw=;Version=1.0;'
logs=WebPubSubServiceClient.from_connection_string(connection_string, hub='log')
print('conected')
folder = datetime.datetime.now().strftime('log_%d_%m_%Y')
JSON_FILE=f'/home/ow-labs/workspaces/robotgpt_6_5/owl_robotgpt/logs/{folder}/robot_state.log'
#json read
last_modified = os.path.getmtime(JSON_FILE)
data=""
print("last:",last_modified)

while True:
    with open(JSON_FILE, 'r') as f:
        for line in f:
            data = line
        print(data)
    logs.send_to_all(message = data)
# with client:
#     def on_message(event):
#         print(event.data)
#         # answer=test_skill.agent_run(event.data)
#         # print(answer)  
#     client.on("server-message", on_message)
#     while True:
#         pass

