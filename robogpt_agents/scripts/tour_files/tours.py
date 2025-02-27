import sys
import os
import rospy
import rospkg
import openai
import subprocess
import pusher
import json
import re
import time

# Get package path and add it to sys.path
rospack = rospkg.RosPack()
agent_base_path = rospack.get_path('robogpt_agents')
sys.path.append(agent_base_path)
robogpt_env_path = os.path.join(agent_base_path, "config", ".demo_env")
import scripts.agent_utils as agu


TOUR_RUNNING = True

def load_keys(keys_path):
        """
        Reads the keys file and loads them into a dictionary.
        """
        keys = {}
        if not os.path.exists(keys_path):
            rospy.logerr("Keys file not found: {}".format(keys_path))
            sys.exit(1)
        
        with open(keys_path, 'r') as file:
            for line in file:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    keys[key] = value
        
        return keys
     
class Guide():
     def __init__(self, script_path):
          self.script_path = script_path
          self.user_steps = self.read_script()
          self.keys = agu.load_env_variables(robogpt_env_path)
          self.model = self.keys['AI_MODEL']
          self.end = False
          self.counter = 0
          self.pusher_client = pusher.Pusher(
                app_id=self.keys['PUSHER_APP_ID'],
                key=self.keys['NEXT_PUBLIC_PUSHER_KEY'],
                secret=self.keys['PUSHER_SECRET'],
                cluster=self.keys['NEXT_PUBLIC_PUSHER_CLUSTER']
            )
          
          openai.api_key = self.keys['OPENAI_API_KEY']

     def send_msg(self, pusher_client, message):
        """
        Sends a message to a specified Pusher channel.

        Args:
            pusher_client: The Pusher client instance.
            message (str): The message to send.
        """
        pusher_client.trigger('private-chat', 'evt::test', {'message': message})
          
     def read_script(self):
        with open(self.script_path, "r") as file:
            script = file.read()
        user_steps = script.split("\n")
        return user_steps
     
     def ai_formatted_msg(self, message: str) -> str:
        """
        Given an input message string, this method creates a prompt incorporating the current LLM model's name,
        sends the prompt to ChatOpenAI for rephrasing, and returns the formatted (rephrased) string.
        """
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"You are a helpful assistant, helping the user with the steps to follow. This is the RoboGPT tour and you are the tour guide. Keep the conversation interesting with a knack of wit and charm, adhering to the social conventions for all ages. Keep the response length limited and clear. Donot give these headsup on the dates of updated information. Please rephrase the following system message:\n\n {message}"}
                ]
            )
        return response['choices'][0]['message']['content']
     
     def format_steps(self):
         formatted_steps = []
         for i in self.user_steps:
            formatted_step = self.ai_formatted_msg(i)
            formatted_steps.append(formatted_step)
         return formatted_steps
     
     def steps(self, current_step, prompt):
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"You are a helpful assistant, helping the user following the tour steps i.e. \n{self.user_steps}\n If there is any issue the user is facing, help them solve that and if there are no challenges, respond in a positive manner. This is the current step to refer to \n{current_step}"},
                {"role": "user", "content": prompt}
                ]
            )
        return response['choices'][0]['message']['content']
     
     def step_tracker(self, current_step, system_response):
         response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"The system response is: {system_response}. "
                    f"The step we followed is: {current_step}. "
                    f"Determine if the step is successfully completed based on the system response. "
                    f"If there are any mentions of errors, troubleshooting, retries, or failures, respond with 'no'. "
                    f"If the system response confirms success or gives a positive acknowledgment, respond with 'yes'. "
                    f"Only respond with 'yes' or 'no', nothing else."}
                ]
            )
         return response['choices'][0]['message']['content']
     
     def get_prompt_response(self, app_id):
        command = f"pusher channels apps subscribe --app-id {app_id} --channel private-chat"

        # Execute the command to subscribe to the Pusher channel and process the output
        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        prompt = None
        system_response = None
        print("Inside get_prompt_response function")

        for line in process.stdout:
            print("Raw line in server:", line)  # Debug: print the raw line
                
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
            
            if "event=chatbox" in line:
                prompt = data.get("message", "")
            if "event=evt::test" in line:
                system_response = data.get("message", "")

            print(f"INSIDE THE FUNCTION, GET_PROMPT_RESPONSE\nfunc_prompt: {prompt}\nfunc_sys_response: {system_response}")
            return prompt, system_response
     
     
     def information_flow(self):
        formatted_steps = self.format_steps()
        agu.send_msg(pusher_client=self.pusher_client, message=formatted_steps[0])

        app_id = self.keys['PUSHER_APP_ID']

        while TOUR_RUNNING:
            prompt = None
            system_response = None

            while prompt is None and system_response is None:
                print("Inside second while loop")
                prompt, system_response = self.get_prompt_response(app_id)
                print(f"PROMPT: {prompt}\nSYSTEM RESPONSE: {system_response}")

    
            # for i in formatted_steps:
            #     step_response = self.steps(i, )

     

"""
- formatted step

- user input
- steps
- step_tracker
- yes -> formatted step | no -> print(resp = steps)

give first step when client is called (by the skill)

user :: prompt, evt::test
send_msg :: formatted_msg

if confirmation is no:
user :: prompt, evt::chatbox
confirmation response :: prompt, evt::test
send_msg :: user_qu
"""



# if __name__ == "__main__":
#      keys = load_keys("keys.txt")
#      guide = Guide(script_path="script.txt", keys=keys)

#      formatted_steps = guide.format_steps()

#      for i in formatted_steps:
#         print(f"RESPONSE: {i}")
#         user = input("USER: ")
#         user_qu = guide.steps(i, user)
#         print(f"STEPS RESPONSE: {user_qu}")
#         confirmation = guide.step_tracker(i, user_qu)
#         print(f"CONFIRMATION: {confirmation}")
#         whiluser = input("USER: ")
#              user_qu = guide.steps(i, user)
#              print(f"STEPS RESPONSE: {user_qu}")
#              confirmation = guide.step_tracker(i, user_qu)
#              print(f"CONFIRMATION: {confirmation}")e confirmation.strip().lower() == "no":
#              