import os
import rospkg
import dotenv

rospack = rospkg.RosPack()
path = rospack.get_path("robogpt_agents")
env_path = os.path.join(path,"config",".robogpt_env")
PUSHER_APP_ID=None
OPENAI_API_KEY=None

def load_env_variables(env_file):
    # Load the environment variables from the .env file into os.environ
    dotenv.load_dotenv(env_file)
    
    # Extract the environment variables from the .env file dynamically
    env_vars = {}
    with open(env_file, 'r') as file:
        for line in file:
            # Skip comments and blank lines
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                env_vars[key] = value
                os.environ[key] = value  # Set the environment variables
    
    # Return the environment variables as a dictionary
    return env_vars

# Specify your .env file path
env = load_env_variables(env_path)

# Now, all environment variables are accessible as variables
print(env['PUSHER_APP_ID'])  # Example of accessing one of the variables
print(OPENAI_API_KEY)  # Another example
