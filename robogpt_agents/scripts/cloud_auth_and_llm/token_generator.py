import requests
import json
def get_connection_string():
    connection_string = requests.post(
        'https://robogpt.centralindia.cloudapp.azure.com/connectionstring', json={"password": "owl"}).json()["message"]
    print(connection_string)
    return connection_string


def get_client(robot, hub_name):

    client_string = requests.post(
        f'https://robogpt.centralindia.cloudapp.azure.com/{robot}/client/{hub_name}', json={"password": "owl"}).json()["message"]
    print(client_string)
    return client_string

def get_robot_info():
    with open('robot_data.json', 'r') as f:
        robos=requests.get('https://robogpt.centralindia.cloudapp.azure.com/list').json()
        robot_data = json.load(f)
        # if (robos["robots"]["robot_id"]==robot_data["robot_id"]):
        #     robot_data["name"]=robos["robots"]["name"]
        #     robot_data["version"]=robos["robots"]["version"]
        #     robot_data["ip"]=robos["robots"]["ip"]
        #     robot_data["description"]=robos["robots"]["description"]
        # else:
        #     print("Robot not found")
    return robot_data