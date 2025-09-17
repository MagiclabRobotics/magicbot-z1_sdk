# Example Description

## Runtime Dependencies
export LD_LIBRARY_PATH=/home/editorxu/ws/mjr/sdk/magic_humanoid_sdk/build:$LD_LIBRARY_PATH

## Example Execution

./high_level_motion_example

High-level motion control state transitions as described in the documentation:

1. Switch from suspended state to standing lock
2. Switch from standing lock state to balance standing
3. Execute trick actions in balance standing state
4. Send remote control commands to move forward in balance standing state
