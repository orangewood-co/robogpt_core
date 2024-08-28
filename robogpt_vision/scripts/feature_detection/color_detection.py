import os, sys
import struct, json
import cv2 
import numpy as np
import time
from .utils.color_thief import ColorThief
from collections import namedtuple
from scipy.spatial.transform import Rotation as R
from multiprocessing import Process

class ColorDetection:
    """
    A class for color detection and object tracking in images.

    This class provides methods for color detection and object tracking in images. It includes functions to find the closest named color to an RGB value, extract objects from an image, and run color detection and tracking algorithms.

    Attributes:
        colors (list): A list of random color values.
        color_map (dict): A dictionary that maps color IDs to color names.
        named_colors (list): A list of named colors with their corresponding RGB values.

    Methods:
        euclidean_distance(color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float: 
            Calculate the Euclidean distance between two RGB colors.

        find_closest_color(rgb: Tuple[int, int, int]) -> str: 
            Find the closest named color in the provided RGB color space.

        extract_object(color_frame: np.ndarray, detection_results: Dict[str, Any]) -> List[np.ndarray]: 
            Extract objects from an image based on detection results.

        run(detection_results: Dict[str, Any], color_frame: np.ndarray, depth_frame: np.ndarray) -> Dict[str, Any]: 
            Run color detection and object tracking algorithms to analyze images and update detection results.

    """
    def __init__(self):
        NamedColor = namedtuple('NamedColor', ['name', 'rgb'])

        self.colors = np.random.randint(256, size=(24, 3)).tolist()
        self.color_map = {
                0:'black',
                1:'red',
                2:'brown',
                3:'yellow',
                4:'green',
                5:'blue',
                6:'purple',
                7:'unknown'
            }
        self.named_colors = [
            NamedColor('Red', (255, 0, 0)),
            NamedColor('Green', (0, 255, 0)),
            NamedColor('Blue', (0, 0, 255)),
            NamedColor('Yellow', (255, 255, 0)),
            NamedColor('Orange', (255, 165, 0)),
            NamedColor('Purple', (128, 0, 128)),
            NamedColor('Pink', (255, 192, 203)),
            NamedColor('Brown', (165, 42, 42)),
            NamedColor('Black', (0, 0, 0)),
            NamedColor('White', (255, 255, 255)),
            NamedColor('Cyan', (0, 255, 255)),
            NamedColor('Magenta', (255, 0, 255)),
            NamedColor('Lime', (0, 255, 0)),
            NamedColor('Teal', (0, 128, 128)),
            NamedColor('Navy', (0, 0, 128)),

        ]

    def euclidean_distance(self,color1, color2):
        """
        Calculate the Euclidean distance between two RGB colors.

        Args:
            color1 (Tuple[int, int, int]): RGB color value as a tuple.
            color2 (Tuple[int, int, int]): RGB color value as a tuple.

        Returns:
            float: Euclidean distance between the two colors.
        """
        return sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)) ** 0.5

    def find_closest_color(self,rgb):
        """
        Find the closest named color in the provided RGB color space.

        Args:
            rgb (Tuple[int, int, int]): RGB color value as a tuple.

        Returns:
            str: Name of the closest named color.
        """
        min_distance = float('inf')
        closest_color = None

        for named_color in self.named_colors:
            distance = self.euclidean_distance(rgb, named_color.rgb)
            if distance < min_distance:
                min_distance = distance
                closest_color = named_color.name

        return closest_color
    
    def extract_object(self,color_frame,detection_results):
        """
        Extract objects from an image based on detection results.

        Args:
            color_frame (np.ndarray): Color image frame.
            detection_results (Dict[str, Any]): Dictionary containing object detection results.

        Returns:
            List[np.ndarray]: List of extracted object images.
        """
        color_obj_list = []

        for result in detection_results.values():

            xymin = result["xyxy"][0]
            xymax = result["xyxy"][1]
            color_obj = color_frame[xymin[1]:xymax[1],xymin[0]:xymax[0]]

            color_obj_list.append(color_obj)

        return color_obj_list

    def run(self,detection_results,color_frame,depth_frame):
        """
        Run color detection and object tracking algorithms to analyze images and update detection results.

        The approach to find the color changes if color_detection is the first algorithm being run or is used somewhere between
        the list of algorithms. 

        Args:
            detection_results (Dict[str, Any]): Dictionary containing object detection results.
            color_frame (np.ndarray): Color image frame.
            depth_frame (np.ndarray): Depth image frame.

        Returns:
            Dict[str, Any]: Updated detection results with color information.
        """
        if bool(detection_results):
            ii = 0
            color_frame_list = self.extract_object(color_frame,detection_results)
            for bounding_color_image in color_frame_list:
                
                color_thief = ColorThief(bounding_color_image)
                dominant_rgb = color_thief.get_color(quality=1)

                color = self.find_closest_color(dominant_rgb)
                s_no = "detection_" + str(ii)
                detection_results[s_no]["color"] = color
                ii += 1

            return detection_results
        
        else:
            
            trackers = {}       # id -> tracker
            trackers_bbox = {}  # id -> tbbox
            trackers_color = {} # id -> color, life
            trackers_map = {}   # bbox id -> id
            trackers_life = {}
            t_id = 0
            ii = 0
            img = cv2.cvtColor(color_frame, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(color_frame, cv2.COLOR_BGR2HSV)

            img = cv2.GaussianBlur(img, (7,7), 1, img, 1)

            edge = cv2.Canny(img, 20, 120, apertureSize=3)
            cv2.morphologyEx(edge, cv2.MORPH_DILATE, (9,9), edge, iterations=3)

            contours, hierarchy = cv2.findContours(edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


            bboxes_raw = []
            rbboxes_raw = []
            for contour in list(contours):
                bboxes_raw.append(cv2.boundingRect(contour))
                rbboxes_raw.append(cv2.minAreaRect(contour))

            # area filter
            bboxes = []
            rbboxes = []
            for i, bbox in enumerate(bboxes_raw):
                # if bbox[2] * bbox[3] > 1500 and bbox[2] * bbox[3] < 22000:
                #     ratio = bbox[2] / bbox[3]
                #     if ratio > 1/3 and ratio < 3:
                bboxes.append(bbox)
                rbboxes.append(rbboxes_raw[i])
                
            # nms
            passid = []
            for i in range(len(bboxes)):
                bb1 = bboxes[i]
                center1 = (int(bb1[0] + bb1[2]/2), int(bb1[1] + bb1[3]/2))
                if (center1[0] < 30 or center1[0] > 640 - 30) or (center1[1] < 50 or center1[1] > 480 - 50):
                    passid.append(i)
                    continue

                for j in range(i+1, len(bboxes)):
                    bb2 = bboxes[j]
                    center2 = (int(bb2[0] + bb2[2]/2), int(bb2[1] + bb2[3]/2))
                    if (abs(center1[0] - center2[0]) < bb2[2] and abs(center1[1] - center2[1]) < bb2[3]):
                        passid.append(i)

            bboxes_fine = []
            rbboxes_fine = []
            for i, bbox in enumerate(bboxes):
                if i in passid:
                    continue
                bboxes_fine.append(bbox)
                rbboxes_fine.append(rbboxes[i])


            # color detection
            # color sample within rotatedrect
            object_colors = [-1 for _ in range(len(bboxes_fine))]
            for i, rbbox in enumerate(rbboxes_fine):
                poll = np.array([0,0,0,0,0,0,0,0])
                rbbox = cv2.boxPoints(rbbox)
                rbbox = np.int0(rbbox)

                tl = (int(bboxes_fine[i][0]), int(bboxes_fine[i][1]))
                br = (int(bboxes_fine[i][0]+bboxes_fine[i][2]), int(bboxes_fine[i][1]+bboxes_fine[i][3]))
                t = 0
                while t < 20:
                    xrand = np.random.randint(tl[0], br[0])
                    yrand = np.random.randint(tl[1], br[1])
                    if cv2.pointPolygonTest(rbbox, (xrand, yrand), True) >= 0:
                        t += 1
                        h, s, v = hsv[yrand, xrand]
                        b, g, r = color_frame[yrand, xrand]
                        
                        # black
                        if v < 50:
                            poll[0] += 1
                        elif h <= 10 or h > 165 and v > 120: # red
                            poll[1] += 1
                        elif h > 10 and h < 30: # Yellow
                            if v < 165:
                                poll[2] += 1 # Brown
                            else:
                                poll[3] += 1
                        elif h >= 30 and h <= 85: # Green
                            poll[4] += 1
                        elif h > 85 and h < 115: # blue
                            poll[5] += 1
                        elif h >= 115 and h < 150: # purple
                            poll[6] += 1
                        else:
                            poll[7] += 1
                
                color_id = np.argmax(poll)
                object_colors[i] = color_id
                # cv2.circle(image_copy, (xrand, yrand), 2, (0, 0, 255), 3)
                # cv2.putText(image_copy, '{} {} {}'.format(h, s, v), (xrand, yrand), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)
                # cv2.drawContours(image_copy, [rbbox], 0, (0, 255, 0), 2)
            remove_trackers = []
            for id, tracker in trackers.items():
                ret, nbbox = tracker.update(color_frame)
                if ret:
                    trackers_bbox[id] = nbbox
                else: # track failed
                    remove_trackers.append(id)
            for id in remove_trackers:
                trackers_bbox.pop(id)
                trackers.pop(id)
                trackers_color.pop(id)
                
            trackers_map = [-1 for _ in range(len(bboxes_fine))]
            for id1, bb1 in enumerate(bboxes_fine):
                mindis = 99999.0
                center1 = (int(bb1[0] + bb1[2]/2), int(bb1[1] + bb1[3]/2))
                match_success = False
                for id2, bb2 in trackers_bbox.items():
                    center2 = (int(bb2[0] + bb2[2]/2), int(bb2[1] + bb2[3]/2))
                    dis = ((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)**0.5
                    if dis < mindis:
                        mindis = dis
                        if dis < 80:
                            trackers_map[id1] = id2
                            match_success = True
                            trackers_life[id2] = 15
                            if object_colors[id1] != trackers_color[id2][0]:
                                trackers_color[id2][1] -= 1
                            else:
                                trackers_color[id2][1] = 3
                            if trackers_color[id2][1] == 0:
                                trackers_color[id2] = [object_colors[id1], 3]

                if not match_success:
                    trackers_map[id1] = t_id
                    trackers[t_id] = cv2.TrackerKCF_create()
                    trackers[t_id].init(color_frame, bb1)
                    trackers_life[t_id] = 15
                    trackers_color[t_id] = [object_colors[id1], 3]
                    t_id += 1

            remove_trackers = []
            for id in trackers.keys():
                if id not in trackers_map:
                    if trackers_life[id] > 0:
                        bb = trackers_bbox[id]
                        center = (int(bb[0] + bb[2]/2), int(bb[1] + bb[3]/2))

                        bboxes_fine.append(bb)
                        rbboxes_fine.append((center, (bb[2], bb[3]), 0.0))
                        trackers_map.append(id)
                        trackers_life[id] -= 1
                    else:
                        remove_trackers.append(id)
                        trackers_life.pop(id)

            for id in remove_trackers:
                trackers.pop(id)
                trackers_bbox.pop(id)
                trackers_color.pop(id)

            for i in range(len(bboxes_fine)):
                cls = self.color_map[trackers_color[trackers_map[i]][0]] + '_object'
                tl = (int(bboxes_fine[i][0]), int(bboxes_fine[i][1]))
                br = (int(bboxes_fine[i][0]+bboxes_fine[i][2]), int(bboxes_fine[i][1]+bboxes_fine[i][3]))
                center = (int((tl[0] + br[0]) / 2), int((tl[1] + br[1]) / 2))
                
                xmin, ymin, xmax, ymax = tl[0], tl[1], br[0], br[1]
                
                if 0 <= center[0] < depth_frame.shape[1] and 0 <= center[1] < depth_frame.shape[0]: #fix for index error
                    # depth1 = int(depth_copy[center[1], center[0]])
                    depth_min = np.min(depth_frame[ymin:ymax,xmin:xmax])
                    threshold = 0.8 * depth_min
                    mask = depth_frame >= threshold

                    # Step 4: Use the mask to filter the array and calculate the average
                    depth = int(np.mean(depth_frame[mask]))

                    # print(depth1, depth2)
                else:
                    depth = 700

                # Calculate area (assumption: area in pixel^2)
                area = bboxes_fine[i][2] * bboxes_fine[i][3]
                if np.isnan(depth_frame[ymin,xmin]):
                    zmin = depth
                else:
                    zmin = int(depth_frame[ymin,xmin])

                if np.isnan(depth_frame[ymax,xmax]):
                    zmax = depth
                else:
                    zmax = int(depth_frame[ymax,xmax])
                height = np.max(depth_frame[max(0,ymin-20):max(depth_frame.shape[0],ymax+20),max(0,xmin-20):max(depth_frame.shape[1],xmax+20)])

                detection_result = {
                    "detected_object": cls,
                    "confidence": 0.01, 
                    "center_pt": center, 
                    "depth": int(depth), 
                    "area": area,  # Add the area to the result
                    "xyxy":[[xmin,ymin,zmin],[xmax,ymax,zmax]],
                    "height":height
                }
                # print(detection_result)
                
                s_no = "detection_" + str(ii)
                detection_results[s_no] = detection_result
                ii += 1

            return detection_results
