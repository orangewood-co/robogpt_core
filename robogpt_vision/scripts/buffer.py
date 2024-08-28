from collections import deque

class DetectionBuffer:
    def __init__(self):
        self.buffer = deque()
        self.buffer_length = 20
        self.merged_objects = {}

    def extract_objects(self, data, name):
        """
        Initialize the object dictionary from the given data.
        """
        objects = {}
        for key, value in data[name].items():
            detected_object = value.get("detected_object")

            if detected_object is not None:
                # Create a copy of the value dictionary excluding the "detected_object" key
                value_without_detected_object = {k: v for k, v in value.items() if k != "detected_object"}
                objects[detected_object] = value_without_detected_object

        return objects

    def merge_objects(self, new_objects):
        for key, value in new_objects.items():
            self.merged_objects[key] = value

    def update_buffer(self, objects):
        self.buffer.append(objects)
        if len(self.buffer) > self.buffer_length:
            # Pop the oldest frame from the buffer
            old_objects = self.buffer.popleft()


    def merge_frames(self, current_frame, name):
        current_objects = self.extract_objects(current_frame,name)
        self.merged_objects={}
        
        for values in self.buffer:
            self.merge_objects(values)

        self.merge_objects(current_objects)
        self.update_buffer(current_objects)

        new_frame = self.create_frame(self.merged_objects,name)
        return new_frame

    def create_frame(self, objects,name):
        new_frame = {}
        for i, (key, value) in enumerate(objects.items(), 0):
            attributes = {'detected_object': key}
            for key2, value2 in value.items():
                attributes[key2] = value2
            s_no = "detection_" + str(i)
            new_frame[s_no] = attributes

        new_frame_with_ip = {name: new_frame}
        return new_frame_with_ip