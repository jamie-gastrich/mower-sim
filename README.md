# mower-sim

A ROS 2 simulation of an autonomous fairway mower: GNSS-based localization, stripe planning, path tracking, safety behavior, obstacle perception, a command-and-control interface, and a fleet manager that coordinates several mowers. It starts as a lightweight 2D simulation and then moves into Gazebo with the same nodes.

I'm building it to learn professional ROS 2, C++, and Python by working through the problems an autonomous mowing system has to solve, one milestone at a time.

> **Status: M0 in progress.** Lesson 01 passed review — `mower_status` builds, its five tests pass, and the node runs with parameters driving behaviour, all verified by the commands in `docs/reviews/01-workspace-and-first-node.md`. Remaining for M0: a real test suite (lesson 03) and the Docker image whose fresh-container build passes the spec's done-when (lesson 04). The first C++ node is deferred to M2 by `docs/decisions/02-language-allocation-and-cpp-timing.md`, so no C++ work is planned at M0. Every other milestone below is not started.

## Milestones

| # | Milestone | State |
|---|---|---|
| M0 | Workspace and tooling (Docker, colcon, Python `mower_status` node, tests) | in progress |
| M1 | Mower model and 2D sim (kinematics, odometry + IMU) | not started |
| M2 | Localization (simulated RTK GNSS + IMU + odometry, EKF) | not started |
| M3 | Stripe planning and path tracking | not started |
| M4 | Safety and state machine (bump, tilt, lift, e-stop, geofence) | not started |
| M5 | Perception (LiDAR obstacle detection, then camera/depth) | not started |
| M6 | Command and control (MQTT + small web dashboard) | not started |
| M7 | Fleet management (task assignment, zone locking, diagnostics, fault recovery) | not started |
| M8 | Gazebo (same nodes, simulator swapped) | not started |
| M9 | Edge performance profiling (stretch) | not started |

Full details and "done when" criteria are in [`spec/mower-spec.md`](spec/mower-spec.md).

## How I work

- **I write the code.** AI agents act as a professor (teaches a concept, assigns the build) and a reviewer (critiques it against the end-product spec). See [`AGENTS.md`](AGENTS.md).
- **Options are compared before a choice is made.** Each concept gets a short survey of up to three approaches, then a decision record in [`docs/decisions/`](docs/decisions/) explaining what was chosen, what was rejected, and why.
- **Lessons and reviews are kept.** [`docs/lessons/`](docs/lessons/) and [`docs/reviews/`](docs/reviews/) show how the project evolved.
- **Standard ROS message types** are used for all sensors and commands, so the Gazebo move changes the simulator, not the mower nodes.

## Quick start

Not available yet. This section will hold the Docker and colcon build commands once M0 is verified.

## Layout

```
spec/mower-spec.md      end product and milestones
docs/lessons/           lectures and assignments
docs/decisions/         decision records (append-only)
docs/reviews/           code reviews
ros2_ws/src/            ROS 2 packages
services/               non-ROS services such as the fleet manager (if the decision record places it outside ROS)
docker/                 reproducible environment
AGENTS.md               how work is planned, built, and reviewed
```

## Honest gaps

- No code, no CI, and no licence file yet.
- Simulation only. No real hardware is planned.