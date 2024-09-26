cmake_minimum_required(VERSION 3.0.2)
project(robogpt_vision)


find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  roscpp
  rospy
  message_generation
)

add_service_files(
  FILES
  GetWorldContext.srv  
)

generate_messages(
  DEPENDENCIES
  std_msgs
  geometry_msgs  
)

catkin_package(
  CATKIN_DEPENDS geometry_msgs roscpp rospy message_runtime
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)


catkin_install_python(PROGRAMS
  scripts/get_world_context.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY config/ DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/config)
