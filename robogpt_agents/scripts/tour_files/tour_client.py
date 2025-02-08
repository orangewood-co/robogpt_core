#!/usr/bin/env python3

import rospy
import actionlib
from robogpt_agents.msg import TourAction, TourGoal

def call_tour(tour_name):
    rospy.init_node("tour_action_client")
    client = actionlib.SimpleActionClient("tour_action", TourAction)
    
    rospy.loginfo("Waiting for server...")
    client.wait_for_server()

    goal = TourGoal()
    goal.tour_name = tour_name

    rospy.loginfo(f"Sending tour request: {tour_name}")
    client.send_goal(goal)

    # client.wait_for_result()
    # result = client.get_result()
    # rospy.loginfo(f"Tour Success: {result.success}")

if __name__ == "__main__":
    tour_name = "pick_n_place"  # Change as needed
    call_tour(tour_name)
