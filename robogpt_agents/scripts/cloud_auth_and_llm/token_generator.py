import requests
import json
def get_connection_string():
    connection_string = requests.post(
        'https://robogpt.westus.cloudapp.azure.com/connectionstring',verify=False, json={"password": "owl"}).json()["message"]
    print(connection_string)
    return connection_string


def get_client(robot, hub_name):

    client_string = requests.post(
        f'https://robogpt.westus.cloudapp.azure.com/{robot}/client/{hub_name}',verify=False, json={"password": "owl"}).json()["message"]
    print(client_string)
    return client_string

def get_robot_info():
    with open('robot_data.json', 'r') as f:
        robos=requests.get('https://robogpt.westus.cloudapp.azure.com/list',verify=False).json()
        robot_data = json.load(f)
    return robot_data

