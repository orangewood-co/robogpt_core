import cv2
import pyrealsense2 as rs
import numpy as np
from zero_shot import ZeroShotDetection

# Initialize the RealSense camera
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
pipeline.start(config)

# Create an instance of ZeroShotDetection
zero_shot_detector = ZeroShotDetection()

while True:
    # Capture color and depth frames from the camera
    frames = pipeline.wait_for_frames()
    color_frame = np.asanyarray(frames.get_color_frame().get_data())
    depth_frame = np.asanyarray(frames.get_depth_frame().get_data())

    # Call the run method to perform object detection
    detection_results = zero_shot_detector.run({}, color_frame, depth_frame)
    print(detection_results)

    # Process the detection results and draw bounding boxes
    for result in detection_results.values():
        label = result["detected_object"]
        xyxy = result["xyxy"]
        xmin, ymin, _, _ = xyxy[0]
        xmax, ymax, _, _ = xyxy[1]
        
        # Draw the bounding box on the color frame
        cv2.rectangle(color_frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
        cv2.putText(color_frame, label, (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Display the color frame with detected objects
    cv2.imshow("Zero Shot Detection", color_frame)

    # Break the loop on pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
pipeline.stop()
cv2.destroyAllWindows()
