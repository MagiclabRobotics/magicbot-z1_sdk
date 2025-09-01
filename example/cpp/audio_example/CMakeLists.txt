
add_executable(audio_example audio_example.cpp)

target_link_libraries(
  audio_example
  PRIVATE magicbot_z1::sdk)
