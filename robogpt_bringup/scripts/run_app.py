#!/usr/bin/env python3
import sys
import os

# Add the directory containing the compiled module to Python's path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # This will import the compiled .so file (after you cythonize app.py)
    from app import QApplication, SplashScreen  #type: ignore
    
    def main():
        # Initialize the Qt application
        app = QApplication(sys.argv)
        
        # Get path to owl logo from the original module
        from app import owl_logo #type: ignore
        
        # Create and show splash screen
        splash = SplashScreen(owl_logo)
        splash.show()
        
        # Start the application event loop
        sys.exit(app.exec())
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Error importing app module: {e}")
    print("Make sure you've compiled app.py into a shared object file first.")
    sys.exit(1)