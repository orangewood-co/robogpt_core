import cv2
import numpy as np
"""
Setting the reference image is necessary for proper usage of ObjectDetector.
For setting it, press 'r' by directing camera(preferably) towards an plain empty surface.
"""
class ObjectDetector:
    def __init__(self, boundary_rect=(490, 200, 300, 300)):
        """
        Initializes the ObjectDetector with video capture and a detection boundary.
        boundary_rect is set to (490, 200, 300, 300) by default. Can be changed to whatever the user wants.
        """
        self.boundary_rect = boundary_rect
        self.cap = cv2.VideoCapture(4)
        self.reference_gray = None  # Placeholder for reference background

        # Capture initial reference background
        ret, reference_frame = self.cap.read()
        if ret:
            self.reference_gray = self.preprocess_frame(reference_frame)
        else:
            print("Error: Could not capture reference frame.")

    def preprocess_frame(self, frame):
        """
        Convert frame to grayscale and apply Gaussian blur.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (21, 21), 0)

    def detect_objects(self, frame):
        """
        Detects objects in the frame by comparing it with the reference background.
        Returns:
            - object_detected: Boolean indicating if an object is found.
            - processed_frame: Frame with boundary and text.
        """
        if self.reference_gray is None:
            return False, frame, frame

        # Preprocess current frame
        gray = self.preprocess_frame(frame)

        # Compute absolute difference between current frame and reference
        frame_diff = cv2.absdiff(self.reference_gray, gray)
        _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)  # Fill small gaps

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Default settings
        boundary_color = (0, 0, 255)
        object_detected = False
        detected_frame = frame.copy()  # Copy for saving

        # Check if any contour is inside the boundary
        x, y, w, h = self.boundary_rect
        for cnt in contours:
            if cv2.contourArea(cnt) < 1000:  # Ignore small noise
                continue

            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                if x < cx < x + w and y < cy < y + h:
                    boundary_color = (0, 255, 0)  # Change to green if object detected
                    object_detected = True

                    # Draw bounding box and label
                    cv2.rectangle(detected_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(detected_frame, "Object Found", (x, y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    break  # Stop after first detected object

        # Draw boundary rectangle on live frame
        cv2.rectangle(frame, (x, y), (x + w, y + h), boundary_color, 2)

        # Display status
        status_text = "Object Found" if object_detected else "No Object"
        status_color = (0, 255, 0) if object_detected else (0, 0, 255)
        cv2.putText(frame, status_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)

        return object_detected, frame, detected_frame

    def save_frame(self, frame, object_detected):
        """
        Save the current frame when 's' is pressed.
        """
        filename = "detected_object.png" if object_detected else "no_object.png"
        cv2.imwrite(filename, frame)
        print(f"Image saved as '{filename}'")

    def reset_background(self):
        """
        Reset the reference background when 'r' is pressed.
        """
        ret, reference_frame = self.cap.read()
        if ret:
            self.reference_gray = self.preprocess_frame(reference_frame)
            print("Reference background updated!")

    def run(self):
        """
        Start the object detection loop.
        """
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            object_detected, processed_frame, detected_frame = self.detect_objects(frame)

            # Show the processed frame
            cv2.imshow("Object Detection", processed_frame)

            # Handle keypress events
            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                self.save_frame(detected_frame if object_detected else processed_frame, object_detected)
            elif key == ord('r'):
                self.reset_background()
            elif key == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()

# Run the detector
if __name__ == "__main__":
    detector = ObjectDetector()
    detector.run()