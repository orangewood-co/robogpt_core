import sys
import time
import logging
import requests
import pysher
import hmac
import hashlib
import json


class PusherListenerSub:
    def __init__(self, app_id='1828565', app_key='7881fafa53083fd8c86b', 
                 app_secret='b016ae4c24ad125b4b58', cluster='ap2'):
        # Pusher app credentials
        self.app_id = app_id
        self.app_key = app_key
        self.app_secret = app_secret
        self.cluster = cluster
        
        # Setup logging
        self.setup_logging()
        
        # Initialize pusher client
        self.pusher = self.create_pusher_client()
        
    def setup_logging(self):
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        ch = logging.StreamHandler(sys.stdout)
        root.addHandler(ch)
    
    def create_pusher_client(self):
        # Create a custom pusher client that can handle private channels
        class CustomPusher(pysher.Pusher):
            def _generate_auth_token(self_pusher, channel_name):
                # Implementation for private channels
                if not self.app_secret:
                    raise ValueError("App secret is required for private channels")
                    
                socket_id = self_pusher.connection.socket_id
                
                string_to_sign = "{}:{}".format(socket_id, channel_name)
                signature = hmac.new(
                    self.app_secret.encode('utf8'),
                    string_to_sign.encode('utf8'),
                    hashlib.sha256
                ).hexdigest()
                
                return "{}:{}".format(self.app_key, signature)
        
        return CustomPusher(self.app_key, cluster=self.cluster)
    
    def callback_function(self, *args, **kwargs):
        print("MESSAGE AAYA BHAI")
        print("processing Args:", args)
        print("processing Kwargs:", kwargs)
    
    def connect_handler(self, data):
        channel = self.pusher.subscribe('private-chat')
        channel.bind('chatbox', self.callback_function)
    
    def start_listening(self):
        self.pusher.connection.bind('pusher:connection_established', self.connect_handler)
        self.pusher.connect()
        
        # Main event loop
        while True:
            # Do other things in the meantime here...
            time.sleep(1)


# Usage example
if __name__ == "__main__":
    listener = PusherListenerSub()
    listener.start_listening()