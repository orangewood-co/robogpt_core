import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect, QPushButton, QGridLayout, QLineEdit
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation

class SplashScreen(QWidget):
    def __init__(self, logo_path):
        super().__init__()
        self.setFixedSize(1000, 600)  # Make splash screen larger
        self.setWindowTitle("Calculator - Splash Screen")

        # Set up splash screen layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo image
        self.logo_label = QLabel(self)
        pixmap = QPixmap(logo_path)

        # Check if pixmap loaded correctly
        if pixmap.isNull():
            print("Error: Unable to load image. Check the logo path.")
        else:
            pixmap = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.SmoothTransformation)
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
        self.fade_animation.finished.connect(self.show_calculator)

    def show_calculator(self):
        self.close()
        self.calculator = Calculator()
        self.calculator.show()

class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern Calculator")
        self.setFixedSize(1000, 600)  # Make calculator window larger

        # Add fullscreen toggle button
        self.fullscreen_button = QPushButton("Toggle Fullscreen")
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)

        # Set up font and colors for a modern look
        font = QFont("Arial", 16)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QLineEdit {
                color: #ffffff;
                background-color: #444444;
                border: none;
                padding: 20px;
                font-size: 22px;
            }
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border-radius: 8px;
                padding: 15px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)

        # Display
        self.display = QLineEdit()
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setFont(font)
        self.display.setReadOnly(True)
        
        # Button layout
        button_layout = QGridLayout()
        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            '0', 'C', '=', '+'
        ]

        # Add buttons to layout
        row, col = 0, 0
        for button_text in buttons:
            button = QPushButton(button_text)
            button.clicked.connect(self.on_button_click)
            button_layout.addWidget(button, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.display)
        main_layout.addWidget(self.fullscreen_button)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # State variable
        self.expression = ""
        self.is_fullscreen = False

    def on_button_click(self):
        button_text = self.sender().text()
        
        if button_text == "C":
            self.expression = ""
        elif button_text == "=":
            try:
                self.expression = str(eval(self.expression))
            except Exception:
                self.expression = "Error"
        else:
            self.expression += button_text
        self.display.setText(self.expression)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
            self.fullscreen_button.setText("Toggle Fullscreen")
        else:
            self.showFullScreen()
            self.is_fullscreen = True
            self.fullscreen_button.setText("Exit Fullscreen")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Specify path to logo image

    logo_path = "/home/aion/orangewood_ws/src/robogpt_v3/robogpt_bringup/scripts/test.png"  # Change this to your desired image path

    # Show splash screen
    splash_screen = SplashScreen(logo_path)
    splash_screen.show()

    sys.exit(app.exec())
