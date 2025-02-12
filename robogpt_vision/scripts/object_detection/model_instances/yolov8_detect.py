import torch
import ssl
import cv2
import math
import json
import time
import os
import numpy as np
import rospkg, rospy
from PIL import Image, ImageDraw, ImageFont
from transformers import pipeline
import struct
from ultralytics import YOLO
from scipy.stats import trim_mean



class YoloV8Detection:
    ''' Implements a fintuned yoloV5 model on custom weights.

    Attributes:
        detector : Zero shot model with Google's OWL-VIT pretrained weights

    Methods:
        extract_object(results,color_frame,depth_frame): Crops the color frame and depth frame based in the xyxy bounding box in results.
        detect_object(color_frame,depth_frame): Run zero shot detection algorithm on color frame and creates a detection_results dictionary
        make_single_prediction(color_frame,depth_frame): Returns the prediction with maximum confidence
        run(detection_results,color_frame,depth_frame): Main entry point of the class. Decides if make_single_prediction or detect_objects needs to be called, based on detection_results.
    '''

    def __init__(self):
        rospack = rospkg.RosPack()
        package_path = rospack.get_path('robogpt_vision')
        self.robogpt_config = os.path.join(package_path,"config/vision_config.json")
        self.weights_path = os.path.join(package_path,"scripts/object_detection/weights/veggies.pt")
        rospy.loginfo("Initiating YoloV8 Model")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = YOLO(self.weights_path).to(self.device)

    def parse_json_file(self,file_name):
        """
        Loads and returns the content of a JSON file.

        Args:
            file_name (str): The path to the JSON file to be parsed.

        Returns:
            dict: The content of the JSON file loaded into a dictionary.
        """
        with open(file_name, 'r') as f:
            return json.load(f)

    def extract_object(self, results, color_frame, depth_frame):
        ''' Crops the color frame and depth frame based on bounding box coordinates stored in results["xyxy"].

        Arguments:
            results (Dict): Dictionary containing the prediction results
            color_frame (np.array): Color image from camera
            depth_frame (np.array): Depth image from camera
        '''
        color_obj_list = []
        depth_obj_list = []

        for result in results.values():
            xymin = result["xyxy"][0]
            xymax = result["xyxy"][1]

            # Getting cropped images
            color_obj = color_frame[xymin[1]:xymax[1], xymin[0]:xymax[0]]
            depth_obj = depth_frame[xymin[1]:xymax[1], xymin[0]:xymax[0]]

            color_obj_list.append(color_obj)
            depth_obj_list.append(depth_obj)

        return color_obj_list, depth_obj_list

    def calculate_effective_depth(self, depth_values):
        ''' Currently uses to get the trimmed mean value of the depth. Applying different strategies soon.
        Agruments:
            depth_values: values of z coordinate of every pixel within the bounding box of the object detected
        '''
        # Remove NaN values
        depth_values = depth_values[~np.isnan(depth_values)]

        # Calculate the trimmed mean if there are enough depth values
        if len(depth_values) > 0:
            return int(trim_mean(depth_values, 0.25))  # Trim 25% from both ends
        else:
            return 0
        
    def read_new_weights(self,json_file):
        # Read the JSON data from the file
        with open(json_file, 'r') as file:
            data = json.load(file)
        
        # Return the value for the key 'new_weights'
        return data.get('new_weights')
    
    def clear_weights(self,file_path):

        with open(file_path, 'r') as file:
                data = json.load(file)
            
            # Update the value for the key 'new_weights'
        data['new_weights'] = ""
            
            # Write the updated JSON data back to the file
        with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)

    def detect(self, image):

        weights_path = self.read_new_weights(self.robogpt_config)
        # rospy.logwarn(weights_path)
        if weights_path != "":
            self.model = YOLO(weights_path).to(self.device)
            rospy.loginfo(f"New Weights detected. Using Weights from {weights_path}")
            self.clear_weights(self.robogpt_config)
        
        results = self.model(image)
        detections = []

        for result in results:
            boxes = result.boxes.xyxy
            class_ids = result.boxes.cls
            confidence_score = result.boxes.conf
            classes = result.names

            for i in range(len(boxes)):
                current_class = classes[int(class_ids[i])]
                current_confidence = float(confidence_score[i])
                current_box = [float(boxes[i][0]), float(boxes[i][1]), float(boxes[i][2]), float(boxes[i][3])]

                if current_class in ['body-lotion','coconut-oil', 'hair-gel','hair-serum','power','power-supply','lotion']:
                    if current_confidence < 0.3:
                        # Skip detections with confidence less than 0.7
                        continue
                # Check if current class is already present in detections
                class_found = False
                for detection in detections:
                    # print(f"{detection}\n\n")
                    if detection['class'] == current_class:
                        class_found = True
                        if current_confidence > detection['confidence']:
                            # Overwrite the existing detection
                            detection['confidence'] = current_confidence
                            detection['box_points'] = current_box
                        break

                if not class_found:
                    # If class not found, add new detection to detections
                    detections.append({
                        'class': current_class,
                        'confidence': current_confidence,
                        'box_points': current_box
                    })

        return detections


    def detect_objects(self, color_frame, depth_frame):
        detection_results = {}
        i = 0

        color_frame_copy = np.copy(color_frame)
        depth_frame_copy = np.copy(depth_frame)
        clm = depth_frame_copy.shape[1]
        row = depth_frame_copy.shape[0]

        # Converting numpy array to PIL image
        image = Image.fromarray(cv2.cvtColor(color_frame_copy, cv2.COLOR_BGR2RGB))

        # Object detection
        detections = self.detect(color_frame)

        for detection in detections:
            if detection['confidence'] < 0.3:
                continue

            xmin, ymin, xmax, ymax = map(int, detection['box_points'])
            # Convert indices to integers
            center = (int((xmin + xmax) / 2), int((ymin + ymax) / 2))  # Centre of bounding box
            area = abs(xmax - xmin) * abs(ymax - ymin)  # Area of bounding box

            # Getting depth at the center of the bounding box using depth_frame
            depth = 0
            if np.any(np.isnan(depth_frame_copy[ymin:ymax, xmin:xmax])):
                if 0 <= center[0] < clm and 0 <= center[1] < row:
                    depth = int(depth_frame_copy[center[1], center[0]])
                else:
                    print("WARNING: OBJECT NOT FOUND")
                    continue
            else:
                if 0 <= xmin < clm and 0 <= xmax < clm and 0 <= ymin < row and 0 <= ymax < row:
                    depth = int(depth_frame_copy[center[1], center[0]])
                else:
                    print("WARNING: OBJECT NOT FOUND")
                    continue

            # Handle zmin and zmax in a similar way as depth
            zmin = int(depth_frame_copy[ymin, xmin]) if not np.isnan(depth_frame_copy[ymin, xmin]) else depth
            zmax = int(depth_frame_copy[ymax, xmax]) if not np.isnan(depth_frame_copy[ymax, xmax]) else depth

            depth_values = depth_frame_copy[ymin:ymax, xmin:xmax].flatten()
            effective_depth = self.calculate_effective_depth(depth_values)

            # Extract the ROI for the color frame
            roi_color = color_frame_copy[ymin:ymax, xmin:xmax]
            roi_gray = cv2.cvtColor(roi_color, cv2.COLOR_BGR2GRAY)

            _, binary_mask = cv2.threshold(roi_gray, 160, 255, cv2.THRESH_BINARY)
            color_object = cv2.bitwise_and(roi_color, roi_color, mask=binary_mask)

            # Display the ROI in the "Current Object" window
            cv2.imshow("Current Object", roi_color)
            cv2.imshow("Current Object2", color_object)
            cv2.waitKey(1)

            # Storing results
            detection_result = {
                "detected_object": f"{detection['class']}",
                "confidence": f"{detection['confidence'] * 100}",
                "center_pt": center,
                "depth_at_center": depth,
                "area": area,
                "xyxy": [[xmin, ymin, zmin], [xmax, ymax, zmax]],
                "effective_depth": effective_depth
            }
            s_no = "detection_" + str(i)
            detection_results[s_no] = detection_result
            i += 1

        return detection_results

    def make_single_prediction(self, color_frame, depth_frame):
        ''' Returns the prediction with maximum confidence. Used when detection results already exist.

        Arguments:
            color_frame (np.array): Color image from camera
            depth_frame (np.array): Depth image from camera
        '''
        color_frame_copy = np.copy(color_frame)
        depth_frame_copy = np.copy(depth_frame)

        image = Image.fromarray(cv2.cvtColor(color_frame_copy, cv2.COLOR_BGR2RGB))
        max_prob = -np.inf
        predictions = self.detector(image, candidate_labels=["body-lotion","coconut-oil", "hair-gel","hair-serum"])
        best_label = None

        for prediction in predictions:
            if prediction["score"] > max_prob:
                best_label = prediction["label"]

        return best_label

    def run(self, detection_results, color_frame, depth_frame):
        ''' Main entry point. Calls appropriate function to use zero shot detection for object detection.

        Arguments:
            detection_results (Dict): Object detection results
            color_frame (np.array): Color image from camera
            depth_frame (np.array): Depth image from camera
        '''
        # If detection_results is not empty, make_single_prediction is used and detection_results is updated
        # if bool(detection_results):
        #     color_frame_list, depth_frame_list = self.extract_object(detection_results, color_frame, depth_frame)
        #     ii = 0
        #     for cl in range(len(color_frame_list)):
        #         best_label = self.make_single_prediction(color_frame_list[cl], depth_frame_list[cl])
        #         s_no = "detection_" + str(ii)
        #         if best_label is not None:
        #             detection_results[s_no]["detected_object"] = best_label
        #         ii += 1
        # else:
        detection_results = self.detect_objects(color_frame, depth_frame)

        return detection_results
