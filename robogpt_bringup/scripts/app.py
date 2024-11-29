import os
import sys
import time 
import urllib
import getpass
import subprocess
import rospkg,rospy
from PySide6.QtWidgets import QApplication,QLineEdit, QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect, QComboBox, QPushButton, QHBoxLayout, QGridLayout
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation

rospack = rospkg.RosPack()
vision_path = rospack.get_path('robogpt_vision')
agent_path = rospack.get_path('robogpt_agents') 

sys.path.append(vision_path)

# Define base_dir for getting the exact path of skills/applications
base_img_dir = f"/home/{getpass.getuser()}/orangewood_ws/src/robogpt_v3/robogpt_bringup/imgs"

main_logo_path = os.path.join(base_img_dir, "White_logo.png")
owl_logo = os.path.join(base_img_dir, "RoboGPT2.png")

def launch_with_delay(launch_file, args, delay):
    command = ['roslaunch'] + launch_file.split() + args
    process = subprocess.Popen(command)
    time.sleep(delay)
    return process

def close_with_delay(processes, delay):
    
    for process in processes:
        process.terminate()
        time.sleep(delay)

class SplashScreen(QWidget):
    def __init__(self, logo_path):
        super().__init__()
        self.setFixedSize(1280, 720)
        self.setWindowTitle("Robogpt")

        # Splash screen layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo image
        self.logo_label = QLabel(self)
        pixmap = QPixmap(logo_path)

        # Check if pixmap loaded correctly
        if pixmap.isNull():
            print("Error: Unable to load image. Check the logo path.")
        else:
            pixmap = pixmap.scaled(1300, 780, Qt.AspectRatioMode.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        
        layout.addWidget(self.logo_label)

        # Set up opacity effect for fade-out animation
        self.opacity_effect = QGraphicsOpacityEffect(self.logo_label)
        self.logo_label.setGraphicsEffect(self.opacity_effect)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(1000)
        self.fade_animation.setStartValue(1)
        self.fade_animation.setEndValue(0)

        # Timer to trigger fade-out animation
        QTimer.singleShot(1000, self.start_fade_out)

    def start_fade_out(self):
        self.fade_animation.start()
        self.fade_animation.finished.connect(self.show_main_app)

    def show_main_app(self):
        self.close()
        self.main_app = MainApp()
        self.main_app.show()

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RoboGPT - Setup")
        self.setFixedSize(1280, 720)
        self.vision_config_path = os.path.join(vision_path,"config/vision_config.json")
        self.app_list = os.path.join(agent_path,"config/tools_config/app_list.json")
        # Set up theme
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                font-size: 20px;
            }
            QComboBox, QLineEdit {
                color: #ffffff;
                background-color: #444444;
                border: 1px solid #555555;
                padding: 5px;
                font-size: 16px;
            }
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                margin-top: 10px
            }
            QPushButton:hover {headline.setStyleSheet("color: white; font-size: 30px;")

                background-color: #555555;
            }
        """)

        # Fonts for the text and dropdowns
        font = QFont("lato", 20)

        # Create and set headline
        headline = QLabel("Welcome to RoboGPT", self)
        headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        headline.setStyleSheet("color: white; font-size: 30px;")
        headline.setGeometry(450, 100, 400, 50)  # Position and size of the headline

        # Logo images
        image1_label = QLabel(self)
        image2_label = QLabel(self)
        logo = QPixmap(main_logo_path).scaled(250, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.SmoothTransformation)
        image1_label.setPixmap(logo)

        # Horizontal layout for logos (extreme left and right)
        image_layout = QHBoxLayout()
        image_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        image_layout.addWidget(image1_label)  # Add image on the left
        image_layout.addStretch(1)  # Stretch to push the image to the left

        # Combine the two layouts (images and headline) vertically
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 215)  # Remove margins for the top layout
        top_layout.addLayout(image_layout)  # Add image layout first (left and right)

        # Create the QLineEdit for Robot IP
        self.robot_ip_input = QLineEdit(self)
        self.robot_ip_input.setFont(font)

        # Set placeholder text with CSS for low opacity
        self.robot_ip_input.setPlaceholderText("Enter Robot IP...")

        # Apply CSS to the placeholder text for low opacity
        self.robot_ip_input.setStyleSheet("""
            QLineEdit {
                color: white;
                margin-bottom: 20px
            }
            QLineEdit::placeholder {
                color: rgba(0, 0, 0, 0.5);  
            }
        """)
        # Connect the textChanged signal to a method that updates the robot_ip variable
        self.robot_ip_input.textChanged.connect(self.update_robot_ip)

        # Create a layout for Robot IP
        robot_ip_layout = QVBoxLayout()
        robot_ip_layout.addWidget(self.robot_ip_input)
        robot_ip_layout.setSpacing(1)
        # Grid layout to organize dropdowns
        grid_layout = QGridLayout()
        grid_layout.setVerticalSpacing(15)  # Reduce vertical spacing

        # Create and add 7 labeled dropdowns
        self.dropdowns = []
        drop_labels = ["Robot Name", "Use Case", "Type", "Drivers", "Use Sim", "Sim Vision"]
        dropdown_options = [
            ["ec63", "ec612", "owl68", "owl65", "ec66"],  
            ["base", "pick_and_place", "archform", "drink_bot"],          
            ["description", "moveit"],               
            ["moveit", "robotiq", "both", "none"],        
            ["false", "true"],  
            ["off","on"], 
        ]

        for i in range(len(drop_labels)):  # Use length of drop_labels
            label = QLabel(drop_labels[i])
            label.setFont(font)
            dropdown = QComboBox()
            dropdown.setFont(font)
            dropdown.setStyleSheet("color: white; font-size: 18px;")

            dropdown.addItems(dropdown_options[i])  # Add custom options from dropdown_options list
            self.dropdowns.append(dropdown)

            # Connect the currentIndexChanged signal to the slot to save value
            dropdown.currentIndexChanged.connect(self.update_dropdown_value)

            # Add label and dropdown to grid layout, placing 4 in each column
            row = i % 3
            col = i // 3  # 0 for left, 1 for right column
            grid_layout.addWidget(label, row * 2, col)         # Label on top
            grid_layout.addWidget(dropdown, row * 2 + 1, col)  # Dropdown below label
        

        # Buttons at the bottom
        button_layout = QHBoxLayout()
        # Open Config Button
        self.open_config_button = QPushButton("Open Config File")
        self.open_config_button.clicked.connect(self.open_config_file)
        self.open_config_button.pressed.connect(lambda: self.set_button_color(self.open_config_button, "#007BFF"))  # Blue
        self.open_config_button.released.connect(lambda: self.set_button_color(self.open_config_button, "#333333"))  # Original
        button_layout.addWidget(self.open_config_button)

        # Open App List Button
        self.open_app_list_button = QPushButton("Open App List")
        self.open_app_list_button.clicked.connect(self.open_app_list)
        self.open_app_list_button.pressed.connect(lambda: self.set_button_color(self.open_app_list_button, "#007BFF"))  # Blue
        self.open_app_list_button.released.connect(lambda: self.set_button_color(self.open_app_list_button, "#333333"))  # Original
        button_layout.addWidget(self.open_app_list_button)

        # Start Button
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_robogpt)
        self.start_button.pressed.connect(lambda: self.set_button_color(self.start_button, "#007BFF"))  # Blue
        self.start_button.released.connect(lambda: self.set_button_color(self.start_button, "#333333"))  # Original
        button_layout.addWidget(self.start_button)

        # Create Stop Button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_robogpt)
        self.stop_button.pressed.connect(lambda: self.set_button_color(self.stop_button, "#FF0000"))  # Change color on press
        self.stop_button.released.connect(lambda: self.set_button_color(self.stop_button, "#333333"))  # Reset color
        button_layout.addWidget(self.stop_button)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)  # Add logos and headline
        main_layout.addLayout(robot_ip_layout)  # Add Robot IP input field
        main_layout.addLayout(grid_layout)  # Add dropdowns
        main_layout.addLayout(button_layout)  # Add buttons
        self.setLayout(main_layout)

        # Default values to Variables to store dropdown selections and Robot IP
        self.robot_name = "ec63"
        self.use_case = "base"
        self.type = "description"
        self.driver = "robotiq"
        self.use_sim = "false"
        self.sim_vision = "off"
        self.robot_ip = "192.168.1.200"

    # Slot function to update robot_ip
    def update_robot_ip(self):
        self.robot_ip = self.robot_ip_input.text()  # Save the current text input into the robot_ip variable

    # Slot to update variable values based on dropdown selection
    def update_dropdown_value(self, index):
        sender = self.sender()  # Get the dropdown that triggered the signal
        selected_text = sender.currentText()

        # Save the selected option to the corresponding variable
        if sender == self.dropdowns[0]:
            self.robot_name = selected_text
        elif sender == self.dropdowns[1]:
            self.use_case = selected_text
        elif sender == self.dropdowns[2]:
            self.type = selected_text
        elif sender == self.dropdowns[3]:
            self.driver = selected_text
        elif sender == self.dropdowns[4]:
            self.use_sim = selected_text
        elif sender == self.dropdowns[5]:
            self.sim_vision = selected_text

    # Placeholder functions for button actions
    def open_config_file(self):
        print("Open Config File button pressed")
        
        if os.path.exists(self.vision_config_path):
            try:
                # Use subprocess to open the file in Gedit
                subprocess.run(["gedit", self.vision_config_path], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error opening file: {e}")
        else:
            print(f"File not found: {self.vision_config_path}")

    def open_app_list(self):
        print("Open App List button pressed")
        print("Open Config File button pressed")
        
        if os.path.exists(self.app_list):
            try:
                # Use subprocess to open the file in Gedit
                subprocess.run(["gedit", self.app_list], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error opening file: {e}")
        else:
            print(f"File not found: {self.app_list}")

    def set_button_color(self, button, color):
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: #ffffff;
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                margin-top: 10px;
            }}
        """)

    def start_robogpt(self):
        # Print all the dropdown values when start button is pressed
        try:
            args = [f'robot_name:={self.robot_name}',f'use_case:={self.use_case}',f'type:={self.type}',f'driver:={self.driver}',f'use_sim:={self.use_sim}',f'sim_vision:={self.sim_vision}',f'robot_ip:={self.robot_ip}']
            print(f"Here is the List of Arguments: {args}")

            bringup_process = launch_with_delay('robogpt_bringup bringup.launch',args=args, delay=5)
            url_process = urllib.urlopen('http://example.com')
            bringup_process.wait()  
            url_process.wait()

        except KeyboardInterrupt:
                # Terminate all processes if the script is interrupted
                processes = [bringup_process]
                close_with_delay(processes, 5)
                print("Processes terminated")

    def stop_robogpt(self):
        print("Stopping RoboGPT...")
        # Logic to terminate processes goes here
        if hasattr(self, 'bringup_process'):
            self.bringup_process.terminate()
            self.bringup_process.wait()
            print("RoboGPT stopped.")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Specify path to logo image
    splash = SplashScreen(owl_logo)
    splash.show()

    sys.exit(app.exec())
