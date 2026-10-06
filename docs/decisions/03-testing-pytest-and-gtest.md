# 03 - How the project tests its logic

**Date:** 2026-10-06 · **Milestone:** M0 · **Status:** accepted · **Relates to:** [01-package-layout.md](01-package-layout.md), [02-language-allocation-and-cpp-timing.md](02-language-allocation-and-cpp-timing.md)

## Context

After lesson 01, `colcon test` means "the five scaffold linters pass": `ament_flake8`, `ament_mypy`, `ament_pep257`, `ament_xmllint`, and (once enabled) `ament_copyright`. Those check *style*, not *behaviour*. M0's done-when says "tests pass", and M2 onwards needs numerical correctness (the EKF's estimated pose error vs ground truth) that a lint pass cannot express. AGENTS.md already requires logic to live outside the ROS nodes so it can be unit tested without a running graph; this record decides how that testing is done.

## Options

1. **pytest unit tests against the pure functions**, one `test_*.py` per module, run through `colcon test` (the scaffold already ships a pytest test dependency and pytest is installed in this distro).
2. **Node-level tests** that launch a node, subscribe to its topic, and assert on the messages (launch_testing / rostest-style), plus replayable-bag checks.
3. **Lint-only**: leave `colcon test` as the scaffold linters and call that "testing".

## Decision

**Option 1, with a per-language rule:**
- Python packages (this project's default until M2) test pure functions with **pytest**; test files live in each package's `test/` next to the scaffold linters.
- C++ packages (M2 onwards: `mower_localization`, `mower_tracker`, `mower_perception`) test pure functions with **GTest**, wired through `ament_cmake_gtest`, driven by the same `colcon test` command.
- `test_copyright` is enabled in every package (the skip removed and a real Apache header naming the owner placed on every source file).
- A package's scoped result must show **zero failures and zero skipped** before a review can pass.

Reasons:

- It is the pattern the scaffold already establishes; there is no new tooling to install, and `colcon test` keeps being the single entry point for both style and behaviour checks.
- The purity split taught in lesson 01 (§15) is exactly the seam this needs: importing a package and asserting on a function needs no daemon, no `ROS_DOMAIN_ID`, no executor — measured at 0.06 s for four assertions in the lesson-03 worked example, versus spinning a node and echoing a topic.
- GTest for C++ keeps the unit boundary identical when the first C++ code arrives (M2); the sample-level rule about "no `rclcpp` include in logic" maps to "no `rclcpp` dependency in the tested translation unit".
- Lint-only (option 3) buys nothing. The M0 done-when would be nearly free, and M2's "measured pose error" criterion would still have no home.

Rejected:

- **Option 2 as the default.** It is the honest test of "the node actually publishes what I think", and M1's `ros2 bag` replay is a legitimate *second* layer for the sim milestone — but as the default it slows every check to graph-setup time, it is brittle in CI, and it tests the wiring rather than the logic. When a milestone genuinely needs it (M1 kinematics, M8 Gazebo drop-in), it is added for that milestone with its own decision record.
- Writing tests against the node class's private methods (unit-testing through the ROS layer) — worst of both.

## What would change this

- A milestone with real timing/message-shape requirements (M1 sim) may add a replayable-bag or launch_testing check *in addition*; that milestone records its own decision.
- If the fleet manager (M7) needs tests beyond pytest (SQL round-trips, MQTT contract), its own record chooses its framework; the ROS-side rule here is unaffected.