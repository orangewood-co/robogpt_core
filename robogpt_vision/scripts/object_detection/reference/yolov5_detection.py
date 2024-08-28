#!/usr/bin/env python3

import torch
import pyrealsense2 as rs
import numpy as np
import cv2
import rospy
from std_msgs.msg import String
import json
import os

# Path to your custom YOLOv5 weights file
custom_weights_path = '/home/ow-labs/workspaces/robogpt/robogpt-core/core/skills/vision_skills/object_detection/yolov5/runs/train/exp2/weights/best.pt'

# Load the custom YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'custom', path=custom_weights_path, force_reload=True, device ="cpu")

# Detection function using YOLOv5
def detect(image):
    results = model(image)
    detections = []
    for *xyxy, conf, cls in results.xyxy[0]:
        label = model.names[int(cls)]  # Get class name from custom model
        detections.append({'box_points': [int(xy) for xy in xyxy], 'confidence': conf.item(), 'class': label})
    return detections

current_directory_path = os.path.dirname(os.path.abspath(__file__))

# Commented out YOLOv3 initialization and ArUco marker related code

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()
rospy.init_node('owl_cv_detector', anonymous=False)
publisher = rospy.Publisher('/detected_objects', String, queue_size=10)

# Device configuration
pipeline_wrapper = rs.pipeline_wrapper(pipeline)
pipeline_profile = config.resolve(pipeline_wrapper)
device = pipeline_profile.get_device()
device_product_line = str(device.get_info(rs.camera_info.product_line))

found_rgb = False
for s in device.sensors:
    if s.get_info(rs.camera_info.name) == 'RGB Camera':
        found_rgb = True
if not found_rgb:
    print("The demo requires Depth camera with Color sensor")
    exit(0)
detections_array = []
detection_results = {}
i = 0

# Stream configuration
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 15)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 15)  # Adjust based on device_product_line if needed

pipeline.start(config)

try:
    while True:
        
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Object detection
        detections = detect(color_image)

        for detection in detections:
            
                # print(detection)
                # if detection["name"] in detections_array:
                #     print('No object detected')
                #     continue
            
            if detection['confidence'] > 0.40:
                    print("confidence is above 20")
                    box_corners = detections[0]['box_points']
                    cv2.rectangle(color_image, (box_corners[0], box_corners[1]), (box_corners[2], box_corners[3]), (0, 255, 0), 2)
                    cv2.rectangle(color_image, (detection["box_points"][0], detection["box_points"][1]), (detection["box_points"][2], detection["box_points"][3]), 0, 2, 0)
                        
                    center = (int((box_corners[0] + box_corners[2])/2), int((box_corners[1] + box_corners[3])/2))
                    center_pt = cv2.circle(color_image, center, 4, (0,0,255), -1)
                    cv2.putText(color_image, detection["class"], (detection["box_points"][0], detection["box_points"][1]), cv2.FONT_HERSHEY_COMPLEX, 1, 0, 2, 1)
                    

                    detection_result = {"detected_object": detection["class"], "confidence": detection["confidence"], "center_pt": center, "depth": int(depth_image[center[1], center[0]])}

                    s_no = "detection_" + str(i)
                    detection_results[s_no] = detection_result
                    i = i+1
        

        

        detection_result_json = json.dumps(detection_results)
                

        # Display the resulting frame
        cv2.imshow('frame', color_image)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cv2.destroyAllWindows()
    pipeline.stop()