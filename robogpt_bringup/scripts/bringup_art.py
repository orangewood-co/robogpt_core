import pyfiglet
import rospy

rospy.init_node("Bringup Art")

def show(text):
    # Generate ASCII art
    welcome_art = pyfiglet.figlet_format(text)
    # Print the result
    print(welcome_art)

if __name__=="__main__":
    text = "Welcome to Robogpt!"    
    show(text)