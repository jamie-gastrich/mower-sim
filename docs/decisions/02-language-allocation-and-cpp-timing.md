# 02 - Language allocation, and the timing of the C++ nodes

**Date:** 2026-10-06 · **Milestone:** M0 · **Status:** accepted · **Relates to:** [01-package-layout.md](01-package-layout.md), [01-status-message-type.md](01-status-message-type.md), [01-status-names-and-diagnostics-feed.md](01-status-names-and-diagnostics-feed.md)

## Context

M0's description text says "Repo layout, Docker image, colcon build, one hello-world node in Python and one in C++, a test that runs in CI-style", and lesson 01's forward references (§1, §19) plan a lesson-02 C++ rebuild of `status_node`. The owner asked for a project-wide language breakdown up front, because every C++ file built purely to satisfy a "hello world" and then discarded would be work that is later removed.

Measured situation:

- The M0 *done-when* is "clean build in a fresh container, tests pass" — it never mentions C++. The C++ requirement appears only in M0's description paragraph.
- The project's genuinely C++-shaped work starts at M2 (localization/EFK: matrix math in a tight loop, the reference implementation `robot_localization` is C++) and continues at M3 (tracker) and M5 (perception, PCL). M9 targets the hot path in C++, which lives inside that stratum.
- `mower_status` (Python) is permanent: it is consumed by Python-side M4 (safety state machine), M6 (web dashboard), and M7 (fleet manager). A duplicate C++ status node would have to be retired later.

## Decision

1. **The language split is recorded for the whole project:**

   | Part | Language |
   |---|---|
   | `mower_status` / status (M0, permanent) | Python |
   | `mower_sim`, 2D sim (M1) — replaced by Gazebo at M8 *by design* | Python |
   | `mower_localization`, EKF (M2) | **C++** |
   | `mower_planner`, stripe paths (M3) | Python |
   | `mower_tracker`, path control (M3) | **C++** |
   | `mower_safety`, state machine (M4) | Python |
   | `mower_perception`, LiDAR (M5) | **C++** |
   | Command & control + dashboard (M6) | Python |
   | Fleet manager (M7, non-ROS service) | Python |

   Rule of thumb: tight loops, matrix math, and ecosystem-locked compute are C++; logic, telemetry, state machines, and services are Python.

2. **M0 ships only the Python `mower_status` node.** There is no C++ node at M0, and no `status_node_cpp` is ever planned. The first C++ node is `mower_localization` (the EKF) at M2. 01-status-names-and-diagnostics-feed.md's pins are unaffected: they refer to the Python `status_node`, which this record keeps permanent.

3. **M0's done-when is unchanged in substance:** "clean build in a fresh container, tests pass" — decided by the Docker lesson (lesson 04), not by a language demo. The two lessons after lesson 01 are the real test suite (03) and the container (04).

4. Lesson 01's forward references to a lesson-02 C++ rebuild of `status_node` are superseded by this record. The record appends to – never rewrites – the decision history.

## Reasons

- Non-throwaway principle (owner directive): a forced C++ hello at M0 either duplicates `status_node` (retired later) or prematurely seeds a node whose real shape (frames, covariance, dt) only exists once M1's sim and M2's sensor model are specified. Teaching `ament_cmake` through a half-defined node is worse than teaching it when the node is actually designed.
- The M0 done-when does not reference C++, so removing the C++ hello from M0's *description* changes scope text, not the acceptance criterion.
- The one thing this project is allowed to throw away is documented up front: the 2D `mower_sim` is replaced by Gazebo at M8 per the spec's own wording. Building it in C++ would be the real waste, and it is deliberately kept Python.

## Rejected

- **C++ status node at M0** (either distinct identity or canonical replacement of the Python node): two status implementations, one retired later; directly against the owner's non-throwaway concern.
- **Seeding `mower_localization` as a M0 skeleton** to double as the C++ hello: the node's parameters and output are not designable until M1/M2; a M0 skeleton would be re-taught wholesale at M2.
- **Choosing C++ for M3 planning / M7 fleet manager now**: coverage geometry and queue/SQL work are not hot; keep them Python unless measured otherwise.

## What would change this

- If a milestone before M2 shows real C++ need (for example M1's sim under unexpected load) → new decision record revisits just that row.
- If M2's localization survey finds a reason the EKF should not be C++ → the allocation table is revisited with that measured evidence.
- If a later consumer needs `mower_status` in C++ (for example an M4 safety node written in C++): M4 is allocated to Python here, so this clause only triggers if that allocation changes.