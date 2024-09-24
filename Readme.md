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



```
mkdir -p ~/orangewood_ws/src

cd ~/orangewood_ws/src

# Cloning the main core packages
git clone git@bitbucket.org:owl-dev/robogpt-v3.git

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

#### 2. Installation of backend related depdencies
- Run `backend.sh` to setup the pusher, stacy and other depdencies
```
cd ~/orangewood_ws/src/robogpt_v3/robogpt_bringup/setup/
./backend_setup.sh

```
#### 3. Install pip depdencies
```
pip3 install -r requirements.txt
```

## Launching Robogpt on local machine

#### Camera setup
```
roslaunch robogpt_vision camera_setup.launch
```

#### Running robogpt bringup 
```
roslaunch robogpt_bringup bringup.launch robot_name:=sim 

```
Current options for bots:- owl_68, owl_65, ec66, ec612, ec63 and sim for simulation

#### To run each module seperatly
- Running vision stack
```
roslaunch robogpt_vision vision_bringup.launch
```
- Running agent stack
```
roslaunch robogpt_agents agents_bringup.launch robot_name:=sim
```
- Running simulation from orangewood sim_stack package
```
roslaunch owl_bringup bringup.launch gripper:=robotiq2f85 world:=table  camera:=on sim:=on time:=5
```

- Running hardware Interface from robogpt_hardware_stack
```
roslaunch hardware_bringup bringup.launch type:=moveit driver:=robotiq
```

## 2) Setting Up in docker 

### *TO-DO*
