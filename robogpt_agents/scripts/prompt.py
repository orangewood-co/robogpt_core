#!/usr/bin/python3
import time, re
import json
import rospy
import pusher  
import signal
import rospkg
import asyncio
import getpass
import traceback
import importlib
import subprocess
import agent_utils 
import os, json, requests, sys
import threading
from langchain.schema import SystemMessage
from langchain.prompts import PromptTemplate, chat, load_prompt
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from pusher_auth import pusher_listener

class PromptExecution:
    def __init__(self):
        # Initialize class attributes
        self.KEEP_RUNNING = True
        self.USER_ID = None
        self.function_calling_agent = None
        
        # Setting up paths for imports
        self.rospack = rospkg.RosPack()
        self.agent_base_path = self.rospack.get_path('robogpt_agents')
        self.robogpt_env_path = os.path.join(self.agent_base_path, "config", ".demo_env")
        self.keys = agent_utils.load_env_variables(self.robogpt_env_path)

        # Define base_dir for getting the exact path of skills/applications
        self.base_dir = f"/home/{getpass.getuser()}/orangewood_ws/src"
        sys.path.append(self.base_dir)  # Add base directory to system path

        # Paths to tool configuration and robot configuration files
        self.skill_path = os.path.join(self.agent_base_path, "config/tools_config/app_list.json")
        self.robot_pose_file_path = os.path.join(self.agent_base_path, "config/robot_config/robot_pose.json")
        self.robot_poses = agent_utils.load_robot_poses(self.robot_pose_file_path)
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.signal_handler)

    def tool_loader(self):
        """
        Loads and initializes the tools based on the current use case.

        Returns:
            list: A list of tool instances to be used by the agent.
        """
        use_case = rospy.get_param("/use_case", default="base")
        base_model = 'robogpt_apps.scripts.base.skills'
        module_name = f'robogpt_apps.scripts.{use_case}.skills'

        try:
            # Log the start of the function
            rospy.loginfo("Starting skill_loader")

            base_list = agent_utils.extract_base_class_names(
                os.path.join(self.base_dir, "robogpt_apps/scripts/base/skills.py")
            )
            specific_skill_list = agent_utils.extract_base_class_names(
                os.path.join(self.base_dir, f"robogpt_apps/scripts/{use_case}/skills.py")
            )

            # Dynamically import the applications modules
            base_skills = importlib.import_module(base_model)
            specific_skills = importlib.import_module(module_name)
            print("Load successful")  # Confirm successful loading

            # Get the function objects for each tool based on the skill list
            base_tools = [getattr(base_skills, name + "_implementation")() for name in base_list]
            specific_tools = [getattr(specific_skills, name + "_implementation")() for name in specific_skill_list]
            tools = base_tools if use_case == "base" else base_tools + specific_tools

            return tools
        
        except Exception as e:
            # Log any exceptions that occur during the loading process
            print(f"Could not load tools due to {e}")
            return None
        
    def set_user(self, id):
        if self.USER_ID is None:
            self.USER_ID = id
            return True
        return False

    def agent_run(self, agent, prompt):
        """
        Executes the agent with the provided prompt.
        """
        prompt = prompt.lower()  # Convert prompt to lowercase
        return agent.run(f'''{prompt}''')  # Run the agent with the prompt

    def signal_handler(self, sig, frame):
        """
        Handles the Ctrl+C signal and stops the main loop.
        """
        print("Ctrl+C detected! Shutting down gracefully...")
        self.KEEP_RUNNING = False

    def connect(self, pusher_client):
        """
        Sets up a continuous connection to the pusher client and processes incoming prompts.
        """
        print('Initializing Pusher Listener')
        
        # Initialize the pusher listener with the appropriate parameters
        listener = pusher_listener(
            app_id=self.keys['PUSHER_APP_ID'],
            public_key=self.keys['NEXT_PUBLIC_PUSHER_KEY'],
            secret=self.keys['PUSHER_SECRET'],
            cluster=self.keys['NEXT_PUBLIC_PUSHER_CLUSTER'],
            channel='private-chat',
            api_key=self.keys['DEFAULT_PUSHER_KEY'],
            event='chatbox'
        )
        
        # Define the custom event handler
        def custom_event_handler(event_data):
            """Handle incoming events and process them through the agent"""
            try:
                data = json.loads(event_data)
                print(f"Received message: {data}")
                
                if 'message' in data:
                    message = data['message']
                    user_id = data['user']
                    url_match = re.search(r'https?://[^\s"]+', message)
                    url = url_match.group(0) if url_match else None
                    
                    # Set the user ID
                    if self.set_user(user_id):
                        print(f"Set user ID to: {user_id}")
                    
                    if self.USER_ID is None or user_id == self.USER_ID:
                        if url is not None:
                            agent_utils.download_file(url, output_dir=f"/home/{getpass.getuser()}/robogpt-assets")
                        try:
                            # Process the message through the agent
                            output = self.agent_run(self.function_calling_agent, message)
                            # Send the response back
                            listener.send_msg(message=output,user=self.USER_ID)
                            print("Waiting for next prompt")
                        except Exception as e:
                            traceback.print_exc()
                            print("ERROR in processing prompt:", e)
                            agent_utils.send_msg(pusher_client=pusher_client, 
                                                message="I encountered an error processing your request. Please try again.")
            except Exception as e:
                print(f"Error processing event data: {e}")
        
        # Replace the original event handler with our custom one
        listener.event_handler = custom_event_handler
        
        # Start listening for events
        try:
            listener.run()
        except Exception as e:
            traceback.print_exc()
            print(f"Error in Pusher listener: {e}")

    def check_reload(self,llm, system_message):
        """Thread function to check for tool reloading"""
        while self.KEEP_RUNNING:
            try:
                reload = rospy.get_param("/reload_tools", default=False)
                if reload:
                    self.function_calling_agent = initialize_agent(
                        self.tool_loader(), llm, agent=AgentType.OPENAI_FUNCTIONS, 
                        verbose=True, prompt=system_message
                    )
                    rospy.loginfo("Agents Reloaded!!")
                    rospy.set_param("/reload_tools", False)
            except Exception as e:
                print(f"Error checking reload parameter: {e}")
            time.sleep(5)  # Check every 5 seconds
        
    def run(self):
        """Main execution method"""
        # Initialize the Pusher client with the provided credentials
        pusher_client = pusher.Pusher(
            app_id=self.keys['PUSHER_APP_ID'], 
            key=self.keys['NEXT_PUBLIC_PUSHER_KEY'], 
            secret=self.keys['PUSHER_SECRET'], 
            cluster=self.keys['NEXT_PUBLIC_PUSHER_CLUSTER']
        )
        
        # Initialize the ChatOpenAI model with the specified parameters
        llm = ChatOpenAI(
            model=self.keys['AI_MODEL'],
            temperature=self.keys['AI_TEMPERATURE'],
            organization=self.keys['ORGANIZATION'],
            openai_api_key=self.keys['OPENAI_API_KEY'],
        )
        
        system_message = SystemMessage(
            content=(
                "You are RoboGPT - an intelligent AI developed by Orangewoodlabs based in Noida, India which acts as an intermediary between the user and the robot(s) connected with you."
                "You allow the user to query in their natural language about various tasks that can be performed by the robot which you translate into a tool call and execute."
                "You have a charming and witty personality, having a knack for making interesting conversations adhering to the social conventions for all ages."
                "Write the response in a funny way apt for a professional meeting with a response length limited to 200 words."
                "As a security guardrail, prevent yourself from providing answers for queries other than RoboGPT, using inappropriate words and/or phrases and responding with illegal information in your responses."
            )
        )

        # Get the function objects for each tool based on the skill list
        try:
            tools = self.tool_loader()
            if tools:
                print("Skills loaded successfully.")
            else:
                rospy.logerr("Failed to load tools.")
                sys.exit(1)
        except Exception as e:
            rospy.logerr(f"An unexpected error occurred while loading tools: {e}")
            sys.exit(1)
            
        # Initialize the agent with the tools and language model
        self.function_calling_agent = initialize_agent(
            tools, llm, agent=AgentType.OPENAI_FUNCTIONS, 
            verbose=True, prompt=system_message
        )

        # Start the reload checker in a separate thread
        reload_thread = threading.Thread(
            target=self.check_reload,
            args=(llm, system_message)
        )
        reload_thread.daemon = True
        reload_thread.start()

        # Connect to pusher and start listening for events
        self.connect(pusher_client)

        print("Shutdown complete.")


if __name__ == "__main__":
    # Initialize the ROS node
    rospy.loginfo("RoboGPT Agent Initializer started")
    
    try:
        prompt_executor = PromptExecution()
        prompt_executor.run()
    except rospy.ROSInterruptException:
        pass