import cv2

def list_available_webcams():
    # Try to open video devices and list their names and indexes
    index = 0
    while True:
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            break
        ret, frame = cap.read()
        if ret:
            print(f"Webcam Index {index}: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
        cap.release()
        index += 1

if __name__ == "__main__":
    print("Available Webcams:")
    list_available_webcams()
