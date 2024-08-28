import torch
import ssl
import cv2
import math
import json
import time
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from transformers import pipeline
import struct
from scipy.stats import trim_mean

class ZeroShotDetection:
    '''
    Implements a pretrained zero shot detection algorithm.

    Attributes:
        detector : Zero shot model with Google's OWL-VIT pretrained weights

    Methods:
        extract_object(results,color_frame,depth_frame):
            Crops the color frame and depth frame based in the xyxy bounding box in results. This is used, when a detection algorithm is used or we have detection results before running zero shot
        
        detect_object(color_frame,depth_frame):
            Run zero shot detection algorithm on color frame and creates a detection_results dictionary

        make_single_prediction(color_frame,depth_frame):
            Returns the prediction with maximum confidence
        
        run(detection_results,color_frame,depth_frame):
            Main entry point of the class. Decides if make_single_prediction or detect_objects needs to be called, based on detection_results. 

    '''
    def __init__(self):
        
        # Initialize the object detection model
        checkpoint = "google/owlvit-base-patch32"
        self.detector = pipeline(model=checkpoint, task="zero-shot-object-detection", device="cpu")

    def extract_object(self,results,color_frame,depth_frame):
        '''
        Crops the color frame and depth frame based on bounding box coordinates stored in results["xyxy"].

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
            color_obj = color_frame[xymin[1]:xymax[1],xymin[0]:xymax[0]]
            depth_obj = depth_frame[xymin[1]:xymax[1],xymin[0]:xymax[0]]

            color_obj_list.append(color_obj)
            depth_obj_list.append(depth_obj)

        return color_obj_list,depth_obj_list
    

    def calculate_effective_depth(self, depth_values):
        '''
        Currently uses to get the trimmed mean value of the depth.
        Applying different stratergies soon.

        Agruments:
            depth_values: values of z coordinate of every pixel within 
                            the bounding box of the object detected
        '''
        # Remove NaN values
        depth_values = depth_values[~np.isnan(depth_values)]

        # Calculate the trimmed mean if there are enough depth values
        if len(depth_values) > 0:
            return int(trim_mean(depth_values, 0.25))  # Trim 25% from both ends
        else:
            return 0
    
    def detect_object(self,color_frame,depth_frame):
        '''
        Used to detect objects from color_frame and depth_frame based on objects of interest.

        Arguments:
            color_frame (np.array): Color image from camera
            depth_frame (np.array): Depth image from camera
        '''
        detection_results = {}

        color_frame_copy = np.copy(color_frame)
        depth_frame_copy = np.copy(depth_frame)
        i = 0
        clm = depth_frame_copy.shape[1]
        row = depth_frame_copy.shape[0]
        
        # Converting numpy array to PIL image
        image = Image.fromarray(cv2.cvtColor(color_frame_copy, cv2.COLOR_BGR2RGB))

        # Loading the objects of interest from JSON
        f = open(os.path.join(os.getcwd(),"config/owl/robogpt.json"))
        candidate_labels = json.load(f)["objects_to_detect"]
        f.close()

        # Making predictions
        predictions = self.detector(image, candidate_labels=candidate_labels)
        cv2.namedWindow("Current Object", cv2.WINDOW_NORMAL)
        for prediction in predictions:
            
            box = prediction["box"]
            if prediction['score'] < 0.16:
                continue

            xmin, ymin, xmax, ymax = box.values()
            
            center = (int((xmin+xmax)/2), int((ymin+ymax)/2)) # Centre of bounding box
            area = abs(xmax-xmin)*abs(ymax-ymin) # Area of bounding box

            # Getting depth at center of bounding box using depth_frame        
            depth = 0
            if np.any(np.isnan(depth_frame_copy[ymin:ymax,xmin:xmax])):
                if 0 <= center[0] < clm and 0 <= center[1] < row: 
                    depth = int(depth_frame_copy[center[1],center[0]])
                else:
                    print("WARNING : OBJECT NOT FOUND")
                    continue
            else:
                if 0 <= xmin < clm and 0 <= xmax < clm and 0 <= ymin < row and 0 <= ymax < row: 
                    depth = int(depth_frame_copy[center[1],center[0]])
                else:
                    print("WARNING : OBJECT NOT FOUND")
                    continue
            # print(probs)
            
            if np.isnan(depth_frame_copy[ymin,xmin]):
                zmin = depth
            else:
                zmin = int(depth_frame_copy[ymin,xmin])

            if np.isnan(depth_frame_copy[ymax,xmax]):
                zmax = depth
            else:
                zmax = int(depth_frame_copy[ymax,xmax])
            
            depth_values = depth_frame_copy[ymin:ymax, xmin:xmax].flatten()

            # Remove NaN values
            depth_values = depth_values[~np.isnan(depth_values)]

            effective_depth = self.calculate_effective_depth(depth_values)

            #Calculating the height of object
            # height = int(np.max(depth_frame_copy[max(0,ymin-20):min(depth_frame_copy.shape[0],ymax+20),max(0,xmin-20):min(depth_frame_copy.shape[1],xmax+20)]))
 
            # Extract the ROI for the color frame
            roi_color = color_frame_copy[ymin:ymax, xmin:xmax]
            roi_gray = cv2.cvtColor(roi_color, cv2.COLOR_BGR2GRAY)

            _, binary_mask = cv2.threshold(roi_gray, 160, 255, cv2.THRESH_BINARY)
            color_object = cv2.bitwise_and(roi_color, roi_color, mask=binary_mask)

            # Display the ROI in the "Current Object" window
            cv2.imshow("Current Object", roi_color)
            cv2.imshow("Current Object2", color_object)


            cv2.waitKey(1)

            #Storing results
            detection_result = {"detected_object": f"{prediction['label']}", "confidence": 100, "center_pt": center, "depth_at_center": depth,"area":area,"xyxy":[[xmin,ymin,zmin],[xmax,ymax,zmax]], "effective_depth": effective_depth}
            s_no = "detection_" + str(i)
            detection_results[s_no] = detection_result
            i = i+1

        return detection_results
    
    def make_single_prediction(self,color_frame,depth_frame):
        '''
        Returns the prediction with maximum confidence. Used when detection results already exist.

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
    
    def run(self,detection_results,color_frame,depth_frame):
        '''
        Main entry point. Calls appropriate function to use zero shot detection for object detection.

        Arguments:
            detection_results (Dict): Object detection results
            color_frame (np.array): Color image from camera
            depth_frame (np.array): Depth image from camera
        '''

        # If detection_results is not empty, make_single_prediction is used and detection_results is updated
        if bool(detection_results):
            color_frame_list,depth_frame_list = self.extract_object(detection_results,color_frame,depth_frame)
            ii = 0
            for cl in range(len(color_frame_list)):

                best_label = self.make_single_prediction(color_frame_list[cl],depth_frame_list[cl])
                s_no = "detection_" + str(ii)
                if best_label is not None:
                    detection_results[s_no]["detected_object"] = best_label
                ii += 1
        else:
            detection_results = self.detect_object(color_frame,depth_frame)

        return detection_results