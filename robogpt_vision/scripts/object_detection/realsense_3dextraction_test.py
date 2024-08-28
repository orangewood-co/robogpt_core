import pyrealsense2 as rs
import numpy as np
import cv2
import time

# Function to measure processing time
def measure_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Processing Time: {end_time - start_time} seconds")
        return result
    return wrapper

# Check if CUDA is available
if not cv2.cuda.getCudaEnabledDeviceCount():
    print("CUDA device not found. Will use CPU instead.")
    use_cuda = False
else:
    print("CUDA device found. Using GPU.")
    use_cuda = True

# Initialize RealSense camera
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

@measure_time
def process_frame(color_image, depth_image):
    # Define initial mask based on depth data
    depth_threshold = 1000  # Depth threshold in millimeters
    initial_mask = np.where(depth_image < depth_threshold, 3, 2).astype('uint8')  # Foreground: 3, Background: 2

    # Initialize other GrabCut parameters
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)

    # Apply GrabCut
    cv2.grabCut(color_image, initial_mask, None, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_MASK)

    # Create masks for foreground and background
    foreground_mask = np.where((initial_mask == 2) | (initial_mask == 0), 0, 1).astype('uint8')
    background_mask = 1 - foreground_mask

    # Extract foreground and background
    foreground = color_image * foreground_mask[:, :, np.newaxis]
    background = color_image * background_mask[:, :, np.newaxis]

    return foreground, background

try:
    while True:
        # Capture frame from RealSense
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            continue

        # Convert frames to NumPy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Debugging
        print(f"Depth frame min value: {np.min(depth_image)}")
        print(f"Depth frame max value: {np.max(depth_image)}")

        # Processing frame (measuring time)
        foreground, background = process_frame(color_image, depth_image)

        # Display results
        cv2.imshow("Foreground", foreground)

        # Break loop with 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
