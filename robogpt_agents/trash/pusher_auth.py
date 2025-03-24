import logging
import re
import time
import json
import pysher  
import hmac
import hashlib
import pusher
# Set up logging. Uncomment this for debugging.
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# Create a custom Pusher client with authentication support
class AuthenticatedPusher(pysher.Pusher):
    def __init__(self, key, secret=None, cluster=None, **options):
        super().__init__(key, cluster=cluster, **options)
        self.secret = secret
        
    def authenticate(self, socket_id, channel_name):
        """Generate auth signature for private channels"""
        string_to_sign = "{}:{}".format(socket_id, channel_name)
        
        signature = hmac.new(
            bytes(self.secret, 'utf8'),
            bytes(string_to_sign, 'utf8'),
            hashlib.sha256
        ).hexdigest()
        
        auth_key = "{}:{}".format(self.key, signature)
        return json.dumps({"auth": auth_key})
    
    def _generate_auth_token(self, socket_id, custom_data=None):
        if not self.secret:
            raise Exception("Secret not set")
        
        if custom_data:
            string_to_sign = "{}:{}:{}".format(socket_id, self.channel_name, custom_data)
        else:
            string_to_sign = "{}:{}".format(socket_id, self.channel_name)
            
        signature = hmac.new(
            bytes(self.secret, 'utf8'),
            bytes(string_to_sign, 'utf8'),
            hashlib.sha256
        ).hexdigest()
        
        return "{}:{}".format(self.key, signature)

# Main class for listening from pusher
class pusher_listener():

    def __init__(self, app_id: str, public_key: str,secret:str, api_key: str, channel:str, event:str, cluster:str = "ap2") -> None:
        self.app_id = app_id
        self.public_key = public_key
        self.secret = secret
        self.cluster = cluster
        self.api_key = api_key
        self.channel_name = channel
        self.event_name = event
        self.msg = None
        self.user_id = None
        self.url = None

    def error_handler(self,data):
        """Handle Pusher errors"""
        print(f"Pusher Error: {data}")

    def send_msg(self,message,user):
        sender = pusher.Pusher(app_id=self.app_id, key=self.public_key, secret=self.secret, cluster=self.cluster)
        sender.trigger('private-chat', 'evt::test', {'message': message,'userId': user})

    def connect_handler(self,data):
        """Handle when we successfully connect to Pusher"""
        print("Connected to Pusher!")
        global client, channel
        
        data_dict = json.loads(data)
        socket_id = data_dict['socket_id']
        
        # For private channels, we need to handle authentication
        if self.channel_name.startswith('private-'):
            auth_data = client.authenticate(socket_id, self.channel_name)
            # Parse the JSON string to get the auth value
            auth_json = json.loads(auth_data)
            auth_token = auth_json['auth']
            channel = client.subscribe(self.channel_name, auth=auth_token)
        else:
            # Regular public channel subscription
            channel = client.subscribe(self.channel_name)
        
        print(f"Subscribed to channel: {self.channel_name}")
        
        # Bind to the specific events you want to listen for
        channel.bind(self.event_name, self.event_handler)
        print(f"Listening for {self.event_name} events...")

    def event_handler(self,event_data):
        """Handle incoming events"""
        try:
            data = json.loads(event_data)
            print(f"Parsed data: {data}")
            
            # Process the event based on its content
            if 'message' in data:
                self.msg = data['message']
                self.user_id = data['user']
                url_match = re.search(r'https?://[^\s"]+', data['message'])
                self.url = url_match.group(0) if url_match else None
        except:
            print("Event data is not in JSON format")
            return None
        

    # If you need to authenticate via the Pusher CLI
    def authenticate_with_cli(self):
        """Authenticate with Pusher CLI using your API key"""
        import subprocess
        
        cli_api_key = self.api_key
        result = subprocess.run(['pusher', 'login', '--key', cli_api_key], 
                            capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Successfully authenticated with Pusher CLI")
        else:
            print(f"Failed to authenticate: {result.stderr}")

    # Initialize a client to listen to events
    def run(self):
        global client
        # Create pusher client with your secret key
        client = AuthenticatedPusher(self.public_key, secret=self.secret, cluster=self.cluster)
        
        # Define what happens when connection is established
        client.connection.bind('pusher:connection_established', self.connect_handler)
        
        # Bind to error events
        client.connection.bind('pusher:error', self.error_handler)
        
        print("Connecting to Pusher...")
        # Connect
        client.connect()
        
        # # Keep the script running to continue listening for events
        while True:
            time.sleep(1)

