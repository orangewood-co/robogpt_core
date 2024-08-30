import pusher
import cv2
import os
import json
import time
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import zipfile
import datetime
import logging
import os
# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=robogpt;AccountKey=mruQzxHY4fWb05Q9KWv9WpJfRUlD9bDg6G2GWBqkGg1F2We+k+EkwY0fhYe9CKB+SIHaPiGVuM2P+ASt8cTgng==;EndpointSuffix=core.windows.net"
AZURE_STORAGE_CONTAINER_NAME = "testing"

def set_logger():
    '''
    Configures and initializes two loggers for logging robot state and operation information. 
    It creates separate log files for each logger and sets up the log format.

    Returns:
    robotlogger (logging.Logger): A logger for robot state information.
    logger (logging.Logger): A logger for operation information.
    '''

    # Creates a folder in /log based on current date
    folder = datetime.datetime.now().strftime('log_%d_%m_%Y')
    os.makedirs(os.getcwd()+"/logs/"+folder, exist_ok=True)

    robotlogger = logging.getLogger("robot state")
    # Configure the log file and format for this script
    file_handler = logging.FileHandler(os.getcwd()+"/logs/"+folder+"/robot_state.log")
    formatter = logging.Formatter('%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    robotlogger.setLevel(logging.INFO)
    robotlogger.addHandler(file_handler)

    logger = logging.getLogger("operation")
    # Configure the log file and format for this script
    file_handler = logging.FileHandler(os.getcwd()+"/logs/"+folder+"/operation.log")
    formatter = logging.Formatter('%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
    logger.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return robotlogger,logger

robot_logger, opt_logger = set_logger()
def upload_image_to_azure(image, image_name):
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=AZURE_STORAGE_CONTAINER_NAME, blob=image_name)
    # Save the image temporarily
    temp_image_path = f"/tmp/{image_name}"
    cv2.imwrite(temp_image_path, image)
    # Upload the image
    with open(temp_image_path, "rb") as data:
        blob_client.upload_blob(data)
    # Remove the temporary image file
    os.remove(temp_image_path)
    # Return the URL of the uploaded image
    return blob_client.url

# def send_image_once(image):
#     # Generate a unique name for the image
#     image_name = f"image_{int(time.time())}.jpg"
#     # Upload the image to Azure Blob Storage
#     image_url = upload_image_to_azure(image, image_name)
#     # Send the image URL via Pusher
#     send_msg(image_url)
#     return image_url

def send_msg(message):
    """
    Send a message using Pusher.
    Args:
        message (str): The message to be sent.
    """
    try:
        app_id = "1828565"
        key = "7881fafa53083fd8c86b"
        secret = "b016ae4c24ad125b4b58"
        cluster = "ap2"
        pusher_client = pusher.Pusher(
            app_id=app_id, key=key, secret=secret, cluster=cluster)
        pusher_client.trigger('private-chat', 'evt::test', {'message': message})
    except Exception as e:
        print(f"Error sending message: {str(e)}")

def get_current_objects():

    detection_file = "config/owl/detection_results.json"  

    

    # Load detection results

    with open(detection_file, "r") as file:

        detection_results = json.load(file)

    objects = []

    # Extract object names

    for key, detections in detection_results.items():

        for detection_key, detection in detections.items():

            objects.append(detection["detected_object"])

    # Create a formatted string

    if not objects:

        return "No objects detected in the frame."

    

    unique_objects = set(objects)  # Remove duplicates if needed

    object_list_str = ", ".join(unique_objects)

    formatted_string = f"I see the following object(s) in the frame: {object_list_str}."

    return object_list_str


def get_skill_template():
    return '''
class {{ class_name }}_definition(BaseModel):
    object: str = Field(default = None, descrption = "the object or device to which robot needs to press button")
class {{ class_name }}_implementation(BaseTool):
    """Tool to tell the position of the object"""
    name = "{{ tool_name }}"
    description = "{{ tool_description }}"
    args_schema: Type[BaseModel] = {{ class_name }}_definition

    def _run(self, object:str = None):
        robot_ip = {{ robot_ip }}
        send_message_to_webapp_implementation()._run(message="Sure! I have instructed the robot to make popcorn")
'''

def extract_xml_from_zip(zip_path, extract_to_folder):
    """
    Extracts XML files from a given zip file into a subfolder named after the zip file.
    Saves their paths in a list.

    :param zip_path: Path to the zip file.
    :param extract_to_folder: Base folder where the files will be extracted.
    :return: A list of paths to the extracted XML files.
    """
    xml_paths = []  # To store paths of extracted XML files

    zip_file_name = os.path.basename(zip_path)  # Get the name of the zip file
    zip_file_name_without_ext = os.path.splitext(zip_file_name)[0]  # Remove the extension
    # Full path for the new subdirectory
    full_extract_path = os.path.join(extract_to_folder, zip_file_name_without_ext)

    # Create the subdirectory if it doesn't exist
    if not os.path.exists(full_extract_path):
        os.makedirs(full_extract_path)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Extract all files in the zip to the subdirectory
        zip_ref.extractall(full_extract_path)
        # Loop through the file names
        for file_name in zip_ref.namelist():
            # Check if the file is an XML
            if file_name.endswith('.xml'):
                # Save the full path of the extracted XML file
                xml_paths.append(os.path.join(full_extract_path, file_name))

    print("All the program files extracted")

    return xml_paths