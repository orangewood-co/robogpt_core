#!/usr/bin/env python3

import rospy
from robogpt_vision.srv import GetWorldContext, GetWorldContextRequest
import sys

def call_get_world_context_service(object_name, parent_frame):
    rospy.wait_for_service('get_world_context')
    try:
        get_world_context = rospy.ServiceProxy('get_world_context', GetWorldContext)
        
        req = GetWorldContextRequest()
        req.object_name = object_name
        req.parent_frame = parent_frame
        resp = get_world_context(req)
        
        print(f"Received transformation in base frame: {resp.Xbase}")
    except rospy.ServiceException as e:
        print(f"Service call failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: call_service.py <object_name> <parent_frame>")
        sys.exit(1)
    
    object_name = sys.argv[1]
    parent_frame = sys.argv[2]
    
    rospy.init_node('call_get_world_context_service_node')
    
    call_get_world_context_service(object_name, parent_frame)
