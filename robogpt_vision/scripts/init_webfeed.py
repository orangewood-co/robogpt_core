#!/usr/bin/env python3
"""
ROS node for initializing and managing a webcam feed for web streaming.
Handles camera capture, performance monitoring, and publishing to ROS topics.
"""

import time
import rospy
from web_feed import WebcamStreamer, PerformanceMonitor # type: ignore

def main():
    """Initialize and run the webcam streaming node."""
    # Initialize ROS node
    rospy.init_node('web_feed_streamer', anonymous=True)
    
    # Configuration options (hardcoded as requested)
    TARGET_FPS = 30  # Adjust based on your needs
    QUALITY = 80
    RESIZE_FACTOR = 1.0
    BUFFER_SIZE = 2
    
    # Get ROS parameters
    WebImageTopic = rospy.get_param("/web_topic", default="web_feed")
    masking = rospy.get_param("/masking", default=False)
    if masking:
        WebImageTopic = "/masked_feed"
        
    rospy.loginfo(f"Starting webcam streamer with topic: {WebImageTopic}")
    
    # Initialize performance monitor and streamer
    monitor1 = PerformanceMonitor()
    streamer = WebcamStreamer(4, "upload1", WebImageTopic, TARGET_FPS, QUALITY, RESIZE_FACTOR, BUFFER_SIZE)
    
    # Start the streamer
    try:
        streamer.start()
        
        while not rospy.is_shutdown():
            monitor1.update()
            
            # Log FPS periodically
            current_time = time.time()
            if current_time % 5 < 0.1:  # Log approximately every 5 seconds
                fps = monitor1.get_fps()
                rospy.loginfo(f"Camera 1 FPS: {fps:.1f}")
            
            rospy.sleep(0.1)
            
    except KeyboardInterrupt:
        rospy.loginfo("Shutting down webcam streamer due to keyboard interrupt")
    except Exception as e:
        rospy.logerr(f"Error in webcam streamer: {e}")
    finally:
        streamer.stop()
        rospy.loginfo("Webcam streamer stopped")

if __name__ == "__main__":
    try:
        main()
    except rospy.ROSInterruptException:
        pass