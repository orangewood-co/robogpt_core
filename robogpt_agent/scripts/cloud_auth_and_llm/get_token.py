import logging
import os
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.identity import DefaultAzureCredential
import json
# logging.basicConfig(level=logging.DEBUG)
# LOG = logging.getLogger()# Set the values of the client ID, tenant ID, and client secret of the AAD application as environment variables:
# WEBPUBSUB_CONNECTION_STRING='Endpoint=https://owl.webpubsub.azure.com;AccessKey=0+zjxrouqD1voR0sYiJ69vaeLHFGH4iqurlYv0xM3Aw=;Version=1.0;'# os.system('az login')
# os.system('azd auth login')
# credential = DefaultAzureCredential()
# WEBPUBSUB_ENDPOINT='https://owl.webpubsub.azure.com'
def get_client(hub_name):
    endpoint="https://orangewood.webpubsub.azure.com/" 
    client_aad = WebPubSubServiceClient(endpoint=endpoint, hub=hub_name,credential=DefaultAzureCredential())
    token_aad = client_aad.get_client_access_token()
    # print('token by AAD: {}'.format(token_aad))
    wss_url=(token_aad["url"])
    print(wss_url)
    return wss_url# Build a client through AAD# list_of_hubs=['Hub','chat','log']
# urls={}
# for i in list_of_hubs:
#     client_aad = WebPubSubServiceClient(endpoint=endpoint, hub=i, credential=DefaultAzureCredential())
#     token_aad = client_aad.get_client_access_token()
#     # print('token by AAD: {}'.format(token_aad))
#     urls[i]=(token_aad["url"])
#     #write this to a file
# with open('hub_urls.json', 'w') as outfile:
#     json.dump(urls, outfile)
#dump this token into a json file# # Build a client through connection string
# client_key = WebPubSubServiceClient.from_connection_string(connection_string, hub='hub')# # Build authentication token
# token_key = client_key.get_client_access_token()
# print('token by access key: {}'.format(token_key))