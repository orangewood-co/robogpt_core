#!/usr/bin/python3

import rospy
import actionlib
from robogpt_vision.msg import RecordCameraAction, RecordCameraGoal

def record_camera_client(ros_topic, output_file, duration):
    client = actionlib.SimpleActionClient('record_camera', RecordCameraAction)
    rospy.loginfo("Waiting for action server...")
    client.wait_for_server()

    goal = RecordCameraGoal()
    goal.ros_topic = ros_topic
    goal.output_file = output_file
    goal.duration = duration

    rospy.loginfo(f"Sending goal: topic={ros_topic}, file={output_file}, duration={duration}")
    client.send_goal(goal)
    # client.wait_for_result()

    result = client.get_result()
    if result.success:
        rospy.loginfo(f"Recording succeeded: {result.video_path}")
    else:
        rospy.logerr(f"Recording failed: {result.video_path}")

if __name__ == '__main__':
    rospy.init_node('record_camera_client')
    record_camera_client('/cv_camera_node/image_raw', 'output.mp4', 10)
