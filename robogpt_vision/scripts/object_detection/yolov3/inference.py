import pyrealsense2 as rs
from imageai.Detection.Custom import CustomObjectDetection
from scipy.spatial.transform import Rotation as R

import numpy as np
import cv2
import rospy
from std_msgs.msg import String
import json
import numpy as np
import os

current_directory_path = os.path.dirname(os.path.abspath(__file__))


detector = CustomObjectDetection()
detector.setModelTypeAsYOLOv3()
detector.setModelPath(f"{current_directory_path}/owl_us_dataset/yolov3_img3_last.pt")
detector.setJsonPath(f"{current_directory_path}/owl_us_dataset/img3_yolov3_detection_config.json")
detector.loadModel() 

dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)

inst_matrix = np.array([[598.9801196 ,   0.       ,  323.39207771],   
                        [  0.     ,    597.93095386, 245.69899093],   
                        [  0.     ,      0.          , 1.        ]])
distortion = np.array([[[-3.51055369e-03 , 7.08338343e-01 , 1.42992349e-03 , 6.85005989e-05, -2.35099158e+00]]])

marker_lenth = 0.08 # m
objp = np.array([
    [-marker_lenth/2, -marker_lenth/2, 0],
    [-marker_lenth/2, marker_lenth/2, 0],
    [marker_lenth/2, marker_lenth/2, 0],
    [marker_lenth/2, -marker_lenth/2, 0]
])

detectorParams = cv2.aruco.DetectorParameters()
detector_aruco = cv2.aruco.ArucoDetector(dictionary, detectorParams)

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()
rospy.init_node('owl_cv_detector', anonymous=False)
publisher = rospy.Publisher('/detected_objects', String, queue_size=10)

# Get device product line for setting a supporting resolution
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

config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 15)

if device_product_line == 'L500':
    config.enable_stream(rs.stream.color, 960, 540, rs.format.bgr8, 15)
else:
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 15)

# Start streaming
pipeline.start(config)

try:
    while True:

        # Wait for a coherent pair of frames: depth and color
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        # Convert images to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # cropped_color_image = color_image
        # cropped_depth_image = depth_image

        cropped_color_image = color_image[0:332, ]
        cropped_depth_image = depth_image[0:332:, ]

        cropped_color_image_output = color_image[0:332, ]
        cropped_depth_image_output = depth_image[0:332:, ]


        detections = detector.detectObjectsFromImage(input_image=cropped_color_image)
        detections_array = []
        
        detection_results = {}
        i = 0

        warn_box_corner = [[168, 0], [421, 0], [421, 180], [168, 180]]

        
        corners, ids, _ = detector_aruco.detectMarkers(cropped_color_image_output, None, None)

        if ids is not None:
            try:
            
                cv2.aruco.drawDetectedMarkers(cropped_color_image_output, corners, ids, (0, 0, 0))
                
                nMarkers = len(corners)

                t = np.array([0.15, 0, 0])
                T, T1 = np.eye(4), np.eye(4)

                rvecs = np.zeros((nMarkers, 3))
                tvecs = np.zeros((nMarkers, 3))
                for i in range(nMarkers):
                    aruco_name = "box_" + str(ids[i][0])
                    cv2.solvePnP(objp, corners[i], inst_matrix, distortion, rvecs[i], tvecs[i])
                    rot = R.from_rotvec(rvecs[i])
                    T[:3, 3] = tvecs[i]
                    T1[:3, 3] = t
                    T[:3, :3] = rot.as_matrix()
                    Tnew = T@T1
                    tvecs[i] = Tnew[:3, 3]        
                    cv2.drawFrameAxes(cropped_color_image_output, inst_matrix, distortion, rvecs[i], tvecs[i], 0.1)                
                    
                    pixel_center = inst_matrix @ tvecs[i]
                    pixel_center /= pixel_center[2]
                    center = (int(pixel_center[0]), int(pixel_center[1]))
                    # print(center)
                    # center = (int((corners[i][0][0][0] + corners[i][0][1][0] + corners[i][0][2][0] + corners[i][0][3][0])/4), int((corners[i][0][0][1] + corners[i][0][1][1] + corners[i][0][2][1] + corners[i][0][3][1])/4))           
                    

                    detection_result = {"detected_object": aruco_name, "confidence": 100, "center_pt": center, "depth": int(cropped_depth_image_output[center[1], center[0]])}
                    s_no = "detection_" + str(i)
                    detection_results[s_no] = detection_result
                    i = i+1
            except Exception as e:
                print(e)
    

        for detection in detections:
            try:
                # print(detection)
                if detection["name"] in detections_array:
                    continue


                if detection["percentage_probability"] > 50:
                    detections_array.append(detection["name"])
                    cv2.rectangle(cropped_color_image_output, (detection["box_points"][0], detection["box_points"][1]), (detection["box_points"][2], detection["box_points"][3]), 0, 2, 0)
                    box_corners = detection["box_points"]
                                       
                    center = (int((box_corners[0] + box_corners[2])/2), int((box_corners[1] + box_corners[3])/2))
                    center_pt = cv2.circle(cropped_color_image_output, center, 4, (0,0,255), -1)
                    cv2.putText(cropped_color_image_output, detection["name"], (detection["box_points"][0], detection["box_points"][1]), cv2.FONT_HERSHEY_COMPLEX, 1, 0, 2, 1)

                    detection_result = {"detected_object": detection["name"], "confidence": detection["percentage_probability"], "center_pt": center, "depth": int(cropped_depth_image_output[center[1], center[0]])}
                    s_no = "detection_" + str(i)
                    detection_results[s_no] = detection_result
                    i = i+1

            except Exception as e:
                print(e)
            
        # draw rectangle for warn_box_corner
        cv2.rectangle(cropped_color_image_output, (warn_box_corner[0][0], warn_box_corner[0][1]), (warn_box_corner[2][0], warn_box_corner[2][1]), (0,0,255), 2, 0)

        print(detection_results)

        detection_result_json = json.dumps(detection_results)
        publisher.publish(detection_result_json)
        print("-------------")

        # # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
        # depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(cropped_depth_image, alpha=0.03), cv2.COLORMAP_JET)

        # depth_colormap_dim = depth_colormap.shape
        # color_colormap_dim = cropped_color_image.shape

        # # If depth and color resolutions are different, resize color image to match depth image for display
        # if depth_colormap_dim != color_colormap_dim:
        #     resized_color_image = cv2.resize(cropped_color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]), interpolation=cv2.INTER_AREA)
        #     images = np.hstack((resized_color_image, depth_colormap))
        # else:
        #     images = np.hstack((cropped_color_image, depth_colormap))

        # Show images

        cv2.namedWindow("owl_detector", cv2.WINDOW_FREERATIO)
        # cv2.resize("owl_detector", 1920, 1080)
        
        cv2.imshow('owl_detector', cropped_color_image_output)
        cv2.waitKey(1)

finally:

    # Stop streaming
    pipeline.stop()