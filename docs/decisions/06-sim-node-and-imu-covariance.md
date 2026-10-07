# Decision 06: sim node configuration contract and IMU covariance layout

Status: accepted (lesson 06, M1 Phase B).
Supersedes: none — it completes decision 05, which pinned the topic
interfaces, QoS, and sample-and-hold policy at the *node* level. This record
resolves the three points decision 05 left for the Phase B lesson: the IMU
covariance parameter shapes, the exact clamp timing inside the node, and the
module layout of `mower_sim`.

## Choices

1. **IMU covariance parameters are 3-element diagonals, expanded to 9 by a
   pure helper.** Each of the three `sensor_msgs/Imu` `float64[9]` covariance
   matrices is configured by a 3-element parameter holding the x/y/z diagonal
   (`[vx, vy, vz]`). A pure function `expand_imu_covariance` places them at
   row-major indices `0, 4, 8` and zeroes the rest, so the parameter only ever
   carries the numbers a human or a datasheet supplies. `mower_math`'s
   `expand_covariance_diagonal` (Phase A) already does this for the two 6×6
   `Odometry` matrices; the IMU case is the same idea at size 9 and lives in
   `mower_sim`'s own pure module (see 3).
2. **`imu_linear_acceleration_covariance` defaults to `[-1.0, 0.0, 0.0]`** —
   the message-level "no estimate" marker. The `Imu.msg` doc (measured,
   lesson 06) says a all-zero covariance means *unknown*, while `-1` in
   element 0 means "no estimate for this data element — disregard it". The
   sim does not simulate an accelerometer, so the accel estimate is absent:
   element 0 = `-1`. Orientation and angular velocity *are* produced, so
   their covariances are never `-1`.
3. **`mower_sim` gets a pure config module.** `mower_sim/sim_config.py`
   holds every default as a module constant, plus `positive_or` and
   `expand_imu_covariance`; `sim_node.py` holds only rclpy glue (declaring,
   reading, warning, ticking, message filling). No `rclpy` import in
   `sim_config.py`. Keeps AGENTS.md's "logic separated from ROS" testable
   without a graph, and keeps `mower_math`'s 30-test Phase A baseline and its
   ROS-free purity untouched (these helpers are mower_sim's configuration
   contract, not kinematics).
4. **Clamp at the inlet, report what was applied.** `limit_twist` runs in
   the `cmd_vel` subscription callback, once per command. The values stored
   and later published in `/odom.twist` and `/imu.angular_velocity` are the
   clamped ones — the robot's applied motion, which is what the acceptance
   checks read. Rejected: clamping at the tick (the published twist would be
   the raw command, misrepresenting what the robot did); a zero-on-silence
   watchdog (decision 05 rejected watchdogs until M4, and the teleop
   publishes only on keypress, so silence is normal driving).
5. **Repo wiring stays with the package:** `docker/entrypoint.sh` gains
   `mower_sim` in its `--packages-select` list, and `.gitignore` gains
   `ros2_ws/bags/` (bags arrive in lesson 07; ignore the directory now so a
   recording can never be committed).

## Rejected options

| Option | Why rejected |
|---|---|
| Full 9-element covariance parameters | forces the user to type nine numbers (only three are ever meaningful to us), invites index errors, and hides the row-major layout instead of centralising it in one tested helper |
| Single scalar variance per matrix | cannot express per-axis differences, and cannot carry the `-1`/`0` distinction the message contract needs |
| Constants and helpers in `sim_node.py` | AGENTS.md's pure/ROS split; the fallback policy and expansion would be untestable without spinning a node |
| `expand_imu_covariance` in `mower_math` | `mower_math` is the kinematics/math package with a frozen 30-test baseline; the 3→9 expansion is part of the sim's configuration contract, not general math |
| `initial_*` omitted (start at 0 always) | lesson 05 already decided the initial pose exists so live and replay runs start identically; this lesson implements it |

## What would change this

- M2's EKF consumes `/odom` and `/imu`; if REP-145's frame or sign semantics
  disagree with this layout, the covariance convention is revisited before
  M2 integration (already on decision 05's revisit list).
- If M8's Gazebo bridge wants `sensor_data` QoS or reuses these parameters
  for real sensor noise, only the QoS line (decision 05) and the default
  *values* change; the parameter *shapes* survive.
- If a safety watchdog is ever added, that is a new decision at M4; it would
  change the sample-and-hold wording of decision 05 and item 4 here, not the
  message or parameter contracts.