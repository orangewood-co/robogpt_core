import logging
import os
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.identity import DefaultAzureCredential
import json

def get_client(hub_name):
    endpoint="https://orangewood.webpubsub.azure.com/" 
    client_aad = WebPubSubServiceClient(endpoint=endpoint, hub=hub_name,credential=DefaultAzureCredential())
    token_aad = client_aad.get_client_access_token()
    # print('token by AAD: {}'.format(token_aad))
    wss_url=(token_aad["url"])
    print(wss_url)
    return wss_url# Build a client through AAD# list_of_hubs=['Hub','chat','log']
