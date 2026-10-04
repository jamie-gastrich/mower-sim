# Mower Sim: End-Product Spec

## Goal
Build a ROS 2 simulation of an autonomous fairway mower that plans stripes, localizes with centimeter-level accuracy, avoids obstacles, and is controlled through a command-and-control interface. Start with a lightweight 2D sim, then move the same nodes into Gazebo.

This is a learning and portfolio project modeled on the kind of system a robotics software engineer at an autonomous mowing company would work on: localization, perception, planning, controls, and command and control.

## Constraints
- ROS 2 (use the installed distro) with a mix of **Python and C++** nodes. Each milestone's assignment states which language it uses.
- Docker for reproducible builds from M0 onward.
- No real hardware. All sensors are simulated and publish **standard ROS message types** so nodes work unchanged in Gazebo.
- The 2D sim is custom (stock turtlesim has no sensors).
- Every node must be testable in isolation (unit tests or a replayable bag).

## Non-goals (for now)
- Real GNSS/RTK hardware, real motor control, real vehicle dynamics beyond simple kinematics.
- Production-grade UI. A simple dashboard is enough.

## System overview
| Area | What it does | Typical ROS interfaces |
|---|---|---|
| Sim | Simulates mower pose and sensors with noise | `/cmd_vel` in; `/odom`, `/imu`, `/gnss`, `/scan` out |
| Localization | Fuses GNSS, IMU, odometry into a pose estimate | `/odometry/filtered` |
| Planning | Turns a boundary into stripe (coverage) paths | `nav_msgs/Path` |
| Tracking | Follows the path within kinematic limits | `/cmd_vel` |
| Safety | Bump, tilt, lift, e-stop, geofence state machine | `/safety/state` |
| Perception | Detects obstacles from LiDAR, then camera/depth | detections / costmap |
| Command & control | Start/stop/status of missions over MQTT + web UI | MQTT topics |

## Milestones
Each milestone is a vertical slice: it runs end to end before the next one starts.

**M0: Workspace and tooling.** Repo layout, Docker image, colcon build, one hello-world node in Python and one in C++, a test that runs in CI-style.
*Done when:* clean build in a fresh container, tests pass.

**M1: Mower model and 2D sim.** Differential-drive (or Ackermann; decided in the survey) kinematics with turning-radius limits. Sim publishes pose and a first sensor (odometry + IMU).
*Done when:* teleop drives the mower; recorded bag replays the same behavior.

**M2: Localization.** Add simulated RTK GNSS with realistic noise. Fuse GNSS + IMU + odometry in an EKF.
*Done when:* estimated pose error vs. ground truth is measured and reported; target within a few centimeters in a clean-sky scenario, with a defined degradation when GNSS drops out.

**M3: Stripe planning and path tracking.** Coverage path (boustrophedon stripes) for a polygon boundary; path tracker respecting turning limits.
*Done when:* mower covers a rectangle and an irregular polygon; cross-track error and coverage percentage are logged.

**M4: Safety and state machine.** Bump, tilt, lift, e-stop, geofence. Explicit states (idle, mowing, paused, fault) with defined transitions.
*Done when:* every fault injected in the sim produces the correct state and a safe stop.

**M5: Perception.** LiDAR obstacle detection and avoidance/stop behavior; then camera or stereo depth.
*Done when:* mower stops or reroutes around a static obstacle placed on a stripe.

**M6: Command and control.** MQTT mission interface (load plan, start, pause, resume, status) and a small web dashboard showing pose, path, and state.
*Done when:* a full mission is started, monitored, and stopped from the dashboard alone.

**M7: Gazebo.** Replace the 2D sim with Gazebo through the ROS-Gazebo bridge. Localization, planning, tracking, safety, perception, and C&C nodes stay unchanged.
*Done when:* the M3 mission runs in Gazebo with the same launch structure.

**M8 (stretch): Edge performance.** Profile CPU/memory, optimize a hot path (likely in C++), and document results.

## Learning method
For every concept inside a milestone, the professor:
1. Surveys up to three options and compares them.
2. Writes a decision record picking one for this project, with reasons and what would change the choice.
3. Teaches the chosen approach.
4. Assigns a build task with acceptance criteria. No solution code.

The student builds it, then the reviewer critiques it against this spec. The implementer agent is not used until the student has passed review on a milestone.

## Definition of done (every milestone)
- Builds in the Docker image, tests pass.
- Interfaces use standard message types and are documented.
- Reviewed, with blockers resolved.
- Decision records and lessons are filed in `docs/`.
