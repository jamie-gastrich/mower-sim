#!/usr/bin/env bash
set -eo pipefail
cd /ws/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --packages-select mower_math mower_status
colcon test-result --test-result-base build/mower_math --verbose
colcon test-result --test-result-base build/mower_status --verbose