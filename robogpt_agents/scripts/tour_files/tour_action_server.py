#!/usr/bin/env python3

import rospy
import actionlib
from robogpt_agents.msg import TourAction, TourFeedback, TourResult
from pick_n_place import Pick_N_Place_Tour

class TourActionServer:
    def __init__(self):
        self.server = actionlib.SimpleActionServer("tour_action", TourAction, self.execute, False)
        self.server.start()
        rospy.loginfo("Tour Action Server started!")

    def execute(self, goal):
        rospy.loginfo(f"Received tour request: {goal.tour_name}")

        if goal.tour_name.lower() == "pick_n_place":
            tour = Pick_N_Place_Tour()
            tour.script()
            success = True
            feedback = "Pick and Place Tour completed!"
        else:
            success = False
            feedback = "Invalid tour name!"

        result = TourResult()
        result.success = success
        self.server.set_succeeded(result, feedback)

if __name__ == "__main__":
    rospy.init_node("tour_action_server")
    server = TourActionServer()
    rospy.spin()
