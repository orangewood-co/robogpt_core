
from langchain.chains import LLMChain, SimpleSequentialChain
from langchain.prompts import PromptTemplate, chat, load_prompt
from langchain.llms import OpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI

import rospy
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType

from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.llms import AzureOpenAI

import os, sys, importlib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trivial_skills.owl.bot_control import *
from core.vision_skills.owl.get_world_context import *
from core.vision_skills.owl.get_aruco_context import *

import json
from langchain.callbacks.stdout import StdOutCallbackHandler
from langchain.chat_models.openai import ChatOpenAI
from langchain.prompts.prompt import PromptTemplate
import argparse

parser = argparse.ArgumentParser(description='Run the script with a specific setup')
parser.add_argument('--setup', required=True, help='The setup to use for loading skills')
args = parser.parse_args()

def reload_bot_control(setup):
    try:
        module_name = f'core.trivial_skills.{setup}.bot_control'
        tool_path = f'config/{setup}/skill_list.json'

        # Load the JSON file
        with open(tool_path) as f:
            data = json.load(f)

        # Retrieve the function names
        tool_names = data["tools"]

        # Importing the trivial skills
        bot_control = importlib.import_module(module_name)
        importlib.reload(bot_control)
        return bot_control, tool_names
    
    except Exception as e:
        print(f"Could not load skills due to {e}")


# Reload the bot_control module
bot_control,tool_names = reload_bot_control(args.setup)

# Get the function objects
tools = [getattr(bot_control, name + "_implementation")() for name in tool_names]


llm = AzureChatOpenAI(
                deployment_name="robotgpt4-test", # The deployment name you chose when you deployed the GPT-35-Turbo or GPT-4 model.
                openai_api_base= "https://robotgpt4-test.openai.azure.com/",
                openai_api_key= "dded2f3a90864ab4a25e25a34cd70f5e",
                openai_api_type="azure",
                openai_api_version="2023-08-01-preview",
                temperature=0.7,
            )

# tools = [set_robot_ip_implementation(),displace_object_implementation(),move_translate_implementation(), stacking_implementation(),pick_and_place_implementation(),get_pose_implementation(), get_zone_pose_implementation(), zone_selection_implementation(), move_to_pose_implementation(), ximg2xbase_implementation(), check_prompt_implementation(),aruco_img_2_base_implementation(),auto_train_implementation(),hand_teach_implementation(),create_skill_implementation(), switch_lamp_implementation()]

agent = initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=True)

rospy.init_node("langchain_roboGPT")

def agent_run(promt):
    print("prompt::::::", promt)
    
    return agent.run(f'''{promt}''') 

if __name__=="__main__":
    set_robot_ip_implementation()._run(robot_ip_list=["10.42.0.53"])

