cmake_minimum_required(VERSION 3.0.2)
project(robogpt_vision)


find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  roscpp
  rospy
  message_generation
  actionlib_msgs
  actionlib
)

add_service_files(
  FILES
  GetWorldContext.srv  
)


generate_messages(
  DEPENDENCIES
  std_msgs
  geometry_msgs
  actionlib_msgs
)

catkin_package(
  CATKIN_DEPENDS geometry_msgs roscpp rospy message_runtime actionlib_msgs std_msgs actionlib
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)




install(DIRECTORY config/ DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/config)
