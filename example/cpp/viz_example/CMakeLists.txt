add_executable(viz_example viz_example.cpp)

target_link_libraries(
  viz_example
  PRIVATE magicbot_z1::sdk)
