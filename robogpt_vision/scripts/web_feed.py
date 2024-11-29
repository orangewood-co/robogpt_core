#!/usr/bin/env python3

import cv2
import time
import queue
import rospy
import struct
import requests
import numpy as np
from threading import Thread
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError


CLOUD_SERVER = "https://janatics.video.api.orangewood.co"


class WebcamStreamer:
    def __init__(self, type, camera_id, endpoint, target_fps=30, quality=70,
                 resize_factor=1.0, buffer_size=2):

        rospy.init_node("Web_App_Feed_Node")
        self.type = type
        self.camera_id = camera_id
        if self.type == "live":
            self.camera = cv2.VideoCapture(camera_id)

        self.endpoint = endpoint
        self.running = True
        self.quality = quality
        self.resize_factor = resize_factor
        self.target_fps = target_fps
        self.frame_time = 1 / target_fps
        self.bridge = CvBridge()

        # Setting the ros parameters 
        self.cam_name = rospy.get_param("/Object_detection_node/camera_name",default="camera")
        self.image_sub = rospy.Subscriber(f"/{self.cam_name}_frame", Image, self.color_callback)
        self.color_frame = None

        # Frame sending queue and thread
        self.send_queue = queue.Queue(maxsize=buffer_size)
        self.send_thread = Thread(target=self._send_frames, daemon=True)
        self.send_thread.start()

        self.heartbeat_thread = Thread(
            target=self._send_heartbeat, daemon=True)
        self.heartbeat_thread.start()

    def color_callback(self, data):
        try:
            # Convert the ROS Image message to OpenCV format
            self.color_frame = self.bridge.imgmsg_to_cv2(data, "bgr8")

        except CvBridgeError as e:
            print(e)

    def _send_frames(self):
        session = requests.Session()
        while self.running:
            try:
                frame_data = self.send_queue.get(timeout=1.0)
                session.post(f"{CLOUD_SERVER}/{self.endpoint}",
                             files={"frame": frame_data})
            except queue.Empty:
                continue
            except requests.RequestException as e:
                print(f"Error sending frame to {self.endpoint}: {e}")
                time.sleep(0.1)

    def _send_heartbeat(self):
        session = requests.Session()
        while self.running:
            try:
                # Send heartbeat every 5 seconds
                session.post(f"{CLOUD_SERVER}/heartbeat",
                             json={"camera_id": self.camera_id})
            except requests.RequestException as e:
                print(f"Error sending heartbeat: {e}")
            time.sleep(5)

    def stop(self):
        self.running = False
        self.camera.release()
        # Send final status update
        try:
            requests.post(f"{CLOUD_SERVER}/heartbeat",
                          json={"camera_id": self.camera_id, "status": False})
        except requests.RequestException:
            pass

    def stream(self):
        last_frame_time = time.time()

        while self.running:
            current_time = time.time()
            if current_time - last_frame_time < self.frame_time:
                continue

            if self.type == "detection":
                if self.color_frame is not None:
                    frame = self.color_frame

                    # Resize if needed
                    if self.resize_factor != 1.0:
                        new_size = (int(frame.shape[1] * self.resize_factor),
                                    int(frame.shape[0] * self.resize_factor))
                        frame = cv2.resize(frame, new_size)

                    # Encode frame with specified quality
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
                    _, img_encoded = cv2.imencode('.jpg', frame, encode_param)

                    # Try to add to queue, skip frame if queue is full
                    try:
                        self.send_queue.put(img_encoded.tobytes(), block=False)
                    except queue.Full:
                        pass

                    last_frame_time = current_time

            elif self.type == "live":

                ret, frame = self.camera.read()
                if ret:
                    # Resize if needed
                    if self.resize_factor != 1.0:
                        new_size = (int(frame.shape[1] * self.resize_factor),
                                    int(frame.shape[0] * self.resize_factor))
                        frame = cv2.resize(frame, new_size)

                    # Encode frame with specified quality
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
                    _, img_encoded = cv2.imencode('.jpg', frame, encode_param)

                    # Try to add to queue, skip frame if queue is full
                    try:
                        self.send_queue.put(img_encoded.tobytes(), block=False)
                    except queue.Full:
                        pass

                    last_frame_time = current_time
                

    def start(self):
        Thread(target=self.stream, daemon=True).start()

    def stop(self):
        self.running = False
        self.camera.release()

# Performance monitoring class


class PerformanceMonitor:
    def __init__(self, window_size=30):
        self.frame_times = []
        self.window_size = window_size
        self.last_time = time.time()

    def update(self):
        current_time = time.time()
        self.frame_times.append(current_time - self.last_time)
        self.last_time = current_time

        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)

    def get_fps(self):
        if not self.frame_times:
            return 0
        return len(self.frame_times) / sum(self.frame_times)


if __name__ == "__main__":

    # Configuration options

    TARGET_FPS = 30  # Adjust based on your needs
    QUALITY = 80
    RESIZE_FACTOR = 1.0
    BUFFER_SIZE = 2

    monitor1 = PerformanceMonitor()


    streamer = WebcamStreamer("detection", 4, "upload1", TARGET_FPS, QUALITY, RESIZE_FACTOR, BUFFER_SIZE)
    streamer.start()

    try:
        while True:
            monitor1.update()

            if time.time() % 5 < 0.1:  # Print every 5 seconds
                print(f"Camera 1 FPS: {monitor1.get_fps():.1f}")
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        streamer.stop()
