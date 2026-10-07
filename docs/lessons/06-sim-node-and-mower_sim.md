**Milestone:** M1 (Phase B) · **Language:** Python · **Prerequisite:**
[05-kinematics-pure-functions.md](05-kinematics-pure-functions.md)

**Concepts this assignment requires** (each is taught in its own section below):

- Node anatomy: subscription + timer + two publishers ([§5.1](#51-the-node-as-a-state-machine-sample-and-hold))
- Applied, not raw: the clamp runs once at the inlet ([§5.1](#51-the-node-as-a-state-machine-sample-and-hold))
- Parameters, not magic numbers: the full 15-parameter table ([§5.2](#52-parameters-not-magic-numbers))
- `positive_or` fallback with a warning that names the parameter ([§5.2](#52-parameters-not-magic-numbers))
- Odometry and IMU message contracts: frames, body-frame twist, covariance layout ([§5.3](#53-the-message-contracts-odometry-and-imu))
- The IMU "unknown" convention: `-1` in covariance element 0 ([§5.3](#53-the-message-contracts-odometry-and-imu))
- Expanding a 3-element diagonal to a row-major 3×3 ([§5.4](#54-two-covariance-shapes-one-idea))
- The tick pipeline: `dt = 1/rate`, integrate, fill, publish ([§5.5](#55-the-tick-pipeline))
- Package-level wiring: entrypoint and `.gitignore` ([§5.7](#57-package-wiring-entrypoint-and-gitignore))
- Worked example: the toy `xp_drive` node, end to end ([§6](#6-worked-example-a-toy-drive-node-with-clamped-sample-and-hold))

---

## 1. Where this fits

M1's spec sentence: *"Differential-drive kinematics with turning-radius
limits. Sim publishes pose and a first sensor (odometry + IMU)."* Phase A
(lesson 05) gave you the pure kinematics in `mower_math` — the 30-test
baseline with `limit_twist`, `step_unicycle`, `yaw_to_quaternion`, and
`expand_covariance_diagonal`. Those functions do not move anything; they are
the model. Phase B, this lesson, wraps the model in the thing the rest of the
mower talks to: the `mower_sim` package with its `sim_node`, which subscribes
`/cmd_vel`, ticks at `update_rate`, and publishes `/odom` and `/imu` —
standard message types, parameter-driven, with the clamp applied exactly
once per command.

This is the lesson where the project stops being math and starts being a
robot: a first moving node, the message contracts M2's EKF and M3's tracker
will consume, and the discipline that every configuration value is a
parameter with a tested fallback. Lesson 07 (next) adds `bag_check.py` and
the record/replay evidence loop that turns M1's done-when ("recorded bag
replays the same behavior") into an exit code; Phases C and D then run the
runtime evidence. This lesson builds the package those phases exercise.

Everything below was measured on this machine on 2026-10-07 in
`/tmp/opencode/l06toy`, with a dedicated `ROS_DOMAIN_ID` per run (41 or 42).

## 2. Verification table

| Claim | How it was checked | Result |
|---|---|---|
| `ros2 pkg create` scaffolds node + entry point | ran `ros2 pkg create xp_drive --build-type ament_python --license Apache-2.0 --node-name drive_node --description "toy drive sim for lesson 06"`; read `setup.py` | `console_scripts` contains `drive_node = xp_drive.drive_node:main`; scaffold ships `LICENSE`, `py.typed`, five `test/test_*.py` linters |
| The scaffold's `test_copyright` starts disabled | read `test/test_copyright.py` | `@pytest.mark.skip(reason='No copyright header has been placed in the generated source file.')` — the toy removes it, and the assignment's `mower_sim` must too (lesson 05 §11) |
| Linters run on the very first `colcon test` and catch dead imports | built the toy with an unused import; ran `colcon test` | `F401 'mower_math.add_kinematics.expand_covariance_diagonal' imported but unused` — flake8 failed the build until the import was used |
| Toy package: 5 unit tests + 5 linters, copyright enabled | `colcon test --packages-select xp_drive`; `colcon test-result --test-result-base build/xp_drive --verbose` | `Summary: 10 tests, 0 errors, 0 failures, 0 skipped`; `grep -o '<testcase' build/xp_drive/pytest.xml \| wc -l` = `10` |
| `mower_math` Phase A baseline unchanged by the toy workspace | `colcon test --packages-select mower_math` in the toy workspace | `Summary: 30 tests, 0 errors, 0 failures, 0 skipped` |
| Pure unit tests in isolation | `python3 -m pytest test/test_xp_config.py -v` from inside the package dir | `5 passed in 0.06s` |
| Node start log line | `ros2 run xp_drive drive_node` | `[INFO] [1791402812.556769631] [xp_drive]: xp_drive up at 20.0 Hz` (timestamps vary per run) |
| Published topics of a running node | `ros2 topic list` (domain 41) | `/xp_cmd_vel`, `/xp_imu`, `/xp_odom`, plus `/parameter_events`, `/rosout` |
| Initial pose is the zero pose | `ros2 topic echo /xp_odom --once --field pose.pose.position` and `... --field pose.pose.orientation` | `x: 0.0 y: 0.0 z: 0.0`; identity quaternion `(0.0, 0.0, 0.0, 1.0)` |
| Default QoS on the publisher | `ros2 topic info /xp_odom --verbose` | `Reliability: RELIABLE`, `History (Depth): KEEP_LAST (10)` |
| Timer rate matches `update_rate` | `timeout 6 ros2 topic hz /xp_odom --window 100` | `average rate: 19.991`, `min: 0.046s max: 0.054s std dev: 0.00100s window: 79` |
| Clamp applies once, at the inlet; `/odom.twist` reports applied values | published `{linear: {x: 0.4}, angular: {z: 5.0}}`, echoed `--field twist` | `linear.x: 0.4`, `angular.z: 0.8` — exactly `min(2.0, 0.4/0.5)`, the radius rule from lesson 05 |
| Straight-line ticks land on a deterministic grid | `ros2 topic echo /xp_odom --once --field pose.pose.position` during a 0.4 m/s run | `x: 1.8200000000000014` (`0.4 × 0.05 = 0.02` m/tick, 91 ticks), `y: 0.0` exactly |
| Sample-and-hold: silence keeps the last command; a stop freezes the pose | drove 0.4 m/s, sent `{}` stop, echoed pose twice 3 s apart | `x: 2.3800000000000017` both times; `twist` all zeros — nothing moved during silence |
| Invalid `update_rate` falls back with a warning naming the parameter | `ros2 run xp_drive drive_node --ros-args -p update_rate:=-5.0` | `[WARN] ... [xp_drive]: update_rate must be positive, falling back to 20.0 Hz`, then `xp_drive up at 20.0 Hz` |
| Array parameters are normal ROS parameters | `--ros-args -p imu_orientation_covariance:="[0.5, 0.5, 0.5]"` | `ros2 param get /xp_cov imu_orientation_covariance` → `Double values are: [0.5, 0.5, 0.5]` |
| A plain Python list assigns into `float64[9]` and `float64[36]` fields | same run, `ros2 topic echo /xp_imu --once --field orientation_covariance` | `[0.5 0.  0.  0.  0.5 0.  0.  0.  0.5]` (numpy-style print; with the default it printed `0.001` at indices 0, 4, 8 and zeros elsewhere) |
| Odometry twist is in the body frame | `ros2 interface show nav_msgs/msg/Odometry` | "The twist in this message should be specified in the coordinate frame given by the child_frame_id" |
| IMU covariance conventions | `ros2 interface show sensor_msgs/msg/Imu` | "If you have no estimate for one of the data elements … please set element 0 of the associated covariance matrix to -1"; "A covariance matrix of all zeros will be interpreted as 'covariance unknown'"; all three matrices are "Row major" |
| `ros2 topic pub` publication flags | `ros2 topic pub -h` | `-r, --rate N` (default 1 Hz), `-t, --times TIMES`, and `-w` — help text: "Defaults to 1 when using "-1"/"--once"/"--times", otherwise defaults to 0." — a `-t` burst waits for one subscriber before publishing |
| Entry point line the container runs | read `docker/entrypoint.sh` | line 7: `colcon test --packages-select mower_math mower_status` — must gain `mower_sim` |
| `.gitignore` has no bags entry yet | read root `.gitignore` | `ros2_ws/build|install|log/` present; no `ros2_ws/bags/` — the assignment adds it |
| Container build + entrypoint run, current tree | `docker build -t mower-sim:pre06 -f docker/Dockerfile .` then `docker run --rm -t mower-sim:pre06` | build ok; entrypoint prints `Summary: 30 tests, 0 errors, 0 failures, 0 skipped` and `Summary: 7 tests, 0 errors, 0 failures, 0 skipped` |
| `colcon test` with `mower_sim` named but missing | same image, `colcon build` then `colcon test --packages-select mower_math mower_status mower_sim` | `WARNING: colcon…: ignoring unknown package 'mower_sim' in --packages-select`, then the two existing packages still run `30` and `7` green — the entrypoint edit is safe before the package exists |
| `tf2_ros` present for the stretch goal | `ros2 pkg list \| grep -E '^tf2(_ros)?$'` | `tf2`, `tf2_ros` |

Not yet verified:

- The owner's `mower_sim` package itself — that is the assignment; its counts
  (`mower_sim` = 10 tests) and its runtime numbers become measured facts when
  the review runs them.
- A container image that includes `mower_sim` (this session's image was
  built from the pre-Phase-B tree; the acceptance in §7 gives the command).
- The `initial_x/y/yaw` replay determinism (Phase D's evidence loop, lesson
  07).

## 3. Options survey: how should the IMU covariance be configured?

One real design choice in this lesson, and it is about the message contract,
not the node: `sensor_msgs/Imu` carries three `float64[9]` covariance
matrices (orientation, angular velocity, linear acceleration), each
row-major about x, y, z. The sim only ever has a *diagonal* — three numbers
— yet the message needs nine, and the "unknown" convention needs element 0
to be `-1` when an estimate is absent.

| Option | Parameter shape | Accuracy | Cost / failure mode |
|---|---|---|---|
| **1. 3-element diagonal, expanded in code** | one `[vx, vy, vz]` parameter per matrix | exact for our diagonal-only model | low; one pure helper, tested, places values at indices 0, 4, 8 |
| 2. Full 9-element parameter | `[a..i]` you type by hand | same, but invites index slips | typing nine numbers where three are real; a transposed row is silent |
| 3. Single scalar per matrix | one `float` applied to all three axes | can't express per-axis differences | fine for orientation, wrong for anything asymmetric |

The platform provides the *target shape* — the message `float64[9]` — but
no tool fills it for you; the choice is the parameter's shape. Field robots
treat covariance parameters exactly as option 1: the `Imu.msg` doc itself
says "if all you know is the variance of each measurement, e.g. from the
datasheet, just put those along the diagonal". And decision 05 already chose
this shape for `Odometry`'s two 6×6 matrices (`pose_covariance_diagonal`,
`twist_covariance_diagonal`, expanded by Phase A's
`expand_covariance_diagonal`). Option 1 extends the same idea to size 9, so
the two message families behave identically. **Chosen: option 1**, recorded
in decision 06, with the "no estimate" case carried by the parameter default
(`[-1.0, 0.0, 0.0]` for the accelerometer), not by a special code path — the
`-1` flows through the same expansion and lands exactly at element 0.

## 4. Decision

`docs/decisions/06-sim-node-and-imu-covariance.md` — the IMU covariance
parameter shapes, the clamp-at-inlet wording of sample-and-hold, the
`sim_config.py` pure module, and the entrypoint/`.gitignore` wiring.

## 5. Lecture

### 5.1 The node as a state machine: sample-and-hold

Everything `sim_node` does this milestone is: remember the latest command,
and every tick, integrate it and publish two messages. The command path is
the interesting part, because of *when* the clamp runs.

```
               ┌──────────────────────────────────────────────┐
  /cmd_vel ──► │ on_cmd:  limit_twist(limit_twist once)        │
  (Twist)      │          self.v, self.w = clamped values      │  ── held state
               └──────────────────────────────────────────────┘
                              ▲ sample-and-hold
                              │ (no watchdog until M4)
               ┌──────────────────────────────────────────────┐
  timer every  │ on_tick: step_unicycle(x, y, yaw; v, w, dt)   │
  dt = 1/rate  │          build Odometry + Imu, publish both   │
               └──────────────────────────────────────────────┘
```

Three properties of this shape are the M1 contract:

**Applied, not raw.** `limit_twist` runs in `on_cmd`, exactly once per
command. The values the node stores — and later publishes as
`/odom.twist.twist.linear.x` and `/odom.twist.twist.angular.z` — are the
*clamped* values, i.e. what the robot actually did. This is what makes the
turning-radius requirement measurable: an acceptance check reads the applied
twist back off the wire and compares it to `min(max_angular, |v|/R_min)`
(your own Phase A table, lesson 05 §10). Over-commanding the toy —
`angular.z: 5.0` against a limit of `min(2.0, 0.4/0.5) = 0.8` — echoes back
exactly `0.8` (measured, verification table). Demote the clamp to the tick
callback and the node would *report* the raw 5.0 while moving at 0.8 — lying
to every consumer, including the Phase D compare.

**Sample-and-hold.** Between commands, the robot keeps doing the last thing
it was told. Decision 05 rejected a zero-on-silence watchdog until M4, and
the platform teleop (lesson 07's topic, but its shape is already known)
publishes *only on keypress* — silence is normal driving, not a fault.
Measured on the toy: after a `{linear: {x: 0.4}}` burst and a `{}` stop, the
pose echoed `x: 2.38` and, three seconds of silence later, still exactly
`x: 2.38` with twist all zeros. Frozen. And the corollary: a straight-line
burst followed by silence keeps *driving* — which is why Phase C's
straight-line acceptance has a range, not a point (the stop arrives on the
next command, whenever you send it).

**Relative topic names.** `'odom'`, `'imu'`, `'cmd_vel'`, bare — no leading
slash. At the root namespace they resolve to `/odom` etc., which is where
the CLI (record, play, spawn) uses absolute names. In M7 each mower runs in
its own namespace and this package works unchanged (decision 01's payoff).
The toy's names are `xp_odom`/`xp_imu`/`xp_cmd_vel` only so the toy cannot
collide with the real sim during a lesson.

### 5.2 Parameters, not magic numbers

AGENTS.md forbids hard-coded rates, distances, and names. `mower_sim`'s
entire configuration surface is the 15 parameters below — every one declared
with a module-level constant default (the lesson 03 pattern: defaults live
in a pure module so tests and the node share the same truth), every one
overridable with `--ros-args -p`, none of them optional:

| Parameter | Default | Why it exists |
|---|---|---|
| `update_rate` | `20.0` Hz | tick rate; the Phase D drift budget scales with its reciprocal |
| `max_linear_speed` | `1.0` m/s | clamp upper bound |
| `max_angular_speed` | `2.0` rad/s | spin + arc bound |
| `min_turn_radius` | `0.5` m | the spec's turning-radius limit |
| `initial_x`, `initial_y`, `initial_yaw` | `0.0`, `0.0`, `0.0` | **reproducible replay**: live and replay must start at the identical pose, or "same behavior" (M1's done-when) is not well-defined |
| `frame_id` | `odom` | the pose frame (`Odometry.header.frame_id`) |
| `child_frame_id` | `base_link` | the body frame (`Odometry.child_frame_id`, home of the twist) |
| `imu_frame_id` | `imu_link` | the `Imu.header.frame_id` |
| `pose_covariance_diagonal` | `[0.001]×6` | `/odom` pose uncertainty (x, y, z, roll, pitch, yaw) |
| `twist_covariance_diagonal` | `[0.001]×6` | `/odom` twist uncertainty |
| `imu_orientation_covariance` | `[0.001]×3` | IMU orientation uncertainty |
| `imu_angular_velocity_covariance` | `[0.001]×3` | IMU angular velocity uncertainty |
| `imu_linear_acceleration_covariance` | `[-1.0, 0.0, 0.0]` | **no accelerometer**: element 0 = `-1` is the message's "no estimate" marker (§5.3) |

Invalid values (negative rate, negative radius) fall back through a pure
helper from lesson 03's `positive_or`:

```python
def positive_or(value: float, fallback: float) -> float:
    """Return value when positive, otherwise the fallback default."""
    return value if value > 0.0 else fallback
```

The node does not silently swallow the fallback; it logs a warning that
names the parameter — because a typo'd launch file should be visible in the
log, and the acceptance check can `grep` it. Measured:

```
[WARN] [1791403554.716610867] [xp_drive]: update_rate must be positive, falling back to 20.0 Hz
[INFO] [1791403554.779772889] [xp_drive]: xp_drive up at 20.0 Hz
```

Note the type flow: `ros2 param get /xp_cov update_rate` prints `Double
value is: 20.0` for the scalar and `Double values are: [0.5, 0.5, 0.5]` for
an array — ROS 2 parameters are typed, the type is inferred from the
declaration's default, and an override must match it. That is why every read
in the node goes through `float(...)` or `str(...)` or `[float(v) for v in
...]`: the YAML/CLI layer hands you the declared type, and the casts pin
what the math expects.

### 5.3 The message contracts: Odometry and Imu

The spec pins these to standard message types so the sim is swappable at M8.
The contracts, with the installed message docs (measured, verification
table):

**`nav_msgs/msg/Odometry`** — "/odom":
- `header.frame_id` = pose frame (the `frame_id` parameter, default `odom`).
- `child_frame_id` = body frame (`base_link`).
- The message doc is a contract, not commentary: *"The pose in this message
  should be specified in the coordinate frame given by header.frame_id"* and
  *"The twist in this message should be specified in the coordinate frame
  given by the child_frame_id"*. So `pose.pose` is the pose of `base_link`
  in `odom` — the map-relative truth — while `twist.twist` is the velocity
  *of the body in its own frame*: `twist.twist.linear.x` is forward speed
  even when the robot faces some non-zero yaw. The sim's `v`/`w` are defined
  in the body frame (lesson 05's unicycle), so `linear.x = v`,
  `angular.z = w` is correct with no rotation math.
- Two `float64[36]` covariance matrices (pose, twist), row-major for the
  6-tuple (x, y, z, roll, pitch, yaw) — expanded from the 6-element
  parameters by Phase A's `expand_covariance_diagonal` (diagonal at indices
  0, 7, 14, 21, 28, 35).

**`sensor_msgs/msg/Imu`** — "/imu":
- `orientation` = absolute attitude as a quaternion. This sim *knows* its
  heading (it integrates it), so the "IMU" gives absolute yaw, not a
  dead-reckoned attitude — the honest read of `(0, 0, sin(yaw/2),
  cos(yaw/2))` from `yaw_to_quaternion`.
- `angular_velocity.z` = the yaw rate `w` (body frame, same as the odom
  twist — REP-103's z-up sign convention).
- `linear_acceleration` = **not measured**. The sim has no accelerometer
  model. The message doc gives the exact way to say that: *"If you have no
  estimate for one of the data elements (e.g. your IMU doesn't produce an
  orientation estimate), please set element 0 of the associated covariance
  matrix to -1"*. So `linear_acceleration_covariance[0] = -1` (from the
  parameter default `[-1.0, 0.0, 0.0]`), and consumers like M2's EKF are
  taught to *"check for a value of -1 in the first element … and disregard
  the associated estimate"*. All-zero would also mean "unknown" per the
  doc, but `-1` is the precise "we decline to estimate this" — the explicit
  choice of decision 06. Orientation and angular velocity *are* produced,
  so their covariances are never `-1`.
- The three covariance matrices are `float64[9]`, *"Row major about x, y, z
  axes"* — element 0, 4, 8 are the x/y/z diagonal (§5.4).

Frames, one paragraph so the vocabulary is right: `odom` is a local,
drifting world frame (REP-105). For M1 it is perfect ground truth — there is
no localization yet, so the sim's pose *is* the truth the M2 EKF will try to
estimate. `base_link` is the robot body. The transform odom → base_link is
exactly the pose in `/odom`; the stretch goal broadcasts it. `imu_link` is
where an IMU would sit; with a pure point model it coincides with base_link
but keeps its own frame name so M8's hardware swap does not rename anything.

### 5.4 Two covariance shapes, one idea

Phase A taught the 6→36 expansion: a parameter carries only the six diagonal
entries; the helper places them at `i * 6 + i` and zeroes the rest. The IMU
case is the same idea at size 3→9 — and it is *mower_sim's* own pure helper
(decision 06: it is configuration contract, not general math; `mower_math`'s
30-test Phase A baseline stays frozen):

```python
def expand_imu_covariance(diagonal: list[float]) -> list[float]:
    """Expand a 3-element diagonal to a 9-element row-major 3x3 matrix."""
    if len(diagonal) != 3:
        raise ValueError('diagonal must have length 3')
    cov = [0.0] * 9
    for i, value in enumerate(diagonal):
        cov[i * 3 + i] = float(value)
    return cov
```

So `[0.001, 0.001, 0.001]` becomes `[0.001, 0, 0, 0, 0.001, 0, 0, 0,
0.001]` — measured live on the wire, and with an override too:

```
$ ros2 param get /xp_cov imu_orientation_covariance
Double values are: [0.5, 0.5, 0.5]

$ ros2 topic echo /xp_imu --once --field orientation_covariance
[0.5 0.  0.  0.  0.5 0.  0.  0.  0.5]
```

And the accel default `[-1.0, 0.0, 0.0]` flows through the *same* helper,
landing `-1` at exactly element 0. One function, two jobs, one tested path —
this is why the parameter shape decision (§3) matters: the `-1` convention
becomes a default value, not a special case in the node.

Two low-level facts the toy confirmed, both measured:

1. **A plain Python list assigns into a `float64[36]`/`float64[9]` field.**
   `odom.pose.covariance = self.pose_cov` works because rclpy's generated
   message classes accept sequences and convert; no numpy import needed at
   this size. (The `--field` echo of an array prints numpy-style
   `[0.5 0.  ...]`, which is just rclpy's repr of the field.)
2. **The `Odometry` twist covariance and the IMU's other two matrices are
   the same pattern** — the assignment's full parameter list has all five
   diagonals; the toy deliberately keeps only two to stay small (pose +
   IMU orientation), and the numbers land identically.

### 5.5 The tick pipeline

`on_tick` is the only place where time enters the model:

```python
self.x, self.y, self.yaw = step_unicycle(
    self.x, self.y, self.yaw, self.v, self.w, self.dt)
stamp = self.get_clock().now().to_msg()
qx, qy, qz, qw = yaw_to_quaternion(self.yaw)
```

- `self.dt = 1.0 / self.rate` is computed once in `__init__` — the model
  steps in *fixed* increments, exactly the Euler step lesson 05 taught, and
  exactly what makes the sim deterministic: every tick advances
  `v × dt` meters. Measured: at `v = 0.4`, `dt = 0.05` → 0.02 m per tick,
  and the echoed positions land on that grid (`1.8200… = 91 ticks`,
  `2.3800… = 119 ticks`, `y = 0.0` exactly for a straight line).
- `stamp = self.get_clock().now().to_msg()` — the same stamp goes into both
  messages so consumers can correlate odom and imu. (This is ROS *system*
  time; simulated time arrives with Gazebo at M8.)
- `yaw_to_quaternion` returns the pure tuple `(x, y, z, w)`; the node copies
  it into both `odom.pose.pose.orientation` and `imu.orientation`. Same
  heading, two messages, one source.

Message filling is explicit field-by-field assignment, not a constructor
call — generated messages have no useful constructors for these shapes, and
explicit assignment makes the frame mapping (§5.3) readable:

```python
odom = Odometry()
odom.header.stamp = stamp
odom.header.frame_id = self.frame_id
odom.child_frame_id = self.child_frame_id
odom.pose.pose.position.x = self.x
odom.pose.pose.position.y = self.y
odom.pose.pose.orientation.x = qx
...
odom.pose.covariance = self.pose_cov
odom.twist.twist.linear.x = self.v
odom.twist.twist.angular.z = self.w
self.pub_odom.publish(odom)
```

Why `linear.x` and `angular.z` only? The unicycle model is non-holonomic:
`linear.y`, `linear.z`, `angular.x`, `angular.y` are always zero for a
differential mower, and the message defaults them to `0.0` — you never need
to write them. (Ackermann or omnidirectional models would populate more.)

The publishers and the subscription are created once with depth 10 —
RELIABLE / KEEP_LAST 10, the ROS default, measured on the live topic
(verification table). Best-effort `sensor_data` QoS waits for Gazebo at M8;
at 20 Hz a lost command is worse than milliseconds of latency, and Phase D
replays need every command.

### 5.6 Testing the package: 5 new tests + 5 linters, zero skips

The five unit tests mirror Phase A's pattern — pure functions, no graph:

- `test_positive_or` (3 parametrized rows): positive stays, zero falls
  back, negative falls back.
- `test_expand_imu_covariance_layout`: `[0.1, 0.2, 0.3]` → the 9-element
  row-major diagonal, as literals.
- `test_expand_imu_covariance_rejects_wrong_length`: `pytest.raises`.

Measured on the toy: `5 passed in 0.06s` directly, and inside `colcon test`
the package reports `10 tests, 0 errors, 0 failures, 0 skipped` — the five
scaffold linters (copyright, flake8, mypy, pep257, xmllint) plus the five
unit tests, with `test_copyright` **enabled** (lesson 05 §11: remove the
scaffold's skip decorator, keep Apache headers on every file you write,
keep the scaffold's `LICENSE`). Two linter behaviors worth remembering from
this session's measurements:

- flake8's import order is enforced and greets new files immediately — the
  toy's first build failed with `F401 '...expand_covariance_diagonal'
  imported but unused` (a real caught bug: I had imported the 6→36 helper
  before I used it). Linters are part of the build loop from the first
  commit.
- mypy is non-strict here: it passes unannotated test files, but annotate
  the node and the pure module anyway — M2's C++ side will be stricter, and
  the annotations are what the worked example shows.

Also measured: `python3 -m pytest test/ -q` from inside the package runs
`10 passed` — the linters are pytest functions too, so a naive `pytest
test/` includes them. Use `test/test_xp_config.py` for the fast unit-only
loop and `colcon test` as the arbiter (lesson 03's rule).

### 5.7 Package wiring: entrypoint and .gitignore

M0's container (decision 04) runs `docker/entrypoint.sh`, which builds and
tests the workspace. Current line 7, read from the file:

```bash
colcon test --packages-select mower_math mower_status
```

The assignment adds `mower_sim` to that list. Measured: naming a package
that does not exist yet is harmless — colcon prints
`WARNING: colcon.colcon_core.package_selection: ignoring unknown package
'mower_sim' in --packages-select` and the known packages still run green.
So the edit is safe *before* `mower_sim` exists, and the acceptance (below)
proves it once the package is there: the container run then prints a third
Summary line, `mower_sim`'s 10 tests.

`.gitignore` (root) currently ignores `ros2_ws/build|install|log/` but
nothing under `ros2_ws/bags/`. Phase D's evidence lives in bags — recorded
sessions are artifacts, not source, and must never enter git. The assignment
adds `ros2_ws/bags/` (bags themselves arrive in lesson 07; the ignore line
goes in now so the directory is safe from day one).

## 6. Worked example: a toy drive node with clamped sample-and-hold

You build this in `/tmp/opencode/l06toy` — scratch, never in `ros2_ws/src/`
(the real sim is your assignment). The toy is the exact architecture of
`mower_sim` minus the parts Phase B's remaining work adds: topic names are
prefixed `xp_`, there are 9 parameters instead of 15 (no initial pose, no
twist/angular-velocity/accel covariances), and one of the toy's covariance
helpers is `mower_sim`'s own (`expand_imu_covariance`). Everything else —
clamp at the inlet, sample-and-hold, timer pipeline, message filling — is
the real thing, so the numbers below are the numbers your `sim_node` will
produce with the same commands.

### 6.1 Scaffold

```bash
mkdir -p /tmp/opencode/l06toy/src && cd /tmp/opencode/l06toy/src
cp -r /home/jamie/mower-sim/ros2_ws/src/mower_math .        # toy reuses Phase A
source /opt/ros/lyrical/setup.bash
ros2 pkg create xp_drive --build-type ament_python \
  --license Apache-2.0 --node-name drive_node \
  --description "toy drive sim for lesson 06"
```

Measured scaffold output: package format 3, version 0.0.0, and five test
files plus `drive_node.py`. Verify the entry point was generated:

```bash
cat xp_drive/setup.py
```

shows `'drive_node = xp_drive.drive_node:main'` under `entry_points` —
created by `--node-name`, not hand-written. Add the toy's dependencies to
`package.xml` (lesson 01 §8: package.xml is not decorative):

```xml
<depend>geometry_msgs</depend>
<depend>mower_math</depend>
<depend>nav_msgs</depend>
<depend>rclpy</depend>
<depend>sensor_msgs</depend>
```

### 6.2 The pure module — `xp_drive/xp_drive/xp_config.py`

```python
"""Pure configuration helpers for the lesson 06 toy drive node."""

DEFAULT_UPDATE_RATE: float = 20.0
DEFAULT_MAX_LINEAR_SPEED: float = 1.0
DEFAULT_MAX_ANGULAR_SPEED: float = 2.0
DEFAULT_MIN_TURN_RADIUS: float = 0.5
DEFAULT_FRAME_ID: str = 'odom'
DEFAULT_CHILD_FRAME_ID: str = 'base_link'
DEFAULT_IMU_FRAME_ID: str = 'imu_link'
DEFAULT_POSE_COVARIANCE_DIAGONAL: list[float] = [
    0.001, 0.001, 0.001, 0.001, 0.001, 0.001,
]
DEFAULT_IMU_ORIENTATION_COVARIANCE: list[float] = [0.001, 0.001, 0.001]


def positive_or(value: float, fallback: float) -> float:
    """Return value when positive, otherwise the fallback default."""
    return value if value > 0.0 else fallback


def expand_imu_covariance(diagonal: list[float]) -> list[float]:
    """Expand a 3-element diagonal to a 9-element row-major 3x3 matrix."""
    if len(diagonal) != 3:
        raise ValueError('diagonal must have length 3')
    cov = [0.0] * 9
    for i, value in enumerate(diagonal):
        cov[i * 3 + i] = float(value)
    return cov
```

(Full listing; the Apache header from the scaffold convention goes on top —
the copyright linter enforces it. Lines 17–27: every default is a named
constant, because tests and the node must share the same truth. Lines 30–32:
`positive_or` from lesson 03. Lines 35–42: §5.4's 3→9 expansion — note the
`ValueError` is part of the contract, asserted by a test.)

### 6.3 The node — `xp_drive/xp_drive/drive_node.py` (scaffold's `main()` replaced)

Imports first (the order is flake8-enforced; the grouping is alphabetical
within each section):

```python
from geometry_msgs.msg import Twist
from mower_math.add_kinematics import (
    expand_covariance_diagonal,
    limit_twist,
    step_unicycle,
    yaw_to_quaternion,
)
from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Imu

from xp_drive.xp_config import (
    DEFAULT_CHILD_FRAME_ID,
    DEFAULT_FRAME_ID,
    DEFAULT_IMU_FRAME_ID,
    DEFAULT_IMU_ORIENTATION_COVARIANCE,
    DEFAULT_MAX_ANGULAR_SPEED,
    DEFAULT_MAX_LINEAR_SPEED,
    DEFAULT_MIN_TURN_RADIUS,
    DEFAULT_POSE_COVARIANCE_DIAGONAL,
    DEFAULT_UPDATE_RATE,
    expand_imu_covariance,
    positive_or,
)
```

The constructor, in three phases — declare, read/validate, wire:

```python
class DriveNode(Node):
    """Hold the last command and integrate it into odom and IMU messages."""

    def __init__(self) -> None:
        super().__init__('xp_drive')
        self.declare_parameter('update_rate', DEFAULT_UPDATE_RATE)
        self.declare_parameter('max_linear_speed', DEFAULT_MAX_LINEAR_SPEED)
        self.declare_parameter('max_angular_speed', DEFAULT_MAX_ANGULAR_SPEED)
        self.declare_parameter('min_turn_radius', DEFAULT_MIN_TURN_RADIUS)
        self.declare_parameter('frame_id', DEFAULT_FRAME_ID)
        self.declare_parameter('child_frame_id', DEFAULT_CHILD_FRAME_ID)
        self.declare_parameter('imu_frame_id', DEFAULT_IMU_FRAME_ID)
        self.declare_parameter(
            'pose_covariance_diagonal', DEFAULT_POSE_COVARIANCE_DIAGONAL)
        self.declare_parameter(
            'imu_orientation_covariance', DEFAULT_IMU_ORIENTATION_COVARIANCE)
```

Every parameter is declared before any is read — that is the rclpy contract;
a `get_parameter` for an undeclared name returns a default-valued result,
silently hiding typos. Declare all, then read all.

```python
        raw_rate = float(self.get_parameter('update_rate').value)
        self.rate = positive_or(raw_rate, DEFAULT_UPDATE_RATE)
        if self.rate != raw_rate:
            self.get_logger().warning(
                f'update_rate must be positive, falling back to '
                f'{self.rate} Hz')
        self.dt = 1.0 / self.rate
        self.max_linear = positive_or(
            float(self.get_parameter('max_linear_speed').value),
            DEFAULT_MAX_LINEAR_SPEED)
        self.max_angular = positive_or(
            float(self.get_parameter('max_angular_speed').value),
            DEFAULT_MAX_ANGULAR_SPEED)
        self.min_radius = positive_or(
            float(self.get_parameter('min_turn_radius').value),
            DEFAULT_MIN_TURN_RADIUS)
        self.frame_id = str(self.get_parameter('frame_id').value)
        self.child_frame_id = str(self.get_parameter('child_frame_id').value)
        self.imu_frame_id = str(self.get_parameter('imu_frame_id').value)
        raw_pose_cov = [float(v) for v in
                        self.get_parameter('pose_covariance_diagonal').value]
        self.pose_cov = expand_covariance_diagonal(raw_pose_cov)
        raw_imu_cov = [float(v) for v in
                       self.get_parameter('imu_orientation_covariance').value]
        self.imu_orientation_cov = expand_imu_covariance(raw_imu_cov)
```

Reading is `float(...)`/`str(...)`/list-comprehension casts, because the
parameter type is inferred from the declaration's default (§5.2). The raw
value and the fallback are compared for the warning — the pure decision is
`positive_or`'s; the log line is the node's. Covariance expansion happens
once, here, not per tick: `expand_covariance_diagonal` (Phase A, 6→36) and
`expand_imu_covariance` (ours, 3→9) both run in `__init__`, and the tick
path only assigns.

```python
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.v = 0.0
        self.w = 0.0

        self.pub_odom = self.create_publisher(Odometry, 'xp_odom', 10)
        self.pub_imu = self.create_publisher(Imu, 'xp_imu', 10)
        self.create_subscription(Twist, 'xp_cmd_vel', self.on_cmd, 10)
        self.create_timer(self.dt, self.on_tick)
        self.get_logger().info(f'xp_drive up at {self.rate} Hz')
```

State is five floats. There is no state machine library, no queue, no
watchdog — sample-and-hold *is* these five floats. Then the wire-up in four
lines: two publishers, one subscription, one timer. Topic names are
relative; depth 10 is the default QoS profile (§5.5).

The two callbacks are the whole behavior:

```python
    def on_cmd(self, msg: Twist) -> None:
        """Clamp the incoming command once, then hold it until the next."""
        self.v, self.w = limit_twist(
            msg.linear.x, msg.angular.z,
            self.max_linear, self.max_angular, self.min_radius)

    def on_tick(self) -> None:
        """Advance the model one step and publish odom and imu."""
        self.x, self.y, self.yaw = step_unicycle(
            self.x, self.y, self.yaw, self.v, self.w, self.dt)
        stamp = self.get_clock().now().to_msg()
        qx, qy, qz, qw = yaw_to_quaternion(self.yaw)

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self.frame_id
        odom.child_frame_id = self.child_frame_id
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.pose.covariance = self.pose_cov
        odom.twist.twist.linear.x = self.v
        odom.twist.twist.angular.z = self.w
        self.pub_odom.publish(odom)

        imu = Imu()
        imu.header.stamp = stamp
        imu.header.frame_id = self.imu_frame_id
        imu.orientation.x = qx
        imu.orientation.y = qy
        imu.orientation.z = qz
        imu.orientation.w = qw
        imu.orientation_covariance = self.imu_orientation_cov
        imu.angular_velocity.z = self.w
        self.pub_imu.publish(imu)
```

Everything in `on_tick` was taught in §5.5: clamp happened upstream (at the
inlet), integration is one pure call, both messages share `stamp` and the
same quaternion, only the diagonal slots of the covariances are non-zero.

And the lesson-01 §14 main with `ExternalShutdownException` (rclpy raises it
when the process is asked to stop; catching it keeps the `finally` shutdown
path clean):

```python
def main() -> None:
    rclpy.init()
    node = DriveNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
```

### 6.4 Tests — `xp_drive/test/test_xp_config.py`

```python
"""Unit tests for the pure configuration helpers."""

import pytest

from xp_drive.xp_config import expand_imu_covariance, positive_or


@pytest.mark.parametrize(
    'value,fallback,expected',
    [
        (1.0, 0.5, 1.0),
        (0.0, 0.5, 0.5),
        (-2.0, 0.5, 0.5),
    ],
)
def test_positive_or(value: float, fallback: float, expected: float) -> None:
    assert positive_or(value, fallback) == expected


def test_expand_imu_covariance_layout() -> None:
    assert expand_imu_covariance([0.1, 0.2, 0.3]) == [
        0.1, 0.0, 0.0,
        0.0, 0.2, 0.0,
        0.0, 0.0, 0.3,
    ]


def test_expand_imu_covariance_rejects_wrong_length() -> None:
    with pytest.raises(ValueError):
        expand_imu_covariance([0.1, 0.2])
```

The layout assertion is exact `==` (it is integer-index placement, no trig),
and the wrong-length case asserts the `ValueError` as specified behavior —
both inherited from Phase A's conventions (lesson 05 §10). Also remove the
`@pytest.mark.skip` from `test/test_copyright.py` (lesson 05 §11) and keep
the Apache header on the three files you wrote (the scaffold's own
`test/` template files keep their OSRF header — those are template files,
not yours to re-license).

### 6.5 Build and test

```bash
cd /tmp/opencode/l06toy
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
```

Measured: `Summary: 2 packages finished [4.05s]`. Then the fast unit loop
and the arbiter:

```bash
cd src/xp_drive
python3 -m pytest test/test_xp_config.py -v
```

```
test/test_xp_config.py::test_positive_or[1.0-0.5-1.0] PASSED             [ 20%]
test/test_xp_config.py::test_positive_or[0.0-0.5-0.5] PASSED             [ 40%]
test/test_xp_config.py::test_positive_or[-2.0-0.5-0.5] PASSED            [ 60%]
test/test_xp_config.py::test_expand_imu_covariance_layout PASSED         [ 80%]
test/test_xp_config.py::test_expand_imu_covariance_rejects_wrong_length PASSED [100%]

============================== 5 passed in 0.06s ===============================
```

```bash
cd /tmp/opencode/l06toy && source install/setup.bash
colcon test
colcon test-result --test-result-base build/xp_drive --verbose
colcon test-result --test-result-base build/mower_math
```

Measured:

```
Summary: 2 packages finished [27.3s]
Summary: 10 tests, 0 errors, 0 failures, 0 skipped
Summary: 30 tests, 0 errors, 0 failures, 0 skipped
```

10 = 5 linters + 5 unit tests, **zero skipped** (`test_copyright` enabled;
the template's skip decorator is gone). `grep -o '<testcase'
build/xp_drive/pytest.xml | wc -l` → `10` if you want the count made of
counts. And `mower_math`'s Phase A baseline is untouched by the toy
workspace: 30.

### 6.6 Run it

One terminal (or backgrounded):

```bash
export ROS_DOMAIN_ID=41
source /opt/ros/lyrical/setup.bash
cd /tmp/opencode/l06toy && source install/setup.bash
ros2 run xp_drive drive_node
```

Measured start line:

```
[INFO] [1791402812.556769631] [xp_drive]: xp_drive up at 20.0 Hz
```

From another shell, same domain:

```bash
ros2 topic list
```

```
/parameter_events
/rosout
/xp_cmd_vel
/xp_imu
/xp_odom
```

The initial pose is the zero pose:

```bash
ros2 topic echo /xp_odom --once --field pose.pose.position
ros2 topic echo /xp_odom --once --field pose.pose.orientation
```

```
x: 0.0
y: 0.0
z: 0.0
---
x: 0.0
y: 0.0
z: 0.0
w: 1.0
```

`ros2 topic hz` confirms the timer matches the parameter:

```bash
timeout 6 ros2 topic hz /xp_odom --window 100
```

```
average rate: 19.991
	min: 0.046s max: 0.054s std dev: 0.00100s window: 79
```

### 6.7 The two measured behaviors the assignment's acceptance reuses

**The clamp, read off the wire.** Over-command and read the applied twist:

```bash
ros2 topic pub -r 5 /xp_cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.4}, angular: {z: 5.0}}' -t 20
ros2 topic echo /xp_odom --once --field twist
```

Measured while the burst was held:

```
twist:
  linear:
    x: 0.4
    y: 0.0
    z: 0.0
  angular:
    x: 0.0
    y: 0.0
    z: 0.8
...
```

`w = 0.8` is `min(max_angular=2.0, |v|/R_min = 0.4/0.5)` — the radius rule
from lesson 05, appearing in the live stream as the applied value. (`-t 20`
with `-r 5` publishes twenty messages then exits; the help text confirms
`-t` waits for one subscriber before starting.)

**Sample-and-hold freezes on silence.** Drive, stop, then watch the pose
for three seconds of silence (measured, from the verification table):

```
--- pose right after stop:
x: 2.3800000000000017
y: 0.0
z: 0.0
--- pose 3s later (silence):
x: 2.3800000000000017
y: 0.0
z: 0.0
--- twist after stop:
linear:  x: 0.0  y: 0.0  z: 0.0
angular: x: 0.0  y: 0.0  z: 0.0
```

And the fallback warning — start another instance with a broken parameter
on a **separate `ROS_DOMAIN_ID`** (or stop the first instance first: two
publishers on one topic make `--once` ambiguous, which is the M7 namespace
problem in miniature):

```bash
timeout 6 ros2 run xp_drive drive_node --ros-args -p update_rate:=-5.0
```

```
[WARN] [1791403554.716610867] [xp_drive]: update_rate must be positive, falling back to 20.0 Hz
[INFO] [1791403554.779772889] [xp_drive]: xp_drive up at 20.0 Hz
```

Kill every node you started before moving on (`ps aux | grep drive_node`)
— AGENTS.md keeps processes clean.

## 7. Assignment — `mower_sim`, Phase B (part 1)

Build the real package in `ros2_ws/src/`. Phase B completes in two lessons:
this one (the node, its parameters, its tests, the repo wiring) and lesson
07 (`bag_check.py` + the record/replay evidence loop). **M1's done-when is
not met by this lesson** — Phases C and D (runtime evidence, teleop, replay)
come after lesson 07.

1. **Scaffold.** `ros2 pkg create mower_sim --build-type ament_python
   --license Apache-2.0 --node-name sim_node --description "deterministic 2D
   mower sim"` in `ros2_ws/src` — `--node-name sim_node` generates
   `mower_sim/mower_sim/sim_node.py` and registers the `sim_node` entry
   point in `setup.py` (verify with `cat setup.py`, like §6.1).
   Add `<depend>` entries for `geometry_msgs`, `mower_math`, `nav_msgs`,
   `rclpy`, `sensor_msgs`. Keep the five scaffold linters; remove the skip
   decorator from `test/test_copyright.py` (lesson 05 §11) and put your
   Apache header on every file you write.
2. **`mower_sim/mower_sim/sim_config.py`** (pure — no `rclpy` import):
   every default from the §5.2 table as a module constant; `positive_or`;
   `expand_imu_covariance`. Node and tests import from here only.
3. **`mower_sim/mower_sim/sim_node.py`**: `SimNode(Node)` named `sim_node`,
   subscribing relative `cmd_vel`, publishing relative `odom` and `imu`;
   timer at `update_rate`; clamped sample-and-hold with `limit_twist` at the
   inlet; `/odom.twist` and `/imu.angular_velocity` carry the **applied**
   twist; `initial_x/y/yaw` read into the start pose, so a fresh node starts
   where a replay needs it (Phase D); every covariance from §5.2's table,
   including `imu_linear_acceleration_covariance` default `[-1.0, 0.0,
0.0]` → element 0 = `-1` on the wire; the same "falls back, warn naming
    the parameter" treatment for all four numeric parameters — `update_rate`
    is shown in the worked example; give `max_linear_speed`,
    `max_angular_speed`, and `min_turn_radius` the same two lines (or factor
    a private helper — your call). The toy's callbacks, filling, and `main`
    are the shape; the parameter table is the difference.
4. **Tests.** `mower_sim/test/test_sim_config.py`: the same five cases as
   the toy (3 `positive_or` rows + 2 covariance cases). Expected: `colcon
   test --packages-select mower_sim` reports **10 tests, 0 errors, 0
   failures, 0 skipped**.
5. **Wiring.** `docker/entrypoint.sh` line 7 gains `mower_sim` in
   `--packages-select`; root `.gitignore` gains `ros2_ws/bags/`.

**Acceptance criteria (each is a command):**

- (A) Host tests:
  ```bash
  cd ros2_ws && source /opt/ros/lyrical/setup.bash
  colcon build --symlink-install
  colcon test && colcon test-result --test-result-base build/mower_sim --verbose
  ```
  `Summary: 10 tests, 0 errors, 0 failures, 0 skipped` for `mower_sim`,
  and `mower_math` still `30`, `mower_status` still `7` — nothing else
  moved. `grep -rn "import rclpy" ros2_ws/src/mower_sim/mower_sim/sim_config.py`
  prints nothing (purity).
- (B) Interfaces and initial state (fresh node, dedicated domain):
  `ros2 topic list` shows `/cmd_vel`, `/odom`, `/imu`;
  `ros2 topic info /odom --verbose` shows RELIABLE / KEEP_LAST 10;
  `ros2 topic echo /odom --once --field pose.pose.position` prints
  `x: 0.0 y: 0.0 z: 0.0` and `--field pose.pose.orientation` prints the
  identity quaternion.
- (C) The clamp, live: publish `{linear: {x: 0.4}, angular: {z: 5.0}}` at
  5 Hz (`-t 20`) and echo `/odom --once --field twist` — must show
  `linear.x: 0.4`, `angular.z: 0.8` (exactly `0.4/0.5`).
- (D) The fallback: launch with `--ros-args -p update_rate:=-5.0` — the log
  contains `update_rate must be positive, falling back to 20.0 Hz` and the
  node comes up at 20 Hz; `ros2 topic hz /odom` reports ≈ 20.
- (E) Parameters reach the wire: launch with
  `--ros-args -p imu_orientation_covariance:="[0.5, 0.5, 0.5]"` —
  `ros2 topic echo /imu --once --field orientation_covariance` prints the
  diagonal `0.5` on indices 0/4/8; without the override it prints `0.001`.
- (F) Silence is held: drive with a short `{linear: {x: 0.4}}` burst, stop
  with `{}`, and echo `--field pose.pose.position` twice three seconds
  apart — identical values, twist zeros.
- (G) Container:
  ```bash
  docker build -t mower-sim:m1-phase-b -f docker/Dockerfile .
  docker run --rm -t mower-sim:m1-phase-b
  ```
  three `Summary:` lines — `30`, `7`, and `10` — all zero failures, zero
  skips.
- (H) The `.gitignore` line `ros2_ws/bags/` exists; `entrypoint.sh`'s
  `--packages-select` names all three packages.

**Stretch goal — make the mower visible.** Broadcast the `odom → base_link`
transform from `sim_node` with `tf2_ros.TransformBroadcaster` (verified
present on this host) at `update_rate`: one `TransformStamped` per tick with
`header.frame_id`/`child_frame_id` from the same parameters, `translation`
= (x, y, 0), `rotation` = `yaw_to_quaternion`. Then `rviz2` can display
`base_link` (and, later, the EKF's child frame). Direction: add `tf2_ros`
to `package.xml`, construct the broadcaster once in `__init__` next to the
publishers, and publish in `on_tick` after `self.x/y/yaw` update. Real
robots publish this transform for exactly the same reason — every consumer
(and every visualization tool) resolves frames rather than re-deriving
poses.

## 8. Where this leaves M1

After this lesson, M1 has a moving, deterministic sim publishing standard
messages from parameters, with the clamp proven on the wire and tests green
on host and in the container. Lesson 07 adds `bag_check.py` and the
record/replay protocol; Phases C and D then produce the runtime evidence
(straight line, radius clamp, teleop drive, replay equivalence) that M1's
done-when demands. M2 then replaces the sim's perfect truth with a noisy
sensor model so an EKF has something to estimate — REP-145's IMU semantics
get verified there, as decision 05 planned.

## 9. Commit

Small, one concept per commit: the package + node + tests as
`M1 (Phase B): add mower_sim node with parameters, bounds, and tests`
(including the entrypoint and `.gitignore` lines). Docs get their own
commit: lesson 06 + decision 06 + hints. Bags never enter git — the
`.gitignore` line you just added is why.