cmake_minimum_required(VERSION 3.0.2)
project(robogpt_agents)

find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  roscpp
  rospy
  actionlib
  actionlib_msgs
  std_msgs
  message_generation
)

add_action_files(
  DIRECTORY action
  FILES Tour.action
)
generate_messages(
  DEPENDENCIES std_msgs actionlib_msgs geometry_msgs
)

catkin_package(
  CATKIN_DEPENDS rospy actionlib actionlib_msgs std_msgs message_generation
)
include_directories(
  ${catkin_INCLUDE_DIRS}
  )
  
install(PROGRAMS
    scripts/tour_files/tour_action_server.py
    scripts/tour_files/tour_action_client.py
    DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
  )
install(DIRECTORY config/ DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/config)
