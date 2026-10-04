# mower-sim

A ROS 2 simulation of an autonomous fairway mower: GNSS-based localization, stripe planning, path tracking, safety behavior, obstacle perception, and a command-and-control interface. It starts as a lightweight 2D simulation and then moves into Gazebo with the same nodes.

I'm building it to learn professional ROS 2, C++, and Python by working through the problems an autonomous mowing system has to solve, one milestone at a time.

> **Status: just started.** Nothing here has been built yet. Per the repo's rule, a claim is either verified by a command in this repo or marked as not yet verified, so every milestone below starts as "not started."

## Milestones

| # | Milestone | State |
|---|---|---|
| M0 | Workspace and tooling (Docker, colcon, Python + C++ hello world, tests) | not started |
| M1 | Mower model and 2D sim (kinematics, odometry + IMU) | not started |
| M2 | Localization (simulated RTK GNSS + IMU + odometry, EKF) | not started |
| M3 | Stripe planning and path tracking | not started |
| M4 | Safety and state machine (bump, tilt, lift, e-stop, geofence) | not started |
| M5 | Perception (LiDAR obstacle detection, then camera/depth) | not started |
| M6 | Command and control (MQTT + small web dashboard) | not started |
| M7 | Gazebo (same nodes, simulator swapped) | not started |
| M8 | Edge performance profiling (stretch) | not started |

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
docker/                 reproducible environment
AGENTS.md               how work is planned, built, and reviewed
```

## Honest gaps

- No code, no CI, and no licence file yet.
- Simulation only. No real hardware is planned.
