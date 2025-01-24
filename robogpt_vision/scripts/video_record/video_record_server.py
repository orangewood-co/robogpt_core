#!/usr/bin/python3

import rospy
import actionlib
from robogpt_vision.msg import RecordCameraAction, RecordCameraFeedback, RecordCameraResult
from cam_record import VideoRecord

class RecordCameraActionServer:
    def __init__(self):
        self.server = actionlib.SimpleActionServer('record_camera', RecordCameraAction, self.execute_callback, False)
        self.server.start()
        rospy.loginfo("RecordCameraActionServer is ready.")

    def execute_callback(self, goal):
        feedback = RecordCameraFeedback()
        result = RecordCameraResult()

        try:
            rospy.loginfo(f"Starting recording: topic={goal.ros_topic}, file={goal.output_file}, duration={goal.duration}")
            vid_record = VideoRecord(goal.ros_topic, goal.output_file, goal.duration)
            vid_record.record_camera_feed()
            result.success = True
            result.video_path = "Recording completed successfully."
            self.server.set_succeeded(result)
        except Exception as e:
            result.success = False
            result.video_path = f"Recording failed: {e}"
            self.server.set_aborted(result)

if __name__ == '__main__':
    rospy.init_node('record_camera_action_server')
    server = RecordCameraActionServer()
    rospy.spin()
