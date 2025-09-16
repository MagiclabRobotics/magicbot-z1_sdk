cmake_minimum_required(VERSION 3.18)

project(magicbot_z1_sdk LANGUAGES C CXX)

# Assuming the SDK is installed in the directory:
# /opt/magic_robotics/magic_z1_sdk
set(CMAKE_PREFIX_PATH /opt/magic_robotics/magic_z1_sdk)

find_package(magicbot_z1_sdk REQUIRED)

add_executable(cmake_example cmake_example.cpp)

target_link_libraries(cmake_example PRIVATE magicbot::z1_sdk)
