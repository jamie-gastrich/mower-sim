# Hints for 06 - The sim node and its parameters (Phase B of M1)

Three tiers. Open only when stuck, and stop at the first tier that unblocks you:

1. **Nudge** — you know the area, you lost the thread.
2. **Direction** — the shape of the fix, in prose.
3. **Near-solution** — enough to type your way out; still *you* writing the real files.

Everything here assumes you have read the lesson section named in each
header. The worked example already contains the toy versions of everything —
the hints are for when you are staring at your own `sim_node.py`, not for
when you skipped the lecture.

---

## 1. Scaffold and package.xml (assignment 1, lesson §6.1)

**Nudge.** `ros2 pkg create --node-name sim_node` generates the entry-point
line for you; `setup.py` is where a missing/extra entry point shows up.

**Direction.** Scaffold with the exact flags from §6.1 (destination
`ros2_ws/src`). The scaffold writes `mower_sim/mower_sim/sim_node.py` with a
print-only `main()` — replace its contents. Add the five `<depend>` lines to
`package.xml` *after* the `<license>` line, before the `<test_depend>`s.
Build with `colcon build --symlink-install` and run
`ros2 run mower_sim sim_node`; if "Package 'mower_sim' not found", you
forgot to `source install/setup.bash` in the shell (lesson 01's standing
rule).

**Near-solution.** `package.xml` deps block, alphabetical:

```xml
<depend>geometry_msgs</depend>
<depend>mower_math</depend>
<depend>nav_msgs</depend>
<depend>rclpy</depend>
<depend>sensor_msgs</depend>
```

`test_copyright.py`: delete the `@pytest.mark.skip(...)` line only (keep
`@pytest.mark.copyright` and the function).

## 2. `sim_config.py` (assignment 2, lesson §5.2–5.4)

**Nudge.** Fifteen defaults, one per §5.2 table row; two functions. The
node's other file already imports constants from here in the worked
example.

**Direction.** Copy the toy's `xp_config.py` shape exactly, then extend the
constant block with the seven parameters the toy omits: `initial_x/y/yaw`
(floats, `0.0`), `twist_covariance_diagonal` (`[0.001]×6`),
`imu_angular_velocity_covariance` (`[0.001]×3`),
`imu_linear_acceleration_covariance` (`[-1.0, 0.0, 0.0]`). The two helpers
are identical to the toy's — no `rclpy` import anywhere in the file.

**Near-solution.** If flake8 complains "imported but unused" for
`expand_covariance_diagonal` when you first build, it is telling the truth:
you haven't wired `twist_covariance_diagonal` into `/odom.twist.covariance`
yet. The pure file is done when the node and the tests both import from it
and nothing else does.

## 3. `sim_node.py` — parameters and state (assignment 3a, lesson §5.2)

**Nudge.** Declare-all-then-read-all; `float(...)` casts; `positive_or`;
warnings naming the parameter.

**Direction.** Declare the 15 parameters in `__init__` with the module
constants as defaults. Read the four numeric ones through `positive_or`,
warn when the fallback fired (mirror the toy's `update_rate` lines), and
compute `dt` from the *fallback* value, not the raw one. Read the three
frame strings with `str(...)`. Expand the five covariance lists with the two
expanders (`expand_covariance_diagonal` for the 6-vectors, ours for the
3-vectors) and store the expanded 36- and 9-element lists on `self`.

**Near-solution.** The four numeric reads are the toy's lines with broader
names; the hardest one to get right is `min_turn_radius` → `self.min_radius`
because its friend `limit_twist` short-circuits on `<= 0` anyway — but the
warn-before-fallback habit stays the same.

## 4. `sim_node.py` — the initial pose (assignment 3b, lesson §5.1, §5.5)

**Nudge.** `initial_x/y/yaw` are read like every other parameter; nothing in
the model changes.

**Direction.** Replace the toy's hard-coded `self.x = 0.0` block with reads
of the three `initial_*` parameters (float casts). Everything else — the
`v`/`w` zero start, the timer, the callbacks — is untouched. Phase D's replay
correctness depends on this: a fresh node started with the defaults is at
the origin, exactly where the live session started.

**Near-solution.**

```python
self.x = float(self.get_parameter('initial_x').value)
self.y = float(self.get_parameter('initial_y').value)
self.yaw = float(self.get_parameter('initial_yaw').value)
```

## 5. `sim_node.py` — message filling (assignment 3c, lesson §5.3–5.4)

**Nudge.** Odometry: pose frame vs body frame, two covariance fields. Imu:
three covariances, one of them `-1` at element 0.

**Direction.** `/odom` fills 36 + 36 covariance elements from the two 6-vector
parameters (indices 0/7/14/21/28/35). `/imu` fills three 9-element matrices
from the three 3-vector parameters; the accel one must land `-1` at element
0 *because the default is `[-1.0, 0.0, 0.0]`* — if you are tempted to
special-case it in the node, stop: decision 06 chose the parameter default
as the carrier. The quaternion tuple produced once per tick goes into both
messages.

**Near-solution.** If your first `colcon test` passes but `ros2 topic echo
/imu` shows a *zero* accel covariance instead of `-1`, you declared
`imu_linear_acceleration_covariance` with `[0.0, 0.0, 0.0]` instead of the
§5.2 table's `[-1.0, 0.0, 0.0]` — grep your own `sim_config.py` for the
`-1`.

## 6. Testing and linting (assignment 4, lesson §5.6)

**Nudge.** Five unit cases, five linters, zero skips. `colcon test` is the
arbiter.

**Direction.** `test_sim_config.py` = the toy's `test_xp_config.py` re-imported.
Run `python3 -m pytest test/test_sim_config.py -v` from inside
`ros2_ws/src/mower_sim` for the fast loop (expect `5 passed in about 0.06s`),
then `colcon test --packages-select mower_sim` for the full count. If it
reports a failure in `test_pep257`: your new module's docstrings are missing
or malformed — every public function and the module itself need one (D213:
summary on the line after `"""`). If `test_flake8`: import order or line
length. If `test_xmllint`: `package.xml` is malformed.

**Near-solution.** The three fix-ups that trip everyone:

- pep257: `"""..."""` on its own line, summary on the line after the
  opening quotes.
- flake8: stdlib group first, then third-party alphabetical
  (`geometry_msgs` … `sensor_msgs`), then your own package last; ≤ 99 chars.
- copyright: your header on **every** `.py` file you wrote (copy the toy's
  header block; the scaffold's own `test/` files keep their OSRF header).

## 7. Runtime acceptance (criteria B–F, lesson §6.6–6.7)

**Nudge.** Dedicated `ROS_DOMAIN_ID` per shell trio; one node at a time on
a topic; `kill` everything afterwards.

**Direction.** Use domain 41 for everything in this session. Start the node
in one shell, run the echo/`topic info`/`hz` checks in another, publish
bursts in a third. When a check echoes the *wrong* node's message
(initial pose when you expected a moved pose, or vice versa), you have two
`sim_node`s on the same domain — that is the same collision the toy showed
in §6.7. For the silence check, publish the stop burst *before* the first
echo, then wait three seconds, then echo again.

**Near-solution.** Criterion C's expected `0.8` restates the Phase A table:
`min(2.0, 0.4/0.5)`. If you see `2.0` instead, the clamp is not running —
your callback stores `msg.angular.z` directly instead of the `limit_twist`
result, and `/odom.twist` is reporting raw commands (the exact failure mode
§5.1 calls out). If you see `5.0`, same bug, worse.

## 8. Container acceptance (criterion G, lesson §5.7)

**Nudge.** The image bakes nothing; `entrypoint.sh` builds and tests at
`docker run` time.

**Direction.** `docker build` from the repo root (the Dockerfile expects
`ros2_ws/src` and `docker/` in the context — building from inside
`ros2_ws` will fail with "COPY failed"). The first `docker run` recompiles
all three packages inside the container; expect the colcon progress noise,
then three `Summary:` lines. If `mower_sim`'s line is missing, `entrypoint.sh`
still names two packages (check your edit). If the whole run fails at
`colcon build`, the container's build of your package failed — the log
names the file; fix it on the host, rebuild the image, rerun.

**Near-solution.** `docker run --rm -t mower-sim:m1-phase-b` is the exact
acceptance command; `--rm` removes the container so repeated runs start
fresh (but *not* the image — rebuild with `docker build` whenever you change
source, since the Dockerfile COPYs `ros2_ws/src` into the image).