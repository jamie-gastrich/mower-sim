# 05 - Kinematics model and M1 sim interfaces

**Date:** 2026-10-06 · **Milestone:** M1 · **Status:** accepted

## Context

M1's spec sentence is *"Differential-drive (or Ackermann; decided in the survey)
kinematics with turning-radius limits. Sim publishes pose and a first sensor
(odometry + IMU)".* So two things get decided here: which kinematic model M1
implements and how the sim's interfaces (`/cmd_vel`, `/odom`, `/imu`) are
defined. Decision 02 already fixed the sim's language (Python) and decision 01
fixed the package layout (`mower_sim` = one node, `mower_math` = shared pure
logic). This record fixes model, interfaces, parameters, and the
determinism/noise policy, because M1's done-when — *"recorded bag replays the
same behavior"* — is only checkable if the sim is deterministic.

## Options: kinematic model

| Option | Accuracy vs. the real mower | Cost/complexity | Failure modes | How field robots do it |
|---|---|---|---|---|
| **1. Differential drive (unicycle): state (x, y, yaw), inputs (v, w), turn radius enforced by limiting w** | Full for a robot that turns about its center: exact at any speed; radius limit is a pure constraint | Low: two integrate-and-wrap equations, one clamp | None at normal speeds; wheel-slip at high w/v is not modeled (acceptable in 2D sim) | Most commercial mowers are differential or twin-differential; they drive stripes by heading control, not by steering geometry |
| 2. Ackermann / bicycle: state (x, y, yaw, steer), inputs (v, steer-angle or curvature) | Exact only if the mower is car-like | Medium: extra steer state with its own rate and range limits; radius comes from steer angle, singular at v=0 | Radius is meaningful only while moving; reversing with steer is geometrically different from forward | Used by row-crop tractors and some ride-on mowers; needs a separate "reversing plan" |
| 3. Holonomic point: direct (vx, vy, w) | Not a mower at all | Lowest | Violates the spec's turning-radius requirement by construction | Rare in mowing; typical for warehouse AGVs (the owner's day job) |

**Chosen: Option 1, differential drive with a turning-radius limit enforced on
`w`.** Reasons:

- The spec allows either; diff-drive is the common commercial-mower layout and
  the simpler state; nothing downstream (planner, tracker, safety) needs a
  steering angle.
- M3's tracker will emit (v, w) commands; a unicycle model consumes them
  directly. Ackermann would force the tracker to reason about steer-rate
  limits immediately.
- The radius policy is a single clamp: for a moving command, require
  `|w| <= |v| / min_turn_radius` and `|w| <= max_angular_speed`. In-place spin
  (v = 0, w ≠ 0) is allowed and bounded only by `max_angular_speed` — this is
  what commercial mowers do for end-of-stripe turnarounds, and teleop must be
  able to spin in place (measured: teleop's `j`/`l` keys emit exactly this).

Rejected:

- **Ackermann/bicycle** — extra state with no consumer until M3, v=0
  singularity for the radius, and no evidence the sim mower is car-like.
- **Holonomic** — spec explicitly demands turning-radius limits; a point robot
  cannot have them.

What would change this: if the spec's mower becomes a ride-on/car-like vehicle
(steerable front axle, rear-wheel drive), or M7's fleet is required to mix
mower types, the model is revisited and the unicycle stays only for the
diff-drive members. If M3's stripe tracker needs to reason about
steering-angle limits, revisit — but the evidence so far points the other way.

## Interfaces

Command in, two sensors out, all standard message types (spec constraint:
unchanged when Gazebo replaces the sim at M8):

| Topic | Type | Direction | Measured facts behind the definition |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | in | `teleop_twist_keyboard` in this install publishes plain `Twist` on relative `cmd_vel` (v2.4.1, read from installed source), so consumer and teleop agree by default at the root namespace |
| `/odom` | `nav_msgs/msg/Odometry` | out | Message doc (verified from this install): the twist is "specified in the coordinate frame given by the child_frame_id", i.e. velocity is in the **body** frame |
| `/imu` | `sensor_msgs/msg/Imu` | out | Message doc (verified): unknown covariance ⇒ "set element 0 of the associated covariance matrix to -1" — used for the accelerometer (not simulated) |

Frames: `odom` (parameterized frame_id, a local world frame per REP-105; for
M1 it is ground truth) and `base_link` (child_frame_id, body frame). The IMU
frame is parameterized (`imu_link` default); REP-145's exact IMU-frame
semantics are **not yet verified** against the installed docs and are revisited
at M2.

QoS: everything is the ROS default profile (RELIABLE, KEEP_LAST 10). Measured
on all three topics in this lesson's runs (`ros2 topic info --verbose`,
`ros2 bag record` shows RELIABLE KEEP_LAST 10 for its subscriptions). Dropping
a command or an odometry sample at this rate is worse than a few ms of
latency; `sensor_data` QoS is revisited when Gazebo raises the sensor rates at
M8.

## Determinism and command policy

- **No noise in M1.** The equivalence check replays a recorded bag into a
  fresh sim and compares final poses; any random term would force
  statistical tolerances. Noise arrives at M2 with the simulated GNSS, using
  a seeded RNG so M2 gets its own deterministic tests.
- **Sample-and-hold:** the sim remembers the latest `/cmd_vel` and integrates
  it every tick. No watchdog yet — a stalled command stream is a safety
  concern and lands with M4 (safety), which is where command-loss handling
  belongs.
- **The sim reports what it applied:** `/odom.twist` carries the *clamped*
  (v, w), not the raw command, so the tracker and the reviewer can see the
  radius policy in the data. This is how the straight-line/radius acceptance
  checks work (report peak |w| and min radius from the recorded odom).
- **Covariance convention:** diagonal-only covariance, expanded from a
  6-element diagonal parameter to the 36-element matrices the messages need
  (position diag at indices 0, 7, 14, 21, 28, 35). Unknown axes use -1.
- **Parameters carry the configuration** (AGENTS.md: no hard-coded topics,
  names, distances, or rates): `update_rate`, `max_linear_speed`,
  `max_angular_speed`, `min_turn_radius`, `initial_x/y/yaw` (the initial pose
  exists so every replay starts from the identical state — that is what makes
  "same behavior" measurable), frame names, and covariance diagonals. Topic
  names stay relative so M7's per-mower namespaces work without code changes.
  Invalid values (e.g. a negative `update_rate`) fall back to the default via
  a pure `positive_or(value, default)` helper, tested without a running graph.
- **Heading convention pinned:** `(-π, π]`. Measured: the current
  `wrap_angle_rad` returns **both** endpoints (`wrap(π) = π` and
  `wrap(-π) = -π` exactly), while its docstring says `[-π, π]` and its tests
  assert `(-π, π]`; review 03 asked for one stated convention. The lesson
  requires making the docstring, implementation, and a new boundary test all
  agree on `(-π, π]` (input `-π` must wrap to `+π`). This is the convention
  lesson 03 already taught, so it is the one being kept.

## What would change this

- M2's EKF consumes `/odom` and `/imu`; if the EKF needs a different
  covariance convention or an angular-velocity sign convention, this record is
  revisited before the M2 integration (REP-145 verification is explicitly
  deferred to M2).
- If M8's Gazebo bridge requires `sensor_data` QoS for high-rate sensors, only
  the QoS line of this record changes.
- If the teleop package disappears from the platform (it is a tutorial package,
  present in this install but absent from the base container image), the
  done-when still stands — the owner can drive by publishing commands — but
  the "platform provides teleop" argument in the lesson is updated.