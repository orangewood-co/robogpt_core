import os
import re

# Load the .env file path
dotenv_path =  'robogpt-webapp-latest/.env'

# Function to prompt the user for a single string input in the given format
def get_input_from_string():
    input_string = input('Enter the values in the format:\n'
                         '" app_id = "" key = "" secret = "" cluster = "" " :\n'
                        'Input: ')

    # Regular expressions to extract values from the input string
    app_id_match = re.search(r'app_id\s*=\s*"([^"]+)"', input_string)
    key_match = re.search(r'key\s*=\s*"([^"]+)"', input_string)
    secret_match = re.search(r'secret\s*=\s*"([^"]+)"', input_string)
    cluster_match = re.search(r'cluster\s*=\s*"([^"]+)"', input_string)

    if app_id_match and key_match and secret_match and cluster_match:
        return {
            'PUSHER_APP_ID': app_id_match.group(1),
            'PUSHER_SECRET': secret_match.group(1),
            'NEXT_PUBLIC_PUSHER_KEY': key_match.group(1),
            'NEXT_PUBLIC_PUSHER_CLUSTER': cluster_match.group(1)
        }
    else:
        raise ValueError("Invalid input format. Please follow the correct format.")

# Function to update the .env file manually
def update_env_file(new_values):
    with open(dotenv_path, 'r') as file:
        lines = file.readlines()

    with open(dotenv_path, 'w') as file:
        for line in lines:
            key = line.split('=')[0]
            if key in new_values:
                # Write updated key-value pair without quotes
                file.write(f"{key}={new_values[key]}\n")
            else:
                # Keep the existing line unchanged
                file.write(line)

# Main function to prompt user for either method
def main():
    choice = input("Choose input method: \n"
                   "1. Enter values individually\n"
                   "2. Enter values as a single string\n"
                   "Choice: ")

    if choice == '1':
        # Prompt user for individual values
        new_values = {
            'PUSHER_APP_ID': input("Enter PUSHER_APP_ID: "),
            'PUSHER_SECRET': input("Enter PUSHER_SECRET: "),
            'NEXT_PUBLIC_PUSHER_KEY': input("Enter NEXT_PUBLIC_PUSHER_KEY: "),
            'NEXT_PUBLIC_PUSHER_CLUSTER': input("Enter NEXT_PUBLIC_PUSHER_CLUSTER: ")
        }
    elif choice == '2':
        # Get values from a single string input
        new_values = get_input_from_string()
    else:
        print("Invalid choice. Exiting.")
        return

    # Update the .env file with the new values
    update_env_file(new_values)
    print("\n.env file has been updated.")

if __name__ == "__main__":
    main()
