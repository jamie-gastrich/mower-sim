# 01 - Message type for a machine status heartbeat

**Date:** 2026-10-05 · **Milestone:** M0 · **Status:** accepted · **Relates to:** [01-package-layout.md](01-package-layout.md)

## Context

The first node in the project reports that a mower is alive and healthy. That node is not a toy: M4 adds safety states, M6 puts a dashboard on top of it, and M7 has a fleet manager collecting health from several mowers over MQTT and storing it in SQL. Whatever message type we pick here becomes the shape of machine health for the whole project, and it is the first thing that has to survive `ros2 bag record` in M1.

## Options

1. **`std_msgs/msg/String`** with a hand-formatted line such as `mower-01 OK uptime=12.4`.
2. **`diagnostic_msgs/msg/DiagnosticStatus`** — the standard ROS health message: `level` (`OK`/`WARN`/`ERROR`/`STALE`), `name`, `message`, `hardware_id`, and a `KeyValue[]` of named values.
3. **A custom `mower_msgs/msg/MowerStatus`** with exactly the fields we want.

## Measurements from this machine

- `ros2 interface show diagnostic_msgs/msg/DiagnosticStatus` resolves; `diagnostic_msgs` is installed. Its comment reads "This message holds the status of an individual component of the robot."
- Every primitive type in `std_msgs` is marked deprecated in this distro. `cat /opt/ros/lyrical/share/std_msgs/msg/String.msg` opens with "This was originally provided as an example message. It is deprecated as of Foxy ... use the equivalent in `example_msgs`." Same for `Int32`, `Float64`, `Bool`.
- The suggested replacement is not available: `ros2 pkg list | grep -x example_msgs` returns nothing.
- `std_msgs/msg/Header` is **not** deprecated, and `lifecycle_msgs`, `unique_identifier_msgs`, `rcl_interfaces` are all present.

## Decision

**Option 2: `diagnostic_msgs/msg/DiagnosticStatus`.**

Reasons:

- It is the platform's answer to this exact question, and it is already installed. Option 1 would mean inventing a format the ecosystem has already agreed on, and it starts from a type this distro has marked deprecated.
- `level` is the field that matters. M4's state machine (idle/mowing/paused/fault) and M7's health checks are all "is this thing OK, WARN, ERROR, or STALE". A string line makes every consumer re-parse text, and the fleet manager's SQL schema inherits that fragility.
- `KeyValue[]` is exactly the "and here are the numbers" slot: publish rate, uptime, frame, battery. Adding a field later does not change the message type or break the dashboard.
- `hardware_id` is the natural home for the mower's identity, which M7 needs per robot.
- Bag-friendly: it is a plain ROS message, so `ros2 bag record` in M1 captures it with no extra work.
- Option 3 is rejected for now, not forever. A custom `mower_msgs` package is the right answer the moment two *different* consumers need different fields out of one message, or when we need a field no standard message has (for example a mission id in M6). Paying that cost now, for a status line, is premature; paying it later is cheap because the decision record exists.

Consequence we accept: `DiagnosticStatus` is a component-level message, not a pose or a command. It carries no `Header`, so it has no timestamp and no frame. Node 01 therefore reports `base_frame` as a `KeyValue` rather than pretending the message is frame-stamped. When real stamped data is needed, `sensor_msgs` and `nav_msgs` already provide `Header`, and those are the types M1 and M2 will use.

## What would change this

- M6's dashboard needs a stable schema it can rely on, and if the key/value pairs turn into a de-facto contract that consumers start depending on field-by-field, promote it to `mower_msgs/msg/MowerStatus` with real named fields.
- If the fleet manager ends up consuming status over MQTT and SQL rather than ROS, the transport changes but this decision does not: the fields are the same, only the envelope differs.
- If a future distro drops or changes `DiagnosticStatus`, that is a new decision record, not a silent edit to this one.