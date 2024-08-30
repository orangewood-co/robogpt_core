import importlib,sys, os
import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

robot_model = "sim" 
# import robogpt_v3.robot_drivers.sim.wrapper.bot_wrapper
try:
    #wrapper_path = f'robogpt_v3/robot_drivers/{robot_model}/wrapper/bot_wrapper'
    wrapper_path = f'/../../../../robogpt_v3/robot_drivers/{robot_model}/wrapper/bot_wrapper'
    bot_control = importlib.import_module(wrapper_path)
    print("Loaded")
except Exception as err:
    print("Could not load robot due to ",err)
    utils.send_msg(message="Error in  loading Robot. Please check the Robot Model")

bot_control.test()

