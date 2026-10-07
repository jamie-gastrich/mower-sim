# 05 - Kinematics pure functions (Phase A of M1)

**Milestone:** M1 · **Language:** Python · **Prerequisite:** Lessons 03 and 04 ([reviews 03, 04 passed](../reviews/)), and [Decision 05 — Kinematics model and M1 sim interfaces](../decisions/05-kinematics-and-m1-sim-interfaces.md)

**Concepts this assignment requires** — each item links to the section that teaches it:

- [Why the mower is modeled as a differential drive, and what `(v, ω)` means](#4-the-mower-as-a-differential-drive)
- [`limit_twist`: why the turning radius is enforced on `ω`, and why `v = 0` is special](#5-limit_twist-the-turning-radius-clamp)
- [`step_unicycle`: body-frame velocity, Euler integration, and the measured drift](#6-step_unicycle-integrating-the-model)
- [Wrapping angles and pinning the heading convention to the half-open range](#7-wrapping-angles-and-pinning-the-half-open-convention)
- [`yaw_to_quaternion`: why ROS orientations are quaternions, and the half-angle formula](#8-yaw_to_quaternion-why-orientation-is-a-quaternion)
- [`expand_covariance_diagonal`: covariance as 36 row-major floats](#9-expand_covariance_diagonal-covariance-as-36-floats)
- [Parametrized pytest cases, `pytest.approx`, `pytest.raises`, and the arithmetic to exactly 30 tests](#10-testing-the-functions-30-cases-approx-and-raises)
- [The scaffold's five linters on brand-new files — and what they do *not* check](#11-the-scaffolds-five-linters-on-brand-new-files)
- [Red to green on a toy package before touching `mower_math`](#12-worked-example-a-toy-pricing-package-red-to-green)
- [Assignment: Phase A in `mower_math`](#13-assignment-phase-a-in-mower_math)

---

## 1. Where this fits

M1 in the [spec](../../spec/mower-spec.md) is: *"Mower model and 2D sim. Differential-drive (or Ackermann; decided in the survey) kinematics with turning-radius limits. Sim publishes pose and a first sensor (odometry + IMU)."* Its done-when: *"teleop drives the mower; recorded bag replays the same behavior."*

This lesson is **Phase A of M1 only**. M1 splits into four phases:

- **Phase A (this lesson)**: pin the heading convention in `mower_math`, and add four pure functions — `limit_twist`, `step_unicycle`, `yaw_to_quaternion`, `expand_covariance_diagonal` — plus their 16 reference test cases. No ROS node, no `mower_sim` package, no bags, no teleop.
- **Phase B (next lesson)**: the `mower_sim` package and its `sim_node`: parameters, a clamped sample-and-hold command loop, publishers for `/odom` and `/imu`, a `bag_check.py` verification script, and the supporting `docker/`/`.gitignore` changes.
- **Phase C**: verify the interfaces and run scripted straight-line and radius checks.
- **Phase D**: teleop + bag replay equivalence, which is what actually satisfies M1's done-when.

**After Phase A, M1 is not done.** The done-when needs B–D.

Why start with pure functions instead of a node? Because of the rule you have been following since lesson 03: logic lives outside `rclpy` so it can be tested without a running graph. `mower_math` is the permanent home for that logic (decision 01, review 03) — M1's kinematics, M2's EKF preprocessing, and M3's cross-track error all graft onto it. The functions you write here are the part of the sim that *is* the model; the node in Phase B is only the part that publishes messages. Keeping them apart is what lets us test the physics at 16 rows of pytest in milliseconds instead of launching a robot to find out the radius clamp is wrong.

This lesson makes **no new decision**: decision 05 already chose the model, pinned the heading convention, and fixed the topic/message interfaces. Section 3 summarises it and §2 re-verifies every measurement behind it.

## 2. Verification table

Everything below was run on this machine before being written down. Scratch work lived in `/tmp/opencode/` (`l05base` = pristine copy, `l05red2` = red→green proof, `l05phaseA` = the finished Phase A state, `l05toy2` = the toy package, `l05tree` = a copy of your working tree) and is deleted after this lesson. Scratch runs used `ROS_DOMAIN_ID=63`.

| Claim | How it was checked | Result |
|---|---|---|
| `mower_math` on a pristine checkout runs 13 tests | `git archive HEAD ros2_ws/src/mower_math` into scratch, `colcon build` + `colcon test` + `colcon test-result` | `Summary: 13 tests, 0 errors, 0 failures, 0 skipped` (5 linters + 3 `clamp` rows + 5 `wrap` rows) |
| Pristine `wrap_angle_rad` reaches **both** `±π` exactly | `python3` calling `wrap(math.pi)` / `wrap(-math.pi)` on the pristine copy | `3.141592653589793` and `-3.141592653589793` |
| Pristine docstring says `[-π, π]`, pristine tests assert `-math_pi < result <= math_pi`, and the `-π` input is absent from the row list | `sed -n '/def wrap_angle_rad/,/^$/p' math_utils.py`; `grep -n -A14 parametrize test/test_math_utils.py` | docstring `"""Wrap an angle in radians to the range [-π, π]."""`; rows `[3.5, -3.5, 10.0, -10.0, 3.1415926535]` |
| The float behind `-π`: `sin(-π)` is not zero | `repr(math.sin(-math.pi))`, `math.atan2(0.0, -1.0)`, `math.atan2(-0.0, -1.0)` | `-1.2246467991473532e-16`; `atan2(0.0, -1.0) = 3.141592653589793`; `atan2(-0.0, -1.0) = -3.141592653589793` |
| Of five neighbouring doubles, only the input `-π` itself wraps to exactly `-π` | wrapped `-math.pi + k * math.ulp(math.pi)` for `k = -2..2` | only `k = 0` returned `-3.141592653589793`; the others returned `-π ± a few ulp` |
| Adding the `-π` row to the pristine test **fails** | pristine copy + the new row, `python3 -m pytest test/test_math_utils.py -v` | `1 failed, 8 passed in 0.06s`, exit 1, `assert -3.141592653589793 < -3.141592653589793` |
| The guard + docstring make it pass | same file after the fix | `9 passed in 0.06s`, exit 0 |
| Full Phase A state (fix + 4 functions + 16 cases) | `colcon build`, `colcon test`, `colcon test-result --verbose` in `l05phaseA` | `Summary: 30 tests, 0 errors, 0 failures, 0 skipped` |
| 30 is really 30 separate test cases | `grep -o '<testcase' build/mower_math/pytest.xml \| wc -l` | `30` |
| Kinematics file alone | `python3 -m pytest test/test_add_kinematics.py -v` (from inside `mower_math/`) | `16 passed in 0.07s` |
| The fast "just the radius clamp" loop | `python3 -m pytest test/test_add_kinematics.py -k limit_twist -v` | `7 passed, 9 deselected in 0.04s` |
| `limit_twist` behaviour, every row in §5's table | REPL calls against the Phase A copy | all seven rows measured, listed in §5 |
| `step_unicycle` behaviour, every row in §6's table | REPL calls against the Phase A copy | all five rows measured, listed in §6 |
| Euler integration error vs the exact arc | two integrators side by side, `dt = 0.05, v = 1, ω = 1` (radius 1 m), heading wrapped each step like `step_unicycle` does | 1 step: `0.0012499131968556475 m`; 31 steps / 1.55 s: `0.03498701863233074 m`; yaw difference `0.0` (both do the same addition) |
| `yaw_to_quaternion(π/2)` — the two halves differ by 1 ulp | REPL | `(0.0, 0.0, 0.7071067811865475, 0.7071067811865476)` |
| That quaternion is a real z-rotation of unit length | rotate `(1, 0, 0)` by the returned quaternion; `math.dist(q, (0,0,0,1))`-style norm check | lands on `(cos yaw, sin yaw)` to 15 decimals for yaw = 0, 1.0, -1.0, 12.3; `|q| = 1.0000000000000002` for the π/2 case |
| Why not Euler angles: gimbal lock is real | `rpy = (0.7, π/2, 0)` vs `(0, π/2, -0.7)` vs `(0.3, π/2, -0.4)` → build rotation matrices, compare | all three equal: `True`; same test at pitch `0.1` → `False` |
| `expand_covariance_diagonal` output shape | REPL: `len()`, non-zero indices, wrong-length call | `36`; `[0, 7, 14, 21, 28, 35]`; `ValueError: diagonal must have length 6` |
| ROS messages say what §8/§9 assume | `cat /opt/ros/lyrical/share/{nav_msgs/msg/Odometry,geometry_msgs/msg/PoseWithCovariance,sensor_msgs/msg/Imu,geometry_msgs/msg/Quaternion}.msg` | Odometry twist is in `child_frame_id`; `float64[36]` "Row-major representation of the 6x6 covariance matrix", axes `(x, y, z, rotation about X, Y, Z)`; Imu has three `float64[9]` "Row major" matrices and the "set element 0 … to -1" rule; Quaternion defaults `0 0 0 1` |
| ROS frame/rotation conventions | read REP-103 from the official repo (`raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0103.rst`) | "x forward, y left, z up", "right handed"; "the yaw component of orientation increases as the child frame rotates counter-clockwise"; rotation preference "1. quaternion — Compact representation, No singularities"; "Euler angles are generally discouraged" |
| The platform does **not** ship a kinematic model; it **does** ship the messages | `ros2 pkg list` (count, presence greps, model grep) | `321` packages; `teleop_twist_keyboard`, `geometry_msgs`, `nav_msgs`, `sensor_msgs`, `tf2_ros`, `rosbag2`, `diagnostic_msgs` present; `grep -iE "kinematic\|diff_drive\|ackermann\|controller"` → no match |
| In-place spin is a real teleop input, not an invention | installed `teleop_twist_keyboard.py` (v2.4.1 from its `package.xml`): `moveBindings` + the publish block | `'j': (0, 0, 0, 1)`, `'l': (0, 0, 0, -1)` → `twist.linear.x = x * speed`, `twist.angular.z = th * turn` → zero linear, non-zero yaw rate |
| ament_flake8's real config | `cat .../ament_flake8/configuration/ament_flake8.ini` | `max-line-length = 99`, `import-order-style = google`, `extend-ignore = B902,C816,D100,...,D404,I202` |
| A long **code** line fails; a long **comment** line does not | 100-char comment line (passed), then a 104-char code line through `python3 -m flake8` | comment: no error; code: `xp_pricing/longline.py:3:100: E501 line too long (104 > 99 characters)` |
| Import order is enforced | swapped `import pytest`/`from xp_pricing...` in the toy, ran the flake8 test | `./test/test_pricing.py:2:1: I100 Import statements are in the wrong order. 'import pytest' should be before 'from xp_pricing.pricing import ...'` |
| A missing blank line between import groups is enforced | your working tree's leftover `add_kinematics.py`, flake8 test in `l05tree` | `./mower_math/add_kinematics.py:16:1: I201 Missing newline between import groups. 'from mower_math...' is identified as Third Party and 'import math' is identified as Stdlib.` |
| Single quotes are enforced by a plugin | same run (`flake8-quotes` is in the installed plugin list) | `Q000 Double quotes found but single quotes preferred` |
| **Docstrings are not linted** | deleted a function docstring from the toy, ran the pep257 test | `test_pep257 PASSED`; the ignore list is `_ament_ignore = ['D100', ..., 'D107', 'D203', 'D212', 'D404']` in the installed `ament_pep257/main.py` |
| Unannotated code passes mypy (it is not strict) | toy `test_pricing.py` has no type hints at all; `test_mypy` passes in the colcon run | `13 tests, 0 errors, 0 failures, 1 skipped` for the toy |
| A fresh `ros2 pkg create` package ships `test_copyright` **skipped** | read the installed template `ros2pkg/resource/ament_python/test_copyright.py.em`; toy run shows the skip | template line: `@pytest.mark.skip(reason='No copyright header has been placed in the generated source file.')` — `mower_math`'s copy has that decorator removed (lesson 03), which is why it reports 0 skips |
| Toy package: red → green → colcon | full §12 sequence in the scratch copy `l05toy2` | red `3 failed, 5 passed in 0.07s` exit 1; green `8 passed in 0.08s` exit 0; colcon `Summary: 13 tests, 0 errors, 0 failures, 1 skipped` |
| The §13 acceptance battery passes as published | one script running build → test → test-result → count → sanity script → greps against `l05phaseA` | `Summary: 30 tests, 0 errors, 0 failures, 0 skipped`, `30`, `all sanity checks passed`, greps all as expected, exit `0` |
| Purity: `mower_math` has no ROS imports | `grep -rn "import rclpy\|import rclcpp" src/mower_math` on `l05phaseA` and on the pristine copy | no output (exit 1) in both |
| **State of your tree today**: the untracked leftovers are incomplete | `git status --short`; colcon on a copy of your tree (`l05tree`) | `?? ros2_ws/src/mower_math/mower_math/add_kinematics.py` (53 lines) and `?? .../test/test_add_kinematics.py` (**0 bytes**); the copy runs `13 tests, 0 errors, 1 failure, 0 skipped` — the failure is the `I201` above |

Not yet verified, and not part of this assignment: everything in Phases B–D (the `mower_sim` node, `/odom` + `/imu` publishing, bag recording/replay); running this lesson's tests inside the M0 container (lesson 04's flow applies, but it was not exercised for Phase A); how Phase B will fill the IMU's three 9-element covariance arrays from a 6-element parameter (an open question — §14); M2/M3 consumers of these functions (planned per decision 05 and the spec, not yet written).

## 3. Options survey: which kinematic model?

The assignment's only real design choice — three ways to turn `(commands, state)` into `(next state)` — was surveyed and recorded in [decision 05](../decisions/05-kinematics-and-m1-sim-interfaces.md). The condensed table, because you should re-read the reasoning rather than trust the summary:

| Option | Accuracy vs. a real mower | Cost / complexity | Failure modes | How field robots do it |
|---|---|---|---|---|
| **1. Differential drive (unicycle): state `(x, y, yaw)`, inputs `(v, ω)`, radius enforced by limiting `ω`** | exact for a machine that pivots about its own centre | two integrate-and-wrap equations, one clamp | none at normal speeds; wheel slip at high `ω/v` is unmodeled (acceptable in a 2D sim) | most commercial mowers are differential/twin-differential; stripes are driven by heading control |
| 2. Ackermann / bicycle: state `(x, y, yaw, steer)` | exact only if the machine is car-like | extra steer state with rate and range limits; radius singular at `v = 0` | radius meaningless while stopped; reversing with steer needs its own plan | row-crop tractors and some ride-ons |
| 3. Holonomic point: direct `(vx, vy, ω)` | not a mower at all | lowest | violates the spec's turning-radius requirement by construction | rare in mowing; common for warehouse AGVs |

**Platform check** (the rule: if ROS already provides the thing, it is one of the options): measured this install with `ros2 pkg list` — **no** installed package provides a kinematic model or a radius limiter (`kinematic|diff_drive|ackermann|controller` → no match), so option 1's equations are ours to write. What the platform *does* provide are the **interfaces**: `geometry_msgs`, `nav_msgs`, `sensor_msgs` are installed, and `teleop_twist_keyboard` (v2.4.1) already publishes `geometry_msgs/msg/Twist` — which is why the command contract in §5 is a `(v, ω)` pair in the first place.

**Chosen: option 1** — differential drive. Decision 05 records the reasons, the rejected options, and what would make us revisit it (a spec change, or a target mower that cannot pivot).

## 4. The mower as a differential drive

A differential-drive robot is two wheels on one axle: each wheel's speed sets the machine's forward speed and its turn rate. Nothing in the middle steers. The state you track is small — position and heading, `(x, y, yaw)` — and the input is equally small: `(v, ω)`, forward speed in m/s and yaw rate in rad/s. That is the whole model.

Two conventions come from ROS itself, and both are measured from [REP-103](https://www.ros.org/reps/rep-0103.html) (read from the official repository for §2):

> In relation to a body the standard is: x forward, y left, z up … All systems are right handed.

> By the right hand rule, the yaw component of orientation increases as the child frame rotates counter-clockwise.

So `yaw = 0` points along +x, positive `ω` turns counter-clockwise, and everything is SI (radians, metres, seconds). If you ever "fix" a turn that goes the wrong way by flipping a sign, you have broken the convention that every other ROS package assumes — fix your inputs instead.

Why is `(v, ω)` the contract rather than, say, `(left_wheel_speed, right_wheel_speed)`? Because that is what ROS messages carry: the cmd topic is `geometry_msgs/msg/Twist`, and the teleop tool you will drive in Phase D publishes exactly this pair — measured from its installed source, the key bindings are

```python
moveBindings = {
    'i': (1, 0, 0, 0),
    ...
    'j': (0, 0, 0, 1),
    'l': (0, 0, 0, -1),
```

and the publisher does `twist.linear.x = x * speed`, `twist.angular.z = th * turn`. The `j`/`l` keys command **zero linear, non-zero angular**: an in-place spin. Hold that thought for §5 — it is why the radius formula needs an escape hatch.

One more interface fact you will consume in Phase B, quoted from `nav_msgs/msg/Odometry.msg`:

```
# The twist in this message should be specified in the coordinate frame given by the child_frame_id
```

i.e. the velocities in `/odom` are **body-frame** velocities — the `(v, ω)` of §5, not a world-frame velocity vector. Writing the integrator in §6 with body-frame inputs is therefore not an arbitrary choice; it is the frame ROS hands you.

Real-world grounding: commercial mowers cut stripes by driving a heading and correcting drift — they are not following wheel encoders around a Ackermann arc. That is decision 05's option 1 in practice, and it is why the spec's M1 line says "kinematics with turning-radius limits": the limits exist because a real chassis cannot instantaneously take any `(v, ω)` you hand it.

The two functions that follow are the model split along the seam ROS forces: `limit_twist` is the **contract enforcer** (what a real chassis will accept), `step_unicycle` is the **integrator** (what happens next). Phase B's node will call both — and you can test both here without a node.

## 5. `limit_twist`: the turning-radius clamp

**Why it exists.** The spec requires turning-radius limits (M1), and every upstream source of `(v, ω)` — teleop, a planner, a bug — can hand the mower a pair no chassis can execute. A robot that turns tighter than its wheelbase allows does not accelerate through the turn; it just does not do what you asked, and in the sim the honest thing is to *report what was actually applied*. Decision 05's sim node will clamp every incoming command and publish the clamped result; M3's path tracker must respect the same limits. This function is where the rule lives, once, testable, with no node attached.

**The math.** Curvature is "how much heading changes per metre travelled":

```
κ = dψ/ds = ω/v          →          R = |v| / |ω|
```

so a minimum radius `R_min` is a constraint on the ratio: for a given speed, `|ω| ≤ |v| / R_min`. Rearranged, that is one line of arithmetic — the rest of the function is deciding *when* the rule applies.

**Why clamp `ω`, and not `v`.** The constraint is symmetric in principle: you could satisfy `R ≥ R_min` by limiting speed instead (`|v| ≥ |ω| · R_min`). But look at what that does to a mower told to turn in place: `ω = 1.0`, `R_min = 0.5` → `|v| ≥ 0.5`, so the machine would **accelerate forward** because it was turning too tightly. Clamping `ω` instead keeps the operator's speed (within `max_linear`) and bends the turn to fit the chassis — the failure is a wider arc, never a surprise lurch. The measured table below shows exactly that: `v` survives, `ω` gets reduced.

**Why `v = 0` gets an escape hatch.** At zero speed the ratio `|v|/|ω|` is zero, not a radius: an in-place spin has no turn radius at all (its centre of rotation is its own axle). The chassis can do it — and teleop really commands it (§4's measured `j`/`l` bindings). So the radius rule applies only when `v ≠ 0`; at `v = 0` the only limit is `max_angular`. The same guard handles `min_radius ≤ 0` (a "disabled" parameter, also decision 05's rule for invalid parameter values): no division by zero, no radius rule.

**The code.** This is the real thing, built up in the copy you will make:

```python
def limit_twist(v: float, w: float, max_linear: float,
                max_angular: float, min_radius: float) -> tuple[float, float]:
    """Clamp a commanded twist to the mower's kinematic limits."""
    v_clamped = clamp(v, -max_linear, max_linear)
    limit_w = max_angular
    if v_clamped != 0.0 and min_radius > 0.0:
        limit_w = min(max_angular, abs(v_clamped) / min_radius)
    return v_clamped, clamp(w, -limit_w, limit_w)
```

Line by line:

- `clamp(...)` is lesson 03's function, reused — speed is bounded symmetrically in both directions, so reversing gets the same treatment as going forward.
- `limit_w` starts at the honest default: if no radius rule applies, the yaw rate is bounded only by `max_angular`.
- The `if` has two conditions doing different jobs. `v_clamped != 0.0` is the in-place-spin exemption above. `min_radius > 0.0` is the "radius limit disabled" exemption — and note it tests the **parameter**, so a bad `0.0` cannot zero-divide.
- `abs(v_clamped) / min_radius` is the derived bound `R_min` allows at this speed; `min(...)` takes whichever is stricter, because **both** limits always apply. Forgetting that `min` is the classic bug: the mower obeys the radius and blows through `max_angular`, or vice versa.
- The returned `w` is clamped symmetrically with the same trick in reverse: bound the yaw rate by `limit_w`, keep its sign.
- `v_clamped != 0.0` uses exact equality deliberately: `0.0` is exact in IEEE 754, and "close to zero" means "creeping", where the radius rule *should* apply.

**Measured** (Phase A copy, `max_linear = 1.0`, `max_angular = 2.0`):

| call `(v, w, max_lin, max_ang, min_r)` | returns | what happened |
|---|---|---|
| `(0.3, 0.4, 1.0, 2.0, 0.5)` | `(0.3, 0.4)` | nothing at the limit |
| `(0.5, 5.0, 1.0, 2.0, 0.5)` | `(0.5, 1.0)` | radius wins: `0.5/0.5 = 1.0 < 2.0` |
| `(1.0, 5.0, 1.0, 2.0, 0.1)` | `(1.0, 2.0)` | angular wins: radius would allow `10.0`, cap is `2.0` |
| `(-0.5, 1.5, 1.0, 2.0, 0.5)` | `(-0.5, 1.0)` | `abs()` on negative `v` — reversing turns equally tight |
| `(0.5, -5.0, 1.0, 2.0, 0.5)` | `(0.5, -1.0)` | sign preserved |
| `(0.0, 5.0, 1.0, 2.0, 0.5)` | `(0.0, 2.0)` | in-place spin: radius rule skipped, `max_angular` only |
| `(2.5, 0.0, 1.0, 2.0, 0.5)` | `(1.0, 0.0)` | speed itself clamped first |

A seventh case worth knowing: `min_radius = 0.0` behaves like "no radius limit" (`(0.5, 5.0, 1.0, 2.0, 0.0)` → `(0.5, 2.0)`).

**Forward references.** Phase B's `sim_node` will call this on every incoming `/cmd_vel` (parameter names from decision 05: `max_linear_speed`, `max_angular_speed`, `min_turn_radius`) and publish what it applied — "clamped sample-and-hold". M3's path tracker must generate commands that already respect these limits, and we will check that against this very function.

## 6. `step_unicycle`: integrating the model

**Why it exists.** A model is only useful if you can step it forward in time: given where I am now and a constant command held for `dt`, where am I next? Phase B's timer tick needs exactly this, at the `update_rate` parameter, and Phase C's scripted radius check will read its outputs. Because it is pure, the arithmetic is testable as five rows of pytest (§10) instead of a launch file.

**The equations.** The command is a *body-frame* velocity (§4: Odometry's twist is in `child_frame_id`), so forward motion points along the mower's current heading, not along world +x:

```
x_next   = x + v · cos(yaw) · dt
y_next   = y + v · sin(yaw) · dt
yaw_next = wrap(yaw + ω · dt)
```

Two things to notice. First, `cos/sin` of the *old* heading — position advances where the robot is pointing, not where it is heading at the end of the step. Second, the heading changes by `ω·dt` exactly, and then **must be wrapped**: without §7, a mower that turns left through 180° for a while ends up at `yaw = 7.9`, and every downstream `cos` still works but every comparison, message, and log lies about which way the machine faces.

**The code:**

```python
def step_unicycle(x: float, y: float, yaw: float, v: float, w: float,
                  dt: float) -> tuple[float, float, float]:
    """Integrate the unicycle model forward by dt seconds."""
    x_new = x + v * math.cos(yaw) * dt
    y_new = y + v * math.sin(yaw) * dt
    yaw_new = wrap_angle_rad(yaw + w * dt)
    return x_new, y_new, yaw_new
```

- `v * math.cos(yaw) * dt` — one multiplication chain per axis; both use the same `yaw`, the pre-step heading.
- `wrap_angle_rad(...)` is the reason §7 exists; the call is unconditional because wrapping is idempotent (`wrap` of an already-wrapped angle is itself) and inputs may arrive unwrapped.
- The function returns a plain `tuple[float, float, float]` — no message objects — so tests compare against tuples, and the Phase B node does the `Odometry` construction where it belongs.

**Measured** (Phase A copy):

| `(x, y, yaw, v, w, dt)` | returns | meaning |
|---|---|---|
| `(0, 0, 0, 1.0, 0.0, 0.5)` | `(0.5, 0.0, 0.0)` | straight ahead, `1.0 × 0.5` |
| `(0, 0, 0, 0.0, 1.0, 0.5)` | `(0.0, 0.0, 0.5)` | pivot in place: heading moves, position does not |
| `(0, 0, 0, 1.0, 0.5, 1.0)` | `(1.0, 0.0, 0.5)` | Euler: x advances along the *old* heading, so y stays 0 for this step |
| `(1, 1, 0, -1.0, 0.0, 1.0)` | `(0.0, 1.0, 0.0)` | reversing |
| `(0, 0, 3.0, 0.0, 1.0, 0.25)` | `(0.0, 0.0, -3.0331853071795867)` | turning left past `+π` lands in the wrapped negative range — this row is the §7 convention made executable |

**How big is the error, honestly?** The update above is *Euler integration*: it assumes heading is constant for the whole step. The exact solution for constant `(v, ω)` follows the arc of radius `R = v/ω`:

```
x_next = x + R · (sin(yaw + ω·dt) − sin(yaw))
y_next = y − R · (cos(yaw + ω·dt) − cos(yaw))
```

Measured side by side at `dt = 0.05 s`, `v = 1 m/s`, `ω = 1 rad/s` (a 1 m radius), wrapping both headings each step:

- **one step**: position error `0.0012499131968556475 m` — about 1.25 mm against 50 mm of travel.
- **31 steps / 1.55 s**: `0.03498701863233074 m` — about 3.5 cm, roughly 2% of the 1.55 m path.
- **heading**: `0.0` difference. Both integrators perform the identical addition `yaw + ω·dt`, so the heading is bit-for-bit the same; only the position drifts.

Three honest consequences:

1. **Determinism survives.** M1's done-when is "bag replay matches the run", and replay uses the *same* integrator in the *same* code — Euler error is identical both times, so equivalence is exact. What we lose is absolute accuracy against a hypothetical real mower, which this milestone does not claim.
2. **The error grows with `dt` and with `ω·dt`.** Halving `update_rate`'s `dt` roughly quarters the per-step error; that is the cheap tuning knob if Phase C's radius check ever needs it.
3. **The upgrade is three lines.** If a later milestone needs better absolute accuracy (M8 swaps this whole 2D layer for Gazebo physics anyway), replace the body with the exact arc above — same signature, same tests, plus rows pinning the difference. That is the trade-off in one sentence: Euler is simpler and deterministic; the exact form is more accurate and has a singularity at `ω = 0` that needs the straight-line branch. We are choosing simplicity *now*, with the numbers on the table.

## 7. Wrapping angles and pinning the half-open convention

**Why angles wrap.** A heading is an *angle*, not a number line: `yaw = 3.2` and `yaw = 3.2 − 2π` describe the same pointing. Unwrapped headings accumulate forever (a mower spinning on the spot for an hour reads `yaw = 113.1`), and every comparison, message field, and log becomes ambiguous. Worse, two of the same physical heading written differently *subtract* to `2π` instead of `0` — which is precisely the bug that hurts in M2, where an EKF innovation is a heading difference. Wrapping to one canonical range is what makes "these two headings are equal" a decidable question.

**How the existing function does it.** `math.atan2(math.sin(a), math.cos(a))` projects any angle onto the unit circle's principal value: `sin`/`cos` are `2π`-periodic, so the ratio recovers the angle in one range, and `atan2` (rather than `atan`) keeps the quadrant information. Measured pieces of that mechanism:

- `math.sin(-math.pi)` → `-1.2246467991473532e-16`. In exact arithmetic `sin(−π) = 0`; in floating point it is a tiny negative number — the seed of the defect below.
- `math.atan2(0.0, -1.0)` → `3.141592653589793` but `math.atan2(-0.0, -1.0)` → `-3.141592653589793`: the sign of *zero* decides which endpoint you get.

**The endpoints, measured on a pristine checkout:** `wrap(π)` returns `3.141592653589793` and `wrap(-π)` returns `-3.141592653589793` — **both** endpoints are reachable. Five neighbouring doubles confirm it is not a coincidence: wrapping `-math.pi + k·ulp(π)` for `k = -2..2`, only `k = 0` (the input `-π` itself) returns exactly `-π`.

**So what is the convention?** Two endpoints, one of them redundant: `+π` and `−π` are the *same physical heading*. Keeping both means the answer to "is my heading exactly 180°?" depends on floating-point luck. The half-open range **`(−π, π]`** gives every physical heading exactly one spelling — it is what lesson 03's tests already assert (`-math_pi < result <= math_pi`), what review 03 demanded be written down ("Wrong math in a comment is how M1 kinematics bugs get born"), and what decision 05 pins:

> **Heading convention pinned:** `(-π, π]`. … The lesson … agrees on `(-π, π]` (input `-π` must wrap to `+π`).

**The defect, measured:** the docstring says `[-π, π]`, the tests never feed `-π`, and `wrap(-π)` returns `-π`. The convention in the code and the convention in the docs are one character apart, and nothing catches it.

**The fix** — one docstring change and a guard on the *result*:

```python
def wrap_angle_rad(angle: float) -> float:
    """Wrap an angle in radians to the range (-π, π]."""
    res = math.atan2(math.sin(angle), math.cos(angle))
    if res == -math.pi:
        return math.pi
    return res
```

Why guard the result and not the input? The input can be *anything* — `3.0 + 0.25` wraps past `π` to something that rounds to exactly `-π` too, and the boundary only exists in the output range. Guarding `res` catches every input that lands on the excluded endpoint, which is the definition of the convention. (Measured: only the input `-π` itself produced `res == -π` among five neighbouring doubles, so the guard fires exactly on the ambiguous case — but it is written against the output, so it stays correct for any future input.)

**The red proof**, run by adding the `-π` row to the pristine parametrized test and executing `python3 -m pytest test/test_math_utils.py -v` from inside `mower_math/`:

```
test/test_math_utils.py::test_wrap_angle_rad_stays_in_range[3.1415926535] PASSED [ 88%]
test/test_math_utils.py::test_wrap_angle_rad_stays_in_range[-3.141592653589793] FAILED [100%]

=================================== FAILURES ===================================
____________ test_wrap_angle_rad_stays_in_range[-3.141592653589793] ____________

angle = -3.141592653589793

    @pytest.mark.parametrize('angle', [3.5, -3.5, 10.0, -10.0, 3.1415926535, -math_pi])
    def test_wrap_angle_rad_stays_in_range(angle: float) -> None:
>       assert -math_pi < wrap_angle_rad(angle) <= math_pi
E       assert -3.141592653589793 < -3.141592653589793
E        +  where -3.141592653589793 = wrap_angle_rad(-3.141592653589793)

test/test_math_utils.py:35: AssertionError
=========================== short test summary info ============================
FAILED test/test_math_utils.py::test_wrap_angle_rad_stays_in_range[-3.141592653589793]
========================= 1 failed, 8 passed in 0.06s ==========================
```

Note what the assertion buys you: `-π < result` fails for the old code *and* would fail for any code returning `-π`, so the row genuinely distinguishes `(−π, π]` from `[−π, π)`. After the guard and docstring, the same file reports:

```
============================== 9 passed in 0.06s ===============================
```

**Forward references.** M2 wraps the EKF's heading innovation before using it (a `−3.13 − 3.13` difference that should be `0.01` is the classic GNSS-heading outage bug); M3 compares a cross-track *angle* the same way; Phases C/D compare recorded yaws against live ones. All three assume `(-π, π]` with no exceptions — which is why it gets pinned now, with a failing test first.

## 8. `yaw_to_quaternion`: why orientation is a quaternion

**Why this function exists at all.** You might expect ROS to carry heading as one number. It does not: orientations are quaternions. Measured from the installed message definitions:

- `sensor_msgs/msg/Imu.msg`: `geometry_msgs/Quaternion orientation`
- `geometry_msgs/msg/Pose.msg` → `geometry_msgs/Point position` + `geometry_msgs/Quaternion orientation` (so `/odom`'s pose too)
- `geometry_msgs/msg/Quaternion.msg`: `float64 x 0` / `y 0` / `z 0` / `w 1` — the identity is `(0, 0, 0, 1)`, and **the field order is x, y, z, w**, not the `(w, x, y, z)` many maths libraries use. Getting that backwards yields a plausible-looking but wrong rotation.

**Why quaternions instead of roll/pitch/yaw?** REP-103's own ranking (read from the official repo):

> 1. quaternion — Compact representation, No singularities
> …
> 3. fixed axis roll, pitch, yaw about X, Y, Z axes respectively
> 4. euler angles yaw, pitch, and roll about Z, Y, X axes respectively — Euler angles are generally discouraged due to having 24 'valid' conventions…

"No singularities" is not academic. Measured on this machine: convert three *different* roll/pitch/yaw triples — `(0.7, π/2, 0)`, `(0, π/2, −0.7)`, `(0.3, π/2, −0.4)` — into rotation matrices and compare: **all three are equal** (`True`). At pitch exactly `π/2` (nose straight up), roll and yaw become indistinguishable: two degrees of freedom describe three, and information is destroyed. The same check at pitch `0.1` returns `False`. That is gimbal lock, it is why aircraft instruments use "heading/attitude" workarounds, and it is why a simulated mower that tilts on a bump (M4) would corrupt its own orientation if we stored Euler angles.

**The math, for the one case we need.** Our world is planar: the mower only ever rotates about the world's z axis (REP-103: z up). A rotation of angle `θ` about a unit axis `n` is the quaternion

```
q = (n · sin(θ/2),  cos(θ/2))
```

For `n = ẑ = (0, 0, 1)` and `θ = yaw`, the vector part has only a z component, and the identity `sin² + cos² = 1` gives `|q| = 1` for free — no normalisation step needed. So:

```python
def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    """Return the (x, y, z, w) quaternion for a planar yaw about z."""
    half = yaw / 2.0
    return (0.0, 0.0, math.sin(half), math.cos(half))
```

- `half = yaw / 2.0` — the half-angle is the whole trick; forgetting it is the most common bug (it silently halves every rotation).
- `0.0, 0.0` for x and y: a pure z rotation has no x/y component.
- Returning a plain 4-tuple keeps it pure; the Phase B node assigns it field-by-field into `Quaternion(x=..., y=..., z=..., w=...)` — remember the order.

**Measured against the real rotation**, for `yaw` in `0, 1.0, -1.0, 12.3`: applying the quaternion to `(1, 0, 0)` lands on `(cos yaw, sin yaw)` to 15 decimal places — i.e. it really does rotate the mower's forward axis to its heading — and `|q| = 1.0000000000000002` for the `π/2` case (one rounding step away from exactly 1, which is fine: normalisation drift at that scale is lost in every downstream tolerance).

**One gotcha you will hit the moment you write the test.** `yaw_to_quaternion(π/2)` returns `(0.0, 0.0, 0.7071067811865475, 0.7071067811865476)` — `z` and `w` are one ulp apart, because `sin(π/4)` and `sqrt(2)/2` are computed by different paths. An expectation of `(0, 0, √2/2, √2/2)` written as `==` fails with `assert 0.7071067811865475 == 0.7071067811865476`. This is what `pytest.approx` exists for (§10), and the same trap is why `step_unicycle`'s wrap row is compared with `approx` too.

**Forward references.** Phase B fills `/odom`'s `pose.orientation` and `/imu`'s `orientation` with this function's output every tick; M2's EKF consumes those quaternions (and converts them to innovations — where the wrap of §7 comes back). Decision 05's interface table is the contract these fields answer to.

## 9. `expand_covariance_diagonal`: covariance as 36 floats

**Why this function exists.** Every pose and twist in ROS ships with a covariance — "how sure am I?" — and the sim has to fill it or downstream consumers (M2's EKF, M3's checks) will read zeros, which mean "perfectly known". The messages will not take the six numbers you actually know; they want a flat array of 36.

**What the messages say**, quoted from the install:

- `geometry_msgs/msg/PoseWithCovariance.msg`:

  ```
  # Row-major representation of the 6x6 covariance matrix
  # The orientation parameters use a fixed-axis representation.
  # In order, the parameters are:
  # (x, y, z, rotation about X axis, rotation about Y axis, rotation about Z axis)
  float64[36] covariance
  ```

  (REP-103 says the same thing in its "Covariance Representation / Six Dimensional" section — the message comment and the REP agree, which is why both are quoted above.)

- `sensor_msgs/msg/Imu.msg` carries **three** smaller matrices: `float64[9] orientation_covariance # Row major about x, y, z axes`, and likewise for angular velocity and linear acceleration — 3×3, not 6×6.

**Why 36.** A 6×6 matrix has 36 entries; the IDL arrays are one-dimensional, so ROS flattens it **row-major**: element `(row, col)` lands at `row * 6 + col`. The diagonal is where `row == col`, so it lands at `i * 6 + i` → indices **0, 7, 14, 21, 28, 35** — measured by listing every non-zero index of a real call. Row-major also means the *order of your six numbers* is `x, y, z, rx, ry, rz` — matching the message comment above — so the function's contract is not just "length 6" but "length 6 **in that order**".

**Why diagonal-only.** A full symmetric matrix has 21 independent numbers; we know one variance per axis and nothing about the correlations between axes. Filling only the diagonal with `[var_x, var_y, ...]` and leaving the cross terms at `0.0` states precisely that: "these axes are uncertain, and I claim no correlation." That is honest, it is what most simulators publish, and decision 05 fixes it as the project convention. (A real mower's wheel-slip does correlate `x` with `yaw` — a Gazebo-based M8 could revisit this; see decision 05's "what would change this".)

**The code:**

```python
def expand_covariance_diagonal(diagonal: list[float]) -> list[float]:
    """Expand a 6-element diagonal to a 36-element row-major covariance."""
    if len(diagonal) != 6:
        raise ValueError('diagonal must have length 6')
    cov = [0.0] * 36
    for i, value in enumerate(diagonal):
        cov[i * 6 + i] = float(value)
    return cov
```

- The `ValueError` is the function's contract in executable form: a 5- or 7-element parameter would otherwise expand into a *silently wrong* covariance (or a crash two frames later in message construction). Fail now, with a message naming the problem. `pytest.raises` pins it (§10).
- `[0.0] * 36` allocates the off-diagonal zeros in one go — the "no correlation claimed" values from the paragraph above.
- `i * 6 + i` is the diagonal of a row-major 6×6 — the same `row * 6 + col` formula with `col = row`. It is worth writing `i * 6 + i` rather than the cleverer `i * 7`: one is the formula you can check against the message comment, the other is a trick you have to remember.
- `float(value)` normalises, because a parameter could arrive as an `int` (`0` meaning "perfect certainty" would be a nasty surprise to discover as an int in a float array).

**Measured:**

```python
>>> cov = expand_covariance_diagonal([0.05, 0.05, 0.1, 0.2, 0.2, 0.4])
>>> len(cov)
36
>>> [i for i, v in enumerate(cov) if v]
[0, 7, 14, 21, 28, 35]
>>> expand_covariance_diagonal([1.0] * 5)
Traceback (most recent call last):
    ...
ValueError: diagonal must have length 6
```

**The `-1` convention**, quoted from `Imu.msg`, because Phase B needs it and the spec should not be paraphrased:

> If you have no estimate for one of the data elements (e.g. your IMU doesn't produce an orientation estimate), please set element 0 of the associated covariance matrix to -1 … and disregard the associated estimate.

Decision 05 does not simulate the accelerometer, so Phase B will publish `-1` in `linear_acceleration_covariance[0]` — the field the message explicitly supports — rather than inventing noise numbers.

**Forward references.** Phase B exposes `pose_covariance_diagonal` and `twist_covariance_diagonal` parameters (decision 05) and expands them with this function into `/odom`'s two 6×6 matrices; M2's EKF reads those covariances as measurement uncertainty. The IMU's three 9-element arrays are a separate question — §14.

## 10. Testing the functions: 30 cases, `approx`, and `raises`

Lesson 03 taught pytest in this repo (parametrize, running from inside the package, `colcon test` as the arbiter). This assignment adds four things, each earned by a failure mode you have now seen.

**1. The 16 cases, as a table.** This table *is* the interface: rows and expected values are specified here so your run, the reviewer's run, and the future refactor all agree. You write the `test_add_kinematics.py` file; five test functions cover 16 cases (three `parametrize` blocks — 7 + 5 + 2 rows — plus two single-case functions for the covariance contract):

| # | function | rows (inputs → expected) |
|---|---|---|
| 7 | `limit_twist` | `(0.3, 0.4, 1.0, 2.0, 0.5) → (0.3, 0.4)` · `(0.5, 5.0, 1.0, 2.0, 0.5) → (0.5, 1.0)` · `(1.0, 5.0, 1.0, 2.0, 0.1) → (1.0, 2.0)` · `(-0.5, 1.5, 1.0, 2.0, 0.5) → (-0.5, 1.0)` · `(0.5, -5.0, 1.0, 2.0, 0.5) → (0.5, -1.0)` · `(0.0, 5.0, 1.0, 2.0, 0.5) → (0.0, 2.0)` · `(2.5, 0.0, 1.0, 2.0, 0.5) → (1.0, 0.0)` |
| 5 | `step_unicycle` | `(0,0,0, 1.0,0.0,0.5) → (0.5, 0.0, 0.0)` · `(0,0,0, 0.0,1.0,0.5) → (0.0, 0.0, 0.5)` · `(0,0,0, 1.0,0.5,1.0) → (1.0, 0.0, 0.5)` · `(1,1,0, -1.0,0.0,1.0) → (0.0, 1.0, 0.0)` · `(0,0,3.0, 0.0,1.0,0.25) → (0.0, 0.0, -3.0331853071795867)` |
| 2 | `yaw_to_quaternion` | `0.0 → (0.0, 0.0, 0.0, 1.0)` · `π/2 → (0.0, 0.0, 0.7071067811865475, 0.7071067811865476)` |
| 2 | `expand_covariance_diagonal` | `[1,2,3,4,5,6]` → length 36, values at `0,7,14,21,28,35`, everything else `0.0` · a 5-element list → `ValueError` |

The two quaternion rows and the arc row **must** be compared with `pytest.approx` (§8's one-ulp fact; §6's `-3.0331853071795867` is a trig result too). Exact `==` is right for `limit_twist` (its arithmetic is `min`/`abs`/division of exact values) — and being deliberate about which rows need which comparison is the skill here.

**2. `pytest.approx`, because you have now seen `==` fail on equal-in-intent floats.** The toy in §12 fails with `assert 12.540000000000001 == 12.54`, and §8's quaternion fails with `assert 0.7071067811865475 == 0.7071067811865476`. `approx` compares with a *relative* tolerance (measured: the default `1e-6` — `0.7071067811865475 == approx(0.7071067811865476)` passes, while `0.71 == approx(0.71 + 7.1e-07)` also passes, i.e. about 1e-6 relative). It also gives readable failures (measured): a wrong expectation reports `Expected: 0.70710778 ± 7.1e-07` next to `Obtained: 0.7071067811865476` instead of a bare `False`, so you can see *how* wrong you are.

**3. `pytest.raises`, because a `ValueError` is part of the contract.** §9's wrong-length case is not a "should not crash" hope — it is specified behaviour. The form:

```python
def test_expand_covariance_diagonal_rejects_wrong_length():
    with pytest.raises(ValueError):
        expand_covariance_diagonal([1.0, 2.0, 3.0, 4.0, 5.0])
```

(`match='diagonal must have length 6'` tightens it further — §12 uses `match` so you can see it.) Without this test, "validation" is a comment.

**4. The arithmetic to 30.** Your target is not a magic number; it is a sum:

```
13 (baseline: 5 linters + 3 clamp rows + 5 wrap rows)
+ 1 (the new -π wrap row)
+ 16 (the five kinematics test functions)
= 30 tests, 0 errors, 0 failures, 0 skipped
```

If you see 29, you dropped a table row; if 31, you added one (fine for the stretch goal in §13 — the baseline 30 must still be there). **Zero skipped** is not decoration: it means `test_copyright` is still enabled (§11), which lesson 03 established and review 03 verified. A skip is a test that silently stops protecting you.

**The loops you will actually use while writing this.** Both measured, both from inside `ros2_ws/src/mower_math/`:

```bash
python3 -m pytest test/test_add_kinematics.py -v          # 16 passed in 0.07s
python3 -m pytest test/test_add_kinematics.py -k limit_twist -v   # 7 passed, 9 deselected in 0.04s
```

(`python3 -m pytest` puts the current directory on `sys.path`, which is how `import mower_math` resolves without any sourcing — lesson 03's trick, unchanged.)

**Test IDs carry the inputs**, which makes failures self-describing: `test_limit_twist[0.5-5.0-1.0-2.0-0.5-expected1]` tells you which row broke without opening the file. When a row fails, the ID *is* the bug report.

Finally: **write red first where you can.** That is not ceremony — §12 shows it changing what you believe about your own code, and §7's guard was only trustworthy because a test failed before it existed. Write a row from the table, watch it fail, implement, watch it pass.

## 11. The scaffold's five linters on brand-new files

Your new module and test file enter a package that already runs five lint tests, measured from `build/mower_math/pytest.xml`: `test_copyright`, `test_flake8`, `test_mypy`, `test_pep257`, `test_xmllint`. None of them is optional, and each has an opinion about the file you are about to write — plus two surprises.

**flake8: 99 characters, Google import order, single quotes.** The real config, from the installed `ament_flake8/configuration/ament_flake8.ini`:

```ini
[flake8]
extend-ignore = B902,C816,D100,D101,D102,D103,D104,D105,D106,D107,D203,D212,D404,I202
import-order-style = google
max-line-length = 99
show-source = true
statistics = true
```

Measured behaviours, each from a deliberate experiment:

- **A 104-char code line fails**: `E501 line too long (104 > 99 characters)`. But a 100-char *comment* line passed — pycodestyle exempts long comment/URL lines whose prefix is short (source: `maximum_line_length` in the installed `pycodestyle.py`, "Special case for long URLs in multi-line docstrings or comments"). So the linter's 99 is a backstop, not your style guide.
- **Import order is enforced**: swapping the toy's two imports produced `I100 Import statements are in the wrong order. 'import pytest' should be before 'from xp_pricing.pricing import ...'`. Standard-library imports and third-party imports are separate groups (a blank line between them) — your working tree's leftover file fails exactly this way: `I201 Missing newline between import groups. 'from mower_math...' is identified as Third Party and 'import math' is identified as Stdlib.`
- **`flake8-quotes` is installed** (it is in `flake8 --version`'s plugin list): `Q000 Double quotes found but single quotes preferred`. This repo is single-quote; the linter enforces it.

**Surprise 1: docstrings are *not* linted.** Measured: deleting a function's docstring from the toy leaves `test_pep257 PASSED`. The installed `ament_pep257/main.py` defines `_ament_ignore = ['D100', 'D101', 'D102', 'D103', 'D104', 'D105', 'D106', 'D107', 'D203', 'D212', 'D404']` — every "missing docstring" code is ignored by the `ament` convention, and flake8's own `extend-ignore` drops the D codes too. **Type hints on public functions and docstrings are requirements of this project, not of the linters** — they will pass review without either. The lesson's rule stands on its own: every public function here gets a type hint and a docstring, because M2/M3 readers are you in six months.

**Surprise 2: mypy is not strict.** Measured: the toy's test file has no annotations at all and `test_mypy` passes. Same conclusion as pep257 — the bar is set by the lesson and the review, not by the tool.

**Copyright: the scaffold ships it disabled.** A fresh `ros2 pkg create` package's `test_copyright.py` contains, per the installed template `ros2pkg/resource/ament_python/test_copyright.py.em`:

```python
# Remove the `skip` decorator once the source file(s) have a copyright header
@pytest.mark.skip(reason='No copyright header has been placed in the generated source file.')
```

That is why §12's toy package reports `1 skipped` — and why your `mower_math`, whose copy had that decorator removed back in lesson 03, reports `0 skipped` and must keep doing so. Adding files with the standard Apache header (copy the one at the top of `math_utils.py`) keeps it there.

**Your line-length target is 79, not 99.** PEP 8's limit is 79; lesson 03's files are written to it; the linter simply will not stop you at 80. The comment exception above means you can pass CI with a 100-character line and still be out of style — so the enforcement is you and the review, which is how it works in every real repo. (If you ever want the linter to enforce 79 instead, that is a one-line config decision for a decision record — not a Phase A task.)

## 12. Worked example: a toy pricing package, red to green

Phase A's job is 16 test rows and a guard. Before you touch `mower_math`, this toy does the *workflow* on a problem with no geometry in it: write a test from a spec, watch it fail for a real reason, decide whether the code or the expectation is wrong, fix it, watch it pass, then let the five linters in. It is deliberately not kinematics — you cannot pattern-match the assignment onto it.

**Step 1 — scaffold, measured:**

```bash
mkdir -p /tmp/opencode/l05toy/src
cd /tmp/opencode/l05toy/src
ros2 pkg create --build-type ament_python --license Apache-2.0 xp_pricing
```

```
going to create a new package
package name: xp_pricing
destination directory: /tmp/opencode/l05toy/src
package format: 3
version: 0.0.0
description: TODO: Package description
maintainer: ['Jamie <jamie-gastrich@users.noreply.github.com>']
licenses: ['Apache-2.0']
build type: ament_python
dependencies: []
creating folder ./xp_pricing
creating ./xp_pricing/package.xml
creating source folder
creating folder ./xp_pricing/xp_pricing
creating ./xp_pricing/setup.py
creating ./xp_pricing/setup.cfg
creating folder ./xp_pricing/resource
creating ./xp_pricing/resource/xp_pricing
creating ./xp_pricing/xp_pricing/__init__.py
creating ./xp_pricing/xp_pricing/py.typed
creating folder ./xp_pricing/test
creating ./xp_pricing/test/test_copyright.py
creating ./xp_pricing/test/test_flake8.py
creating ./xp_pricing/test/test_mypy.py
creating ./xp_pricing/test/test_pep257.py
creating ./xp_pricing/test/test_xmllint.py
```

**Step 2 — the module, written from a spec.** The spec, in one comment: *tiers are half-open — quantities `0 ≤ qty < 10` get 0%, `10 ≤ qty < 50` get 5%, `qty ≥ 50` get 10%.* The comment below states that; check whether the code agrees:

`xp_pricing/xp_pricing/pricing.py`:

```python
"""Pure pricing helpers for the lesson 05 worked example."""

# Half-open tiers: [0, 10) at 0%, [10, 50) at 5%, [50, ...) at 10%.
TIER_BREAKS: tuple[int, ...] = (10, 50)
TIER_RATES: tuple[float, ...] = (0.05, 0.10)


def discount_rate(qty: int) -> float:
    """Return the fractional discount for an order quantity."""
    if qty < 0:
        raise ValueError(f'qty must be non-negative, got {qty}')
    if qty <= TIER_BREAKS[0]:
        return 0.0
    if qty <= TIER_BREAKS[1]:
        return TIER_RATES[0]
    return TIER_RATES[1]


def line_total(qty: int, unit_price: float) -> float:
    """Return the total price for qty units after the discount."""
    return qty * unit_price * (1.0 - discount_rate(qty))
```

**Step 3 — the tests, straight from the spec** (five boundary-ish quantities, two totals including one that will expose float equality, one `raises` row):

`xp_pricing/test/test_pricing.py`:

```python
import pytest

from xp_pricing.pricing import discount_rate, line_total


@pytest.mark.parametrize(
    'qty, expected',
    [
        (1, 0.0),
        (10, 0.05),
        (49, 0.05),
        (50, 0.10),
        (999, 0.10),
    ],
)
def test_discount_rate(qty, expected):
    assert discount_rate(qty) == expected


@pytest.mark.parametrize(
    'qty, unit_price, expected',
    [
        (3, 10.0, 30.0),
        (12, 1.1, 12.54),
    ],
)
def test_line_total(qty, unit_price, expected):
    assert line_total(qty, unit_price) == expected


def test_negative_qty_rejected():
    with pytest.raises(ValueError, match='qty must be'):
        discount_rate(-1)
```

Note the import order (third-party `pytest` first, blank line, then the project) — that is `I100` avoidance from §11, done by habit.

**Step 4 — red:**

```bash
cd /tmp/opencode/l05toy/src/xp_pricing
python3 -m pytest test/test_pricing.py -v
```

```
test/test_pricing.py::test_discount_rate[1-0.0] PASSED                   [ 12%]
test/test_pricing.py::test_discount_rate[10-0.05] FAILED                 [ 25%]
test/test_pricing.py::test_discount_rate[49-0.05] PASSED                 [ 37%]
test/test_pricing.py::test_discount_rate[50-0.1] FAILED                  [ 50%]
test/test_pricing.py::test_discount_rate[999-0.1] PASSED                 [ 62%]
test/test_pricing.py::test_line_total[3-10.0-30.0] PASSED                [ 75%]
test/test_pricing.py::test_line_total[12-1.1-12.54] FAILED               [ 87%]
test/test_pricing.py::test_negative_qty_rejected PASSED                  [100%]

=================================== FAILURES ===================================
...
E       assert 0.0 == 0.05
E        +  where 0.0 = discount_rate(10)
...
E       assert 0.05 == 0.1
E        +  where 0.05 = discount_rate(50)
...
E       assert 12.540000000000001 == 12.54
E        +  where 12.540000000000001 = line_total(12, 1.1)
...
========================= 3 failed, 5 passed in 0.07s ==========================
```

**Step 5 — decide which side is wrong.** This is the actual lesson:

- Rows `[10-0.05]` and `[50-0.1]`: the *comment* says half-open, the *tests* say half-open, and the code says `<=`. **The code is wrong** — the tier boundary belongs to the next tier. Two one-character fixes: `qty <= TIER_BREAKS[0]` → `qty < TIER_BREAKS[0]`, and the same for the second break.
- Row `[12-1.1-12.54]`: `12 × 1.1 × 0.95` in binary floating point is `12.540000000000001`, and `12.54` cannot be represented exactly either. The *expectation* is right (that is what the price is in decimal); **the comparison is wrong**. Fix the test, not the code: `== pytest.approx(expected)`.

Apply those three edits.

**Step 6 — green:**

```
============================== 8 passed in 0.08s ===============================
```

exit 0. The five tests that passed before still pass — you changed behaviour only where the spec disagreed.

**Step 7 — the linters, via colcon** (from `/tmp/opencode/l05toy`, with ROS sourced, `ROS_DOMAIN_ID=63`):

```bash
colcon build --symlink-install --packages-select xp_pricing
colcon test --packages-select xp_pricing
colcon test-result --verbose --test-result-base build/xp_pricing
```

```
Starting >>> xp_pricing
Finished <<< xp_pricing [1.62s]

Summary: 1 package finished [1.77s]
Starting >>> xp_pricing
Finished <<< xp_pricing [10.4s]

Summary: 1 package finished [10.6s]
Summary: 13 tests, 0 errors, 0 failures, 1 skipped
```

13 = 5 linters + 8 tests. The **1 skipped is `test_copyright`**, because the scaffold template ships it decorated with `@pytest.mark.skip` (§11) — the toy keeps that, `mower_math` must not (it reports 0). flake8 passed on both toy files, meaning they are ≤ 99 chars, import-ordered, and single-quoted; pep257 passed even though the *test* functions have no docstrings (the D-codes are ignored); mypy passed with the test file entirely unannotated. All three surprises of §11, live.

**Clean up:** `rm -rf /tmp/opencode/l05toy`

The assignment's real work now has a shape: table row → red → think → green → linters → 30.

## 13. Assignment: Phase A in `mower_math`

**First, the state of your tree.** `git status` currently shows two untracked files under `ros2_ws/src/mower_math/`: `mower_math/add_kinematics.py` (53 lines) and `test/test_add_kinematics.py` (**0 bytes**). They are incomplete leftovers — measured on a copy of your tree: `13 tests, 0 errors, 1 failure, 0 skipped`, the failure being `test_flake8`'s `I201` in that module. This assignment is *you* writing those two files (plus the `wrap` fix). Overwrite them; do not treat them as a starting draft, and do not leave the `I201` behind.

**Scope:** four files only — `mower_math/mower_math/math_utils.py` (the wrap fix), `mower_math/mower_math/add_kinematics.py` (new), `mower_math/test/test_math_utils.py` (the `-π` row), `mower_math/test/test_add_kinematics.py` (new). Do **not** create `mower_sim` (Phase B), touch `docker/`, edit `README.md`, or add `log/` artifacts.

### Requirements

1. **Pin the heading convention** in `math_utils.py`: docstring states `(-π, π]`; guard maps a `res` of exactly `-π` to `+π` (§7); add `-math_pi` to the parametrized row list in `test_math_utils.py`. Write the row first and watch it fail (§7 shows the exact red output you should reproduce).
2. **Add `add_kinematics.py`** with the four pure functions of §5, §6, §8, §9: `limit_twist`, `step_unicycle`, `yaw_to_quaternion`, `expand_covariance_diagonal`. Reuse `clamp` and `wrap_angle_rad` from `math_utils` — do not reimplement them. No `rclpy`, no `geometry_msgs`, no `os`/`sys`: this module must be importable in a bare Python process.
3. **Add `test_add_kinematics.py`** with the 16 cases from §10's table — inputs and expected values exactly as specified — using `parametrize`, `approx` where the table's rows are trig-derived, and `raises` for the `ValueError` row.
4. **Style:** every public function has a full type hint and a docstring in this project's voice ("…the mower's kinematic limits", not "clamps stuff"); lines ≤ 79; single quotes; import groups blank-line separated (§11).

### Interfaces

| function | signature | returns | raises |
|---|---|---|---|
| `limit_twist` | `(v, w, max_linear, max_angular, min_radius) -> tuple[float, float]` | `(v_clamped, w_clamped)` | — |
| `step_unicycle` | `(x, y, yaw, v, w, dt) -> tuple[float, float, float]` | `(x, y, yaw)` with `yaw` in `(-π, π]` | — |
| `yaw_to_quaternion` | `(yaw) -> tuple[float, float, float, float]` | `(x, y, z, w)` of a z-rotation | — |
| `expand_covariance_diagonal` | `(diagonal: list[float]) -> list[float]` | 36 floats, row-major 6×6 diagonal | `ValueError` if `len != 6` |

Argument names are part of the interface: Phase B's node passes these from parameters (`max_linear_speed`, `max_angular_speed`, `min_turn_radius`, `update_rate` — decision 05), and the reviewer's sanity script calls them by position and by name.

### Acceptance

Run from your repo; each block is one check.

```bash
cd ~/mower-sim/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install --packages-select mower_math
colcon test --packages-select mower_math
colcon test-result --verbose --test-result-base build/mower_math
```

- [ ] `Summary: 30 tests, 0 errors, 0 failures, 0 skipped`
- [ ] `grep -o '<testcase' build/mower_math/pytest.xml | wc -l` prints `30` (proves 30 cases, not one test counting 30)

```bash
cd ~/mower-sim/ros2_ws
source /opt/ros/lyrical/setup.bash
source install/setup.bash
python3 - <<'EOF'
from math import pi
from mower_math.math_utils import clamp, wrap_angle_rad
from mower_math.add_kinematics import (limit_twist, step_unicycle,
                                       yaw_to_quaternion,
                                       expand_covariance_diagonal)

# heading convention (-pi, pi]
assert wrap_angle_rad(-pi) == pi, 'wrap(-pi) must be +pi'
assert wrap_angle_rad(pi) == pi
assert abs(wrap_angle_rad(3.5) - (3.5 - 2 * pi)) < 1e-12

# limit_twist: angular wins, radius wins, in-place spin, linear clamps
assert limit_twist(1.0, 5.0, 1.0, 2.0, 0.1) == (1.0, 2.0)
assert limit_twist(0.5, 5.0, 1.0, 2.0, 0.5) == (0.5, 1.0)
assert limit_twist(0.0, 5.0, 1.0, 2.0, 0.5) == (0.0, 2.0)
assert limit_twist(2.5, 0.0, 1.0, 2.0, 0.5) == (1.0, 0.0)

# step_unicycle: straight line, and a heading that wraps past -pi
assert step_unicycle(0.5, 0.0, 0.0, 0.5, 0.0, 1.0) == (1.0, 0.0, 0.0)
x, y, yaw = step_unicycle(0.0, 0.0, 3.0, 0.0, 1.0, 0.25)
assert abs(yaw - -3.0331853071795867) < 1e-12, repr(yaw)

# quaternion
qx, qy, qz, qw = yaw_to_quaternion(pi / 2)
assert (qx, qy) == (0.0, 0.0)
assert abs(qz - qw) < 1e-12 and abs(qz - 2 ** -0.5) < 1e-12, repr((qz, qw))

# covariance
cov = expand_covariance_diagonal([0.05, 0.05, 0.1, 0.2, 0.2, 0.4])
assert len(cov) == 36
assert [i for i, v in enumerate(cov) if v] == [0, 7, 14, 21, 28, 35]
try:
    expand_covariance_diagonal([1.0] * 5)
except ValueError:
    pass
else:
    raise SystemExit('expected ValueError for a 5-element diagonal')

print('all sanity checks passed')
EOF
```

- [ ] prints `all sanity checks passed` (and exits 0 — a wrong value anywhere aborts with the failing assertion named)

```bash
grep -rn "import rclpy\|import rclcpp" ~/mower-sim/ros2_ws/src/mower_math   # expect no output
grep -n "(-π, π\]" ~/mower-sim/ros2_ws/src/mower_math/mower_math/math_utils.py   # expect line 24-ish
grep -rn "TODO\|FIXME" ~/mower-sim/ros2_ws/src/mower_math   # expect no output
```

- [ ] first and third print nothing; second prints the docstring line containing `(-π, π]`
- [ ] `cd ~/mower-sim/ros2_ws/src/mower_math && python3 -m pytest test/test_add_kinematics.py -q` → `16 passed`
- [ ] `python3 -m pytest test/test_math_utils.py -q` → `9 passed`
- [ ] zero skips anywhere (the copyright test still runs — `grep -L "pytest.mark.skip" test/test_copyright.py` prints the filename, i.e. no skip decorator)

**Stretch goal — pin the convention harder.** Review 03's point was that a range assertion alone (`-π < result <= π`) cannot fully distinguish conventions: an implementation returning, say, `0.0` for input `-π` would pass your row. Add tests *you* design that pin the terminal exactly — at minimum an explicit `wrap(-π) == +π` equality assertion, and optionally rows an epsilon either side of `-π` (with `ulp`-scale care, §7's neighbourhood table is your map). Keep the baseline 30 green; your additions raise the count, which the acceptance wording above allows (`30` must still be there and nothing may fail or skip). Write the new test first, and if you can find an implementation it rejects that the range row accepts, say so in your commit message — that is the real receipt.

## 14. Where this leaves M1

Phase A done means: `mower_math` carries the model — a tested turning-radius clamp, a tested integrator, the quaternion and covariance conversions the messages demand, and one heading convention that is asserted instead of assumed. Review 03's open notation issue is closed by a failing test rather than a comment.

**M1's done-when is still unmet.** Nothing publishes anything yet; no bag exists; teleop has not moved anything. Phases B–D remain:

- **B** — `mower_sim` + `sim_node`: parameters (decision 05's list), clamped sample-and-hold calling `limit_twist`, a timer calling `step_unicycle`, publishers for `/odom` and `/imu` using `yaw_to_quaternion` and `expand_covariance_diagonal`, plus `bag_check.py`, `docker/entrypoint.sh`, and `.gitignore` changes.
- **C** — scripted straight-line and radius verification against the interfaces table in decision 05.
- **D** — teleop drives the mower; a recorded bag replays the same behaviour — the spec's words.

Two open items, deliberately surfaced rather than papered over:

1. **The IMU's three covariance arrays are 9 elements, not 36.** Decision 05 lists `imu_orientation_covariance` (and friends) as parameters but does not say how a 6-element diagonal becomes three `float64[9]` matrices — probably a slice of the first three elements per matrix, but that is a Phase B design decision to record, not to guess. `expand_covariance_diagonal` as assigned covers Odometry's two 6×6 matrices only, which is exactly what §9's measured scope says.
2. **Container runs of Phase A were not exercised** (§2). Lesson 04's image flow exists; whether these tests pass inside it is unverified here and belongs to Phase B's docker work or a reviewer's run.

Forward references worth remembering as you go: M2 wraps heading innovations (§7), M3's tracker must generate commands `limit_twist` would pass unchanged (§5), and M8 replaces this 2D layer wholesale — which is why the functions are small, pure, and independently testable: the smaller the surface, the cheaper the swap.

## 15. Commit

One concept, one commit, as always:

```
M1 (Phase A): add kinematics pure functions to mower_math, pin wrap_angle_rad to (-π, π]
```

Docs are a separate commit if you batch them (`docs: add lesson 05 kinematics pure functions and hints`). Small and frequent — if you committed the wrap fix and the four functions separately while working, that is better than one bundle, and both are fine as long as each message says what changed and that it is M1.
