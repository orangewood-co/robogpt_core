# RoboGPT Stack
This repository contains all the core packages of Orangewood' s Robogpt including vision and agent stack.

## Setting Robogpt Stack

Methods 
- Setting up Robogpt on Local machine
- Setting up in Docker (*To-Do*)

## 1) Setting Simulation in HOST PC

### Prerequisites

Here are the prerequisites to run this Gazebo simulation

* [Ubuntu 20.04.6 LTS](https://releases.ubuntu.com/focal/)
* [ROS Noetic Full Desktop Full](https://wiki.ros.org/noetic/Installation/Ubuntu) , you can also use [Single line installation](https://github.com/qboticslabs/ros_install_noetic) which is given below


ROS Noetic Single line installation
```
wget -c https://raw.githubusercontent.com/orangewood-co/orangewood_sim_stack/main/host_pc_scripts/ros_install_noetic.sh && chmod +x ./ros_install_noetic.sh && ./ros_install_noetic.sh
```

After installing ROS Noetic in the host PC, we can setup a ROS workspace to build the sim packages.

Setup Bitbucket ssh key. Use this link for [ssh-setup Tutorial](https://support.atlassian.com/bitbucket-cloud/docs/set-up-personal-ssh-keys-on-linux/)

Download Pusher using this link [Pusher-cli](https://github.com/pusher/cli/releases?_gl=1*g4kqg7*_gcl_au*NDI0Njc4NDQ3LjE3MjE3NjA2Mjc.)

**This step is only if you are using Robogpt-Webapp on Local host**

Go to [pusher_dashboard](https://dashboard.pusher.com/) and create an channel to get pusher credentials for setting up local host.
use this [pusher_tut](https://youtu.be/5rAlSopSdpw?si=Pk7BQIidggV_LPGB)


Run these commands in terminal
```
mkdir -p ~/orangewood_ws/src

cd ~/orangewood_ws/src

# Cloning the main core packages
git clone git@bitbucket.org:owl-dev/robogpt_v3.git

# Cloning the additional supporting packages
git clone git@bitbucket.org:owl-dev/robot_drivers.git
git clone git@bitbucket.org:owl-dev/robogpt_apps.git

# Hardware Context package
git clone git@bitbucket.org:owl-dev/robogpt_hardware_stack.git

# Simulation package
git clone git@bitbucket.org:owl-dev/orangewood_simstack.git

** Note: You might need to setup some external dependencies for these supporting packages.Please Go through each individual readme of these repositories

cd ~/orangewood_ws

#Installing depdencies 

rosdep install --from-paths src --ignore-src -r -y

#Building packages

catkin_make -j1

echo "source ~/orangewood_ws/devel/setup.bash" >> /home/$USER/.bashrc

source /home/$USER/.bashrc

```
### Local setup steps

#### 1. Installing Realsense packages
- Install Ros Realsense package
```
sudo apt-get install ros-$ROS_DISTRO-realsense2-camera
```

#### 2.1 Installation of backend related depdencies
- Run `backend.sh` to setup the pusher, stacy and other depdencies
```
cd ~/orangewood_ws/src/robogpt_v3/robogpt_bringup/setup/
sudo ./backend_setup.sh

```
**While running backend setup you need to setup the pusher key. Use the default pusher key present in `keys.txt` for using production Robogpt webapp**

#### 2.2 Installation and setup of frontend for Running Robogpt-Webapp on local host
Run `frontend.sh` file to clone and setup the robogpt-webapp in your local machine
```
sudo chmod +x frontend_setup/frontend_setup.sh frontend_setup/pusher_key_update.py  # Making these two files executables

sudo ./frontend_setup/frontend_setup.sh

python3 frontend_setup/pusher_key_update.py  # Enter your pusher credentials here app-id, key, cluster and secret

```

#### 3. Install pip depdencies
```
pip3 install -r requirements.txt
```

## Launching Robogpt on local machine

#### Camera setup
```
roslaunch robogpt_vision camera_setup.launch type:=stereo 
# Type args is for type of camera stereo (realsense) or rbg 
```

#### Running robogpt bringup 
```
roslaunch robogpt_bringup bringup.launch robot_name:=sim use_case:=base use_sim:=true sim_vision:=on
```
- Current options for bots:- owl_68, owl_65, ec66, ec612, ec63 and sim for simulation

- Current options for use_case:- base, pick_and_place, drinkbot, archform.   **Note: Base is defualt and contains basic skills**

- Use_sim args decides to run the orangewood sim stack or robogpt hardware stack based on bool value

- sim_vision args decides to run the detection models for simulaton or not Options : on / off : Default is off

#### To run each module seperatly
- Running vision stack
```
roslaunch robogpt_vision vision_bringup.launch sim_vision:=off 
# sim_vision args decides to run the detection models for simulaton or not Options : on / off : Default is off

```
- Running agent stack
```
roslaunch robogpt_agents agent_bringup.launch robot_name:=sim use_case:=base 
# default robot_name is sim and use_case is set to base
# base contains all the basic skills like move to pose, save pose, connect robot
```
- Running simulation from orangewood sim_stack package
```
roslaunch owl_bringup bringup.launch gripper:=robotiq2f85 world:=table  camera:=on sim:=on time:=5
```

- Running hardware Interface from robogpt_hardware_stack
```
roslaunch hardware_bringup bringup.launch type:=moveit driver:=robotiq
# type: moveit or  description based on user if he/she wants to use moveit or not
# driver: robotiq, moveit, both or none. Currently for moveit we only run moveit driver for 6.8 and 6.5 

```


## 2) Setting Up in docker 

### *TO-DO*
