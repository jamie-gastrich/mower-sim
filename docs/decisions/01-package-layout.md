# 01 - Package and node layout

**Date:** 2026-10-05 · **Milestone:** M0 · **Status:** accepted

## Context

M0 requires a repo layout, and every later milestone adds nodes: sim, localization, planning, tracking, safety, perception, command and control. M7 then runs *several* mowers, each in its own ROS namespace. The layout decision is made once, at M0, and every package added afterwards inherits it. The spec adds one hard constraint: when the 2D sim is swapped for Gazebo in M8, "localization, planning, tracking, safety, perception, and C&C nodes stay unchanged."

## Options

1. **One package per node, plus shared pure-logic packages.** `mower_sim`, `mower_localization`, `mower_planner`, `mower_tracker`, `mower_safety`, `mower_perception`, `mower_status`, and shared logic in `mower_math` (no `rclpy`/`rclcpp` import) plus `mower_msgs` if custom interfaces are ever needed.
2. **One package for the whole robot.** A single `mower_robot` (or `mower_bringup`) containing every node.
3. **One package per subsystem**, several nodes inside each: `mower_navigation` holding the planner and the tracker, `mower_body` holding safety and status.

## Decision

**Option 1: one package per node, plus shared pure-logic packages.**

Reasons, with the measurement that backs each:

- It is the platform's own convention, not a style preference. In this install, 45 of the 84 packages that ship any executable ship **exactly one** (`ros2 pkg executables`, all packages, counted). The multi-executable packages are overwhelmingly demos and tutorials (`demo_nodes_cpp` 28, `examples_rclcpp_minimal_subscriber` 10, `quality_of_service_demo_cpp` 10).
- Independent build and test. `colcon build --packages-select mower_safety` builds one node. With option 2, editing a formatting string in the tracker rebuilds the safety node too, and one failing test blocks the whole robot.
- M8 is the payoff. Gazebo replaces `mower_sim` and nothing else, because the sim is one package with one entry point. Under option 2 the sim cannot be swapped without touching the nodes the spec says must stay unchanged.
- M7 is the second payoff. One namespace per mower means the *same* package is started three times under three namespaces. That works cleanly when a package is one node, and gets confusing when a package holds several nodes with different lifetimes.
- AGENTS.md already requires logic separated from ROS so it can be unit tested without a running graph. That is a package-level property, so it needs a package: `mower_math`.

Rejected:

- **Option 2 (one package).** Fewer `package.xml` files, but one broken test or one bad merge blocks every node, `colcon build --packages-select` stops being useful, and the M8 simulator swap turns into a refactor of the whole robot. Cost of being wrong is highest here because M8 is eight milestones away.
- **Option 3 (per subsystem).** A reasonable middle ground and it does group related code. Rejected because subsystem membership is exactly what changes as the project grows (safety grows a pre-arm check, perception grows a costmap layer), and a package boundary that keeps moving means import churn for no benefit.

Known counter-example, stated honestly: `ros_gz_bridge` ships 4 executables and `ros_gz_sim` ships 6. Grouping is not forbidden by the platform. The rule we are adopting is "one node per package unless there is a specific reason," and the reason gets written down when it happens.

## What would change this

- If the fleet manager ends up sharing large amounts of code with the nodes, a shared `mower_msgs` package is added. That is not a reversal of this decision, it is the "shared package" half of it.
- If M8 shows the Gazebo bridge can only be inserted at the sim boundary *and* several nodes must change together (for example a Gazebo-specific QoS or a different sensor driver), option 3 becomes worth revisiting for that subsystem only.
- If package count becomes painful to navigate (past roughly fifteen), revisit grouping, but only for nodes that genuinely always start and stop together.