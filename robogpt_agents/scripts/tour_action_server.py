#!/usr/bin/env python3

import rospy
import actionlib
from tours import Guide
from robogpt_agents.msg import TourAction, TourFeedback, TourResult

class TourActionServer:
    def __init__(self):
        self.server = actionlib.SimpleActionServer("tour_action", TourAction, self.execute, False)
        self.server.start()
        rospy.loginfo("Tour Action Server started!")

    def execute(self, goal):
        rospy.loginfo(f"Received tour request: {goal.tour_name}")
        print("Loading guide")
        tour = Guide(goal.tour_name)
        print("Guide loaded")
        tour.information_flow()
        print("infro started")

if __name__ == "__main__":
    rospy.init_node("tour_action_server")
    server = TourActionServer()
    rospy.spin()
