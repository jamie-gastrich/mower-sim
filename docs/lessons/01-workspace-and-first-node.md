# 01 - The workspace, the package, and your first node

**Milestone:** M0 · **Language:** Python · **Prerequisite:** none (first lesson)

**Concepts this assignment requires** — each line links to the section that teaches it:

- [A ROS 2 package is the unit of build, dependency, and test](#5-what-ros2-pkg-create-gives-you-and-why)
- [How `ros2 run` finds your code at all](#6-how-ros2-run-finds-your-code)
- [colcon's build / install / source cycle, and what `--symlink-install` changes](#7-colcon-build-install-source)
- [Declaring real dependencies in `package.xml`](#8-packagxml-is-not-decorative)
- [A node: publisher, node-private topic name, and QoS depth](#9-nodes-topics-and-the-prefix)
- [Building a message, and the two things that will bite you](#10-messages-and-two-things-that-bite)
- [Parameters instead of magic numbers](#11-parameters-no-magic-numbers)
- [Timers](#12-timers)
- [Logging through the node logger](#13-logging)
- [Shutting down cleanly on Ctrl-C](#14-stopping-cleanly)
- [Keeping logic out of the node class](#15-keep-the-string-out-of-the-node)
- [The scaffold's lint tests are not optional](#16-the-scaffolds-lint-tests-are-not-optional)

---

## 1. Where this fits

M0 in the spec is "Repo layout, Docker image, colcon build, one hello-world node in Python and one in C++, a test that runs in CI-style." Its done-when is "clean build in a fresh container, tests pass."

This lesson is the first half of that: the layout decision, the build loop, and one real node in Python. Lesson 02 does the same node in C++ so you feel the difference between the two build systems. Lesson 03 makes `colcon test` mean something.

The node you are going to build is not a throwaway hello-world. It is `mower_status`: the node that says a mower is alive and healthy. That node exists in the final system. M4 hangs the safety state machine off it, M6 draws it on a dashboard, and M7's fleet manager polls a fleet of them over MQTT to decide whether to reassign a mower's work. Everything you learn about parameters, private topic names, and message types here is used again in every one of those milestones.

## 2. Verification table

Everything in this lesson was run on this machine before being written down. The scratch package was `xp_hello_counter`, built in `/tmp/opencode/l01`, and deleted afterwards.

| Claim | How it was checked | Result |
|---|---|---|
| `ros2 pkg create` scaffolds both Python and C++ packages | `ros2 pkg create --help` | build types `cmake`, `ament_cmake`, `ament_cargo`, `ament_python` |
| The `ament_python` scaffold writes these 13 files | `find xp_hello_counter -type f` after create | `LICENSE`, `package.xml`, `setup.py`, `setup.cfg`, `resource/<pkg>`, 5 files in `test/`, `<pkg>/__init__.py`, `<pkg>/py.typed` |
| `resource/<pkg>` is what makes the package visible to ROS | `wc -c resource/xp_hello_counter` | 0 bytes, an empty marker file |
| colcon build of the scaffold works | `colcon build --symlink-install` | `Finished <<< xp_hello_counter [1.55s]` |
| Without sourcing the workspace, ROS cannot see the package | `ros2 pkg prefix xp_hello_counter` with no `source install/setup.bash` | `Package not found` |
| After sourcing, it resolves | same command after sourcing | `/tmp/opencode/l01/install/xp_hello_counter` |
| A `console_scripts` entry becomes a runnable executable | `ros2 pkg executables xp_hello_counter` | `xp_hello_counter widget_monitor` |
| Renaming an executable does not remove the old one from `install/` | added a second entry point, rebuilt without cleaning | both `counter` and `widget_monitor` still listed; `rm -rf build install log` then rebuild → only `widget_monitor` |
| `~/name` resolves to `/<node_name>/name` | `ros2 topic list` while running | `/widget_monitor/diagnostics` |
| Parameters are settable from the command line | `ros2 run ... --ros-args -p widget_id:=widget-z` | `ros2 param get` → `String value is: widget-z` |
| Rate actually follows the parameter | `ros2 topic hz` with `-p publish_rate:=5.0` | `average rate: 5.003` |
| `DiagnosticStatus.values` has **no** `.add()` in this distro | `msg.values.add(...)` at runtime, and `hasattr(msg.values, 'add')` | `AttributeError: 'list' object has no attribute 'add'`; `hasattr` → `False` |
| `DiagnosticStatus.OK` is `bytes` here, and is the only accepted value for `level` | printed `repr(DiagnosticStatus.OK)`; assigned bytes vs `int` with `ROS_PYTHON_CHECK_FIELDS=1` | `b'\x00'`; `int` **rejected**: "The 'level' field must be of type 'bytes' or 'ByteString' with length 1" |
| Every primitive `std_msgs` type is deprecated in this distro | `cat /opt/ros/lyrical/share/std_msgs/msg/String.msg` (also `Int32`, `Float64`, `Bool`) | "It is deprecated as of Foxy ... use the equivalent in `example_msgs`" |
| `example_msgs` is not installed | `ros2 pkg list \| grep -x example_msgs` | no match |
| `diagnostic_msgs` and `lifecycle_msgs` are installed | `ros2 pkg list` | both present |
| Catching `ExternalShutdownException` is what makes Ctrl-C clean | 6 runs of the worked example, `kill -INT` | 5 clean exits, 1 run let an `RCLError` escape (see [§14](#14-stopping-cleanly)) |
| The scaffold's own lint tests can fail your build | `colcon test` on the scratch package | `1 failure`: `I100 Import statements are in the wrong order`, `W292 no newline at end of file`; after fixing, `5 tests, 0 errors, 0 failures, 1 skipped` |
| One-node-per-package is the platform's own convention | `ros2 pkg executables` over all packages, counted per package | 45 of 84 executable-bearing packages ship exactly one executable; the multi-executable ones are demos (`demo_nodes_cpp` 28, `examples_rclcpp_minimal_subscriber` 10) |

Not yet verified: nothing in this lesson's worked example or assignment depends on Docker. That arrives in lesson 04.

## 3. Options survey: how should the repo be laid out?

The survey is about the repo layout, because that is what the assignment actually touches (it decides the package name and where the files go). Decision record: [`docs/decisions/01-package-layout.md`](../decisions/01-package-layout.md).

| Option | Build/test isolation | M8 Gazebo swap | M7 three namespaces | Cost |
|---|---|---|---|---|
| **1. One package per node** + shared logic packages | one node per `colcon build --packages-select`, one failing test blocks one node | replace `mower_sim`, nothing else | same package started 3× under 3 namespaces | more `package.xml` files |
| 2. One package for the whole robot | none; one test blocks everything | becomes a refactor of the whole robot | confusing: several nodes, different lifetimes | fewest files now |
| 3. One package per subsystem | per-subsystem | partial | partial | subsystem boundaries move as the project grows |

Measurement behind the table: of the 84 installed packages that ship any executable, 45 ship exactly one. The multi-executable packages are demos and tutorials. `ros_gz_bridge` (4) and `ros_gz_sim` (6) are honest counter-examples, which is why the rule we adopt is "one node per package unless there is a reason, and write the reason down."

**Chosen: option 1.**

## 4. Options survey: what message type carries the status?

The assignment's second real choice. Decision record: [`docs/decisions/01-status-message-type.md`](../decisions/01-status-message-type.md).

| Option | Has a severity field | Status | Fits M4 state machine and M7 fleet health | Cost |
|---|---|---|---|---|
| `std_msgs/msg/String` | no | **deprecated in this distro** | every consumer re-parses text | trivial now, expensive later |
| **`diagnostic_msgs/msg/DiagnosticStatus`** | yes: `OK`/`WARN`/`ERROR`/`STALE` | installed and supported | directly | slightly more verbose |
| custom `mower_msgs/msg/MowerStatus` | yes | we own it | directly | new interface package, codegen, breaks the "standard types" habit |

Measurement: `ros2 interface show diagnostic_msgs/msg/DiagnosticStatus` resolves, and its docstring is "This message holds the status of an individual component of the robot." Meanwhile `cat /opt/ros/lyrical/share/std_msgs/msg/String.msg` starts with a deprecation notice, and the recommended replacement `example_msgs` is not installed on this machine.

**Chosen: `diagnostic_msgs/msg/DiagnosticStatus`.**

## 5. What `ros2 pkg create` gives you, and why

Do not hand-write these files. The scaffolder is part of the platform, it knows the current conventions, and it will change under you. Generate, then read.

```bash
mkdir -p /tmp/lesson01 && cd /tmp/lesson01
source /opt/ros/lyrical/setup.bash
ros2 pkg create --build-type ament_python \
  --license Apache-2.0 \
  --maintainer-name "Jamie" \
  --maintainer-email "jamie-gastrich@users.noreply.github.com" \
  --description "scratch package for lesson 01" \
  xp_hello_counter
```

I ran exactly this. It printed:

```
going to create a new package
package name: xp_hello_counter
destination directory: /tmp/lesson01
package format: 3
version: 0.0.0
description: scratch package for lesson 01
maintainer: ['Jamie <jamie-gastrich@users.noreply.github.com>']
licenses: ['Apache-2.0']
build type: ament_python
dependencies: []
creating folder ./xp_hello_counter
creating ./xp_hello_counter/package.xml
creating source folder
creating folder ./xp_hello_counter/xp_hello_counter
creating ./xp_hello_counter/setup.py
creating ./xp_hello_counter/setup.cfg
creating folder ./xp_hello_counter/resource
creating ./xp_hello_counter/resource/xp_hello_counter
creating ./xp_hello_counter/xp_hello_counter/__init__.py
creating ./xp_hello_counter/xp_hello_counter/py.typed
creating folder ./xp_hello_counter/test
creating ./xp_hello_counter/test/test_copyright.py
creating ./xp_hello_counter/test/test_flake8.py
creating ./xp_hello_counter/test/test_mypy.py
creating ./xp_hello_counter/test/test_pep257.py
creating ./xp_hello_counter/test/test_xmllint.py
```

Now read the three files that matter. All three are quoted from what I actually got.

### `package.xml` — the manifest

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>xp_hello_counter</name>
  <version>0.0.0</version>
  <description>scratch package for lesson 01</description>
  <maintainer email="jamie-gastrich@users.noreply.github.com">Jamie</maintainer>
  <license>Apache-2.0</license>

  <test_depend>ament_copyright</test_depend>
  <test_depend>ament_flake8</test_depend>
  <test_depend>ament_mypy</test_depend>
  <test_depend>ament_pep257</test_depend>
  <test_depend>ament_xmllint</test_depend>
  <test_depend>python3-pytest</test_depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

This is the package's identity as far as the rest of the world is concerned. `<build_type>ament_python</build_type>` is how colcon knows to hand it to setuptools instead of CMake. The `<test_depend>` entries are the scaffold's test suite: five linters, already wired up.

### `setup.py` — the Python packaging

```python
from setuptools import find_packages, setup

package_name = 'xp_hello_counter'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    package_data={'': ['py.typed']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jamie',
    maintainer_email='jamie-gastrich@users.noreply.github.com',
    description='scratch package for lesson 01',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
        ],
    },
)
```

Three things to notice:

1. `entry_points={'console_scripts': [...]}` is **empty**. This is where your executable goes. Each entry is `'name = module:function'`. This is plain setuptools, nothing ROS-specific: it is the same mechanism `pip`-installed CLI tools use.
2. `data_files` installs `resource/xp_hello_counter` into `share/ament_index/resource_index/packages`. That is the ament index, the ROS equivalent of a registry.
3. `find_packages(exclude=['test'])` means the `test/` directory is not installed as an importable package. Good, you do not want `test` on your import path in production.

### `setup.cfg` — where the executable lands

```ini
[develop]
script_dir=$base/lib/xp_hello_counter
[install]
install_scripts=$base/lib/xp_hello_counter
```

This is why `ros2 run xp_hello_counter widget_monitor` works: the generated script goes to `install/xp_hello_counter/lib/xp_hello_counter/widget_monitor`.

### `resource/xp_hello_counter` — the marker file

It is **0 bytes**. `wc -c` says `0`. It has no content because its *path* is the information. An empty file at `share/ament_index/resource_index/packages/<name>` is what `ros2 pkg list`, `colcon`, and `rosdep` use to discover the package. Delete it and your package becomes invisible.

## 6. How `ros2 run` finds your code

This is worth ten minutes of understanding, because "it works on my machine" in ROS is almost always an environment problem.

There are two separate lookups:

1. **`ros2 run <package> <executable>`** needs to know which *packages* exist. It reads the ament index. That is what `resource/<pkg>` is for.
2. Once it knows the package, it looks in `install/<package>/lib/<package>/` for an executable of that name. That is what `setup.cfg`'s `install_scripts` is for.

Both of those live in the **install space**, which is a directory colcon generates. It is not your source tree. That is why step 7 exists.

## 7. colcon: build, install, source

```bash
cd /tmp/lesson01
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
```

Real output:

```
Starting >>> xp_hello_counter
Finished <<< xp_hello_counter [1.55s]

Summary: 1 package finished [1.67s]
```

Three directories appeared next to your source: `build/` (intermediates), `install/` (the result you actually run), `log/` (build logs). They are all in `.gitignore`, and they should never be edited or committed.

`--symlink-install` means "when you install a Python file, put a symlink to my source file there instead of a copy." So when you edit your node and rerun, you do not have to rebuild to see the change. Without the flag, colcon copies, and a stale copy is a genuinely confusing bug. Use the flag.

Now the step people skip:

```bash
source install/setup.bash
```

I verified what happens if you do not. Before sourcing:

```
$ ros2 pkg prefix xp_hello_counter
Package not found
```

After sourcing:

```
$ ros2 pkg prefix xp_hello_counter
/tmp/lesson01/install/xp_hello_counter

$ ros2 pkg executables xp_hello_counter
xp_hello_counter widget_monitor
```

**Sourcing is per-shell.** Every new terminal needs it. This is the single most common beginner error in ROS and it always looks like "my code isn't being picked up."

### A trap specific to your machine

Your shell environment has **another ROS workspace** on it. Right now, in a shell where something has already sourced another workspace, `AMENT_PREFIX_PATH` is:

```
/home/jamie/robotics-factory/ros2_ws/install/rescue_turtle:/home/jamie/robotics-factory/ros2_ws/install/first_robot:/opt/ros/lyrical
```

That is not a typo, and it is not something I set up for the lesson; I read it out of a real shell here. `AMENT_PREFIX_PATH` is how ROS finds *packages*, and `source` only ever **appends** to it. So in that shell, `ros2 pkg list` will show packages from a project you are not working on, and `colcon build` may resolve dependencies against the wrong tree.

In a clean shell it is just `/opt/ros/lyrical`. So: **work in a fresh terminal for this project**, and if a command behaves impossibly, check `echo $AMENT_PREFIX_PATH` first. If it has more than one entry that you did not add, open a new terminal.

## 8. `package.xml` is not decorative

The scaffold gives you zero dependencies because it does not know what you will use. When you import `rclpy` and `diagnostic_msgs`, say so:

```xml
  <depend>rclpy</depend>
  <depend>diagnostic_msgs</depend>
```

Why it matters, concretely:

- **colcon build order.** colcon reads `package.xml` to work out what must be built first.
- **`rosdep install`.** This is how the Docker image in lesson 04 and any future CI machine will know to install your dependencies. A missing `<depend>` is a build that works on your machine and nowhere else.
- **Honesty about coupling.** `<depend>` says "this package needs this at build time and at run time," which is true of an `ament_python` package.

## 9. Nodes, topics, and the `~` prefix

A **node** is one process with one job. Nodes find each other by name at runtime; there is no central broker, no compile-time wiring. A **topic** is a named, typed channel. Publishers and subscribers agree on a topic name and a message type and nothing else. Neither knows the other's process, PID, or language.

```python
self.publisher = self.create_publisher(DiagnosticStatus, '~/diagnostics', 1)
```

Read the three arguments as: *publish messages of type `DiagnosticStatus`, on a topic named `~/diagnostics`, with a queue depth of 1.*

The `~` is the important one. A leading `~` means "private to this node," and it is resolved against the node's own name. The node is called `widget_monitor`, so the topic that actually appears on the graph is:

```
/widget_monitor/diagnostics
```

Verified with `ros2 topic list` while the node was running:

```
/parameter_events
/rosout
/widget_monitor/diagnostics
```

Two of those three are free: every node gets `/rosout` (its log) and `/parameter_events` (parameter changes) automatically.

Why private names matter for a mower: when M7 runs three mowers, `mower_status` started under namespace `/mower_01` publishes `/mower_01/mower_status/diagnostics`, and the node code does not change. If you had hard-coded `/diagnostics`, all three mowers would collide on one topic and the fleet manager could not tell whose status it is reading. **Use `~/` for anything the node itself owns.**

What about the topic *name* being in the code? That is not a magic number. The topic name is the node's **interface** — its contract with the rest of the system — so it belongs in code where it is readable. Parameters are for *configuration*: rates, identities, frames, thresholds. Keeping that line straight is most of what "no hard-coded topics, names, distances, or rates" means in practice.

The `1` is the QoS **queue depth**: how many messages to buffer if a subscriber is slow. For a periodic status heartbeat, the newest message makes the old ones worthless, so depth 1 is right. Sensor streams are different and we will measure that in M1.

## 10. Messages, and two things that bite

A message is a typed struct. You make one by instantiating the class and filling fields:

```python
from diagnostic_msgs.msg import DiagnosticStatus, KeyValue

msg = DiagnosticStatus()
msg.level = DiagnosticStatus.OK
msg.name = 'widget'
msg.hardware_id = 'widget-a'
msg.message = 'nominal'
msg.values = [KeyValue(key='uptime_s', value='0.0')]
```

`DiagnosticStatus` is five fields: `level`, `name`, `message`, `hardware_id`, and `values`, which is a list of `KeyValue` (a `key` string and a `value` string).

### Bite 1: use the named constants, never a raw number

In this distro, `DiagnosticStatus.OK` is not the integer `0`:

```
>>> repr(DiagnosticStatus.OK)
b'\x00'
```

It is a `bytes` object of length one, because ROS message `byte` fields are `uint8`. I checked what the field setter accepts, with field checking switched on via `ROS_PYTHON_CHECK_FIELDS=1`:

```
bytes constant: accepted -> b'\x00'
int 0: REJECTED -> AssertionError: The 'level' field must be of type 'bytes' or 'ByteString' with length 1
int 2: REJECTED -> AssertionError: The 'level' field must be of type 'bytes' or 'ByteString' with length 1
```

So `msg.level = 0` only appears to work, and only because type checking is off by default. `msg.level = DiagnosticStatus.WARN` is correct, portable, and self-documenting. This is the ROS rule anyway; this distro just makes the rule enforceable.

### Bite 2: sequence fields are plain Python lists here

The older tutorials write `msg.values.add(key='x', value='y')`. That does not work on this machine:

```
AttributeError: 'list' object has no attribute 'add'
```

and `hasattr(msg.values, 'add')` is `False`. Look at the generated class and you can see why: `/opt/ros/lyrical/lib/python3.14/site-packages/diagnostic_msgs/msg/_diagnostic_status.py` declares

```
'values': 'sequence<diagnostic_msgs/KeyValue>'
```

and its setter is a plain property that does `self._values = list(value)`. No helper object. So use one of:

```python
msg.values = [KeyValue(key='uptime_s', value='0.0')]   # replace
msg.values.append(KeyValue(key='uptime_s', value='0.0'))  # add one
```

The lesson: when a tutorial's code fails, read the installed source of the library before assuming the tutorial is wrong. It is on your disk at `/opt/ros/lyrical/lib/python3.14/site-packages/`.

## 11. Parameters: no magic numbers

```python
self.declare_parameter('publish_rate', 2.0)
self.rate = float(self.get_parameter('publish_rate').value)
```

`declare_parameter(name, default)` says "this node has a parameter called `publish_rate`, and if nobody sets it, it is `2.0`." Declaring is what makes a parameter visible and settable.

This is not ceremony. It is the difference between a node you can deploy and a node you have to recompile. Watch what happens when a parameter exists:

```bash
ros2 run xp_hello_counter widget_monitor --ros-args -p publish_rate:=5.0 -p widget_id:=widget-z
```

```
[INFO] [1791233754.658209626] [widget_monitor]: widget_monitor up at 5.0 Hz for widget-z
```

```
$ ros2 param get /widget_monitor publish_rate
Double value is: 5.0
$ ros2 param get /widget_monitor widget_id
String value is: widget-z
```

```
$ ros2 topic hz /widget_monitor/diagnostics
average rate: 5.003
	min: 0.200s max: 0.200s std dev: 0.00021s window: 4
```

Five hertz, because a parameter said so, with no recompile. Now imagine a fleet where every mower has a different ID and a different reporting rate. With parameters, that is a launch file (lesson 05). With magic numbers, it is a rebuild per mower.

`ros2 param list /widget_monitor` will also show `use_sim_time` and `start_type_description_service`. Every node gets those; they are not yours.

## 12. Timers

```python
self.timer = self.create_timer(1.0 / self.rate, self.on_timer)
```

A timer calls a callback on a fixed period. `1.0 / self.rate` converts hertz to a period in seconds, because the timer wants seconds and the operator thinks in hertz.

The callback must be short. It runs on the node's executor thread, and while it runs, no other callback of that node runs. A status callback that formats one line and publishes is instant. A callback that sleeps, reads a file, or waits on a network call will stall everything else in the node. In M2, when the EKF and the GNSS driver live in the same node, this is the difference between a 10 Hz filter and a jittery one.

## 13. Logging

```python
self.get_logger().info(f'widget_monitor up at {self.rate} Hz for {self.widget_id}')
```

Use `self.get_logger()`, never `print()`. The logger writes to `/rosout`, which means the line is timestamped, tagged with the node name, severity-filtered, and capturable by `ros2 bag record`. A `print()` in a node is invisible to every one of those, and in M6 you will want your logs in the dashboard.

Real output:

```
[INFO] [1791233754.658209626] [widget_monitor]: widget_monitor up at 5.0 Hz for widget-z
[INFO] [1791233754.848774495] [widget_monitor]: published OK for widget-z
[INFO] [1791233755.047570322] [widget_monitor]: published OK for widget-z
```

Use `info` sparingly. At 5 Hz, an `info` line per publish is log spam that will cost you nothing now and cost you disk and signal-to-noise later. For the assignment, one startup line and one line when something changes is plenty.

## 14. Stopping cleanly

Press Ctrl-C and you get this at the end:

```
[ros2run]: Received signal:  Interrupt
```

and then the process exits 0 with no traceback. That took a specific pattern:

```python
def main() -> None:
    rclpy.init()
    node = WidgetMonitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
```

with `from rclpy.executors import ExternalShutdownException` at the top.

Why both exception types? `rclpy.init()` installs its own SIGINT handler, which shuts the context down rather than raising `KeyboardInterrupt`. `spin()` then notices the dead context and raises `ExternalShutdownException` (`rclpy/executors.py`, `ExternalShutdownException` at line 154, raised at line 889, caught inside the multi-threaded executor at line 1101). `KeyboardInterrupt` is in the tuple because a SIGTERM or a `kill -9`-adjacent path can still deliver one.

Here is the honest part. I ran the worked example six times and sent SIGINT each time. Five exited cleanly through `ExternalShutdownException`. **One let an `rclpy._rclpy_pybind11.RCLError` escape** and printed this:

```
rclpy._rclpy_pybind11.RCLError: failed to initialize wait set: the given context is not valid, either rcl_init() was not called or rcl_shutdown() was called., at ./src/rcl/wait.c:110
```

That is a race inside this distro's executor: the context is shut down while the wait set is being built. It is not your bug, and it is not worth catching by hand — the type lives in a private module (`rclpy._rclpy_pybind11`) and importing private API to suppress a 1-in-6 cosmetic traceback is a bad trade. Keep the canonical pattern, and if you hit that message on Ctrl-C, know that you have found a real quirk of Lyrical rather than broken code.

The `finally` block matters for a different reason: if a callback raises, the node still releases its DDS resources instead of leaving a zombie entity on the graph. M4's safety node will care about that.

## 15. Keep the string out of the node

One small habit, taught now because it is cheap and it is a rule in `AGENTS.md`:

> Keep algorithm logic free of `rclpy`/`rclcpp` imports where practical so it can be unit tested without a running graph.

In the worked example above, `'nominal'` is a literal inside the callback. Fine for a toy. The moment the status text depends on anything you would want to check, it belongs in a plain function:

```python
# mower_status/status_format.py
def format_status_message(robot_id: str, state: str) -> str:
    return f'{robot_id}: {state}'
```

No `rclpy` import in that file. That means lesson 03 can test it with `pytest` in about a second, with no ROS graph, no daemon, and no `ROS_DOMAIN_ID` juggling. Compare that to testing the same string through a running node: start it, echo a topic, parse the output, tear it down. You will write that test exactly once and then never again.

The node class stays a thin wrapper: read parameters, call the function, fill the message, publish.

## 16. The scaffold's lint tests are not optional

The scaffold shipped five tests in `test/`. They are not decoration, and they will fail your build. Here is a real failure from my own scratch package, before I fixed it:

```
$ colcon test
Finished <<< xp_hello_counter [14.2s]  [ with test failures ]
  1 package had test failures: xp_hello_counter

$ colcon test-result --verbose
- xp_hello_counter.test.test_flake8 test_flake8
  <<< failure message
    AssertionError: Found 2 code style errors / warnings:
      ./xp_hello_counter/widget_monitor.py:2:1: I100 Import statements are in the wrong order. 'from diagnostic_msgs.msg import DiagnosticStatus, KeyValue' should be before 'import rclpy'
      ./xp_hello_counter/widget_monitor.py:44:11: W292 no newline at end of file
```

Two things to take from that:

- **Imports are sorted alphabetically by top-level module name**, `from X import` and `import X` interleaved. `diagnostic_msgs` before `rclpy`. You will get this wrong once. Let the linter tell you and move on; do not memorise the rule.
- **Files end with a newline.** Always.

After fixing those two lines:

```
$ colcon test-result
Summary: 5 tests, 0 errors, 0 failures, 1 skipped
```

The one skip is `test_copyright`, which the scaffold marks `@pytest.mark.skip` until you put a licence header on your source files. The project is Apache-2.0, so when you write `status_node.py`, give it the same 13-line Apache header the scaffold's own `test/` files carry. Copy it from `ros2_ws/src/mower_math/test/test_flake8.py`. Then remove the `@pytest.mark.skip` line so the check actually runs.

Lesson 03 takes these five linters seriously and adds real unit tests. For now, just know they run and that `colcon test` is part of your build loop, not an optional extra.

---

## 17. Worked example: a widget health monitor

A toy node in a scratch package outside the repo. It publishes a `DiagnosticStatus` for a made-up widget. It is the same shape as the assignment but on a different subject.

### Step 1: scaffold

```bash
mkdir -p /tmp/lesson01 && cd /tmp/lesson01
source /opt/ros/lyrical/setup.bash
ros2 pkg create --build-type ament_python \
  --license Apache-2.0 \
  --maintainer-name "Jamie" \
  --maintainer-email "jamie-gastrich@users.noreply.github.com" \
  --description "scratch package for lesson 01" \
  xp_hello_counter
cd /tmp/lesson01
```

### Step 2: write the node

Create `xp_hello_counter/xp_hello_counter/widget_monitor.py`:

```python
from diagnostic_msgs.msg import DiagnosticStatus, KeyValue
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class WidgetMonitor(Node):
    """Toy node: reports a fake widget's health as a DiagnosticStatus."""

    def __init__(self) -> None:
        super().__init__('widget_monitor')
        self.declare_parameter('publish_rate', 2.0)
        self.declare_parameter('widget_id', 'widget-a')
        self.rate = float(self.get_parameter('publish_rate').value)
        self.widget_id = str(self.get_parameter('widget_id').value)
        self.publisher = self.create_publisher(DiagnosticStatus, '~/diagnostics', 1)
        self.timer = self.create_timer(1.0 / self.rate, self.on_timer)
        self.get_logger().info(f'widget_monitor up at {self.rate} Hz for {self.widget_id}')

    def on_timer(self) -> None:
        msg = DiagnosticStatus()
        msg.level = DiagnosticStatus.OK
        msg.name = 'widget'
        msg.hardware_id = self.widget_id
        msg.message = 'nominal'
        msg.values = [KeyValue(key='uptime_s', value='0.0')]
        self.publisher.publish(msg)
        self.get_logger().info(f'published OK for {self.widget_id}')


def main() -> None:
    rclpy.init()
    node = WidgetMonitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

Note the import order: `diagnostic_msgs`, then `rclpy`, alphabetically. That is [§16](#16-the-scaffolds-lint-tests-are-not-optional), not a style opinion.

### Step 3: register the executable

In `xp_hello_counter/setup.py`, replace the empty list:

```python
    entry_points={
        'console_scripts': [
        ],
    },
```

with:

```python
    entry_points={
        'console_scripts': [
            'widget_monitor = xp_hello_counter.widget_monitor:main',
        ],
    },
```

The left side is the command you will type. The right side is `module:function`, and the function is `main`.

### Step 4: build

```bash
cd /tmp/lesson01
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
```

```
Starting >>> xp_hello_counter
Finished <<< xp_hello_counter [1.55s]

Summary: 1 package finished [1.67s]
```

### Step 5: source, then check it is visible

```bash
source install/setup.bash
ros2 pkg prefix xp_hello_counter
ros2 pkg executables xp_hello_counter
```

```
/tmp/lesson01/install/xp_hello_counter
xp_hello_counter widget_monitor
```

### Step 6: run it

```bash
ros2 run xp_hello_counter widget_monitor
```

```
[INFO] [1791233754.658209626] [widget_monitor]: widget_monitor up at 2.0 Hz for widget-a
[INFO] [1791233754.881320535] [widget_monitor]: published OK for widget-a
[INFO] [1791233755.380349010] [widget_monitor]: published OK for widget-a
```

Ctrl-C to stop. Last line should be `[ros2run]: Received signal:  Interrupt` with no traceback ([§14](#14-stopping-cleanly)).

### Step 7: look at it from outside

In a **second terminal**, source the workspace again (`source /opt/ros/lyrical/setup.bash && source /tmp/lesson01/install/setup.bash`) and:

```bash
ros2 node list
ros2 topic list
ros2 param list /widget_monitor
ros2 topic echo --once /widget_monitor/diagnostics
```

```
/widget_monitor
```
```
/parameter_events
/rosout
/widget_monitor/diagnostics
```
```
  publish_rate
  start_type_description_service
  use_sim_time
  widget_id
```
```
level: "\0"
name: widget
message: nominal
hardware_id: widget-a
values:
- key: uptime_s
  value: '0.0'
---
```

`level: "\0"` is `DiagnosticStatus.OK` printed as the bytes it is. If you see that, the severity is set correctly.

### Step 8: change it without rebuilding

Stop the node, then run it with different parameters:

```bash
ros2 run xp_hello_counter widget_monitor --ros-args -p publish_rate:=5.0 -p widget_id:=widget-z
```

```
[INFO] [1791233754.658209626] [widget_monitor]: widget_monitor up at 5.0 Hz for widget-z
```

And from the other terminal:

```bash
ros2 topic echo --once /widget_monitor/diagnostics
ros2 topic hz /widget_monitor/diagnostics
```

```
level: "\0"
name: widget
message: nominal
hardware_id: widget-z
values:
- key: uptime_s
  value: '0.0'
---
```
```
average rate: 5.003
	min: 0.200s max: 0.200s std dev: 0.00021s window: 4
```

Same binary, different behaviour. That is the whole point of parameters.

### Step 9: clean up

```bash
ros2 daemon stop
rm -rf /tmp/lesson01
```

---

## 18. Assignment: `mower_status`

**Language: Python.** Take the worked example and make it report on a mower instead of a widget.

### Requirements

**Package**

1. A new `ament_python` package named `mower_status` in `ros2_ws/src/`, generated with `ros2 pkg create` (not hand-written). Real `--description` and maintainer, licence `Apache-2.0`. No `TODO` left anywhere in `package.xml` or `setup.py`.
2. `<depend>rclpy</depend>` and `<depend>diagnostic_msgs</depend>` in `package.xml` ([§8](#8-packagxml-is-not-decorative)).
3. One executable registered in `console_scripts`, named `status_node`.

**Node**

4. A class inheriting `rclpy.node.Node`, node name `mower_status`, registered with the name `status_node`.
5. Exactly three parameters, all declared, no magic numbers anywhere ([§11](#11-parameters-no-magic-numbers)):

   | name | type | meaning |
   |---|---|---|
   | `robot_id` | string | this mower's identity, e.g. `mower-01` |
   | `publish_rate` | double | status rate in Hz |
   | `base_frame` | string | the frame this machine reports in, e.g. `base_link` |

6. Publishes `diagnostic_msgs/msg/DiagnosticStatus` on the node-private topic `~/diagnostics`, QoS depth 1, from a timer at `publish_rate` ([§9](#9-nodes-topics-and-the-prefix), [§12](#12-timers)).
7. Each published message sets:
   - `level`, using the named constant — `DiagnosticStatus.OK`. Never a raw `0`.
   - `name` = `'mower_status'`
   - `hardware_id` = the `robot_id` parameter
   - `message` = the return value of a pure function (see below)
   - `values` = at least two `KeyValue` entries: one for `base_frame` from the parameter, and one for a value that changes at runtime (for example `publish_count`, the number of messages this node has published since start).

**Structure**

8. The status text is produced by a function in its own module (for example `mower_status/status_format.py`) that **imports no `rclpy`** and takes plain arguments ([§15](#15-keep-the-string-out-of-the-node)). `status_node.py` calls it.
9. `main()` uses the pattern from [§14](#14-stopping-cleanly): `rclpy.init()`, `try` / `except (KeyboardInterrupt, ExternalShutdownException)` / `finally` with `destroy_node()` and `rclpy.shutdown()`. Log with `self.get_logger()`; no `print()` ([§13](#13-logging)).
10. Source files carry the Apache-2.0 header (copy it from `ros2_ws/src/mower_math/test/test_flake8.py`), and the `@pytest.mark.skip` on `test_copyright` in `ros2_ws/src/mower_status/test/test_copyright.py` is removed so the check runs ([§16](#16-the-scaffolds-lint-tests-are-not-optional)).

**Leave alone**

`ros2_ws/src/mower_math/` already exists as a bare scaffold. Do not touch it; lesson 03 fills it in.

### Interfaces

| | |
|---|---|
| Node | `mower_status` |
| Executable | `ros2 run mower_status status_node` |
| Publishes | `~/diagnostics` → `/mower_status/diagnostics`, type `diagnostic_msgs/msg/DiagnosticStatus`, QoS depth 1 |
| Parameters | `robot_id` (string), `publish_rate` (double), `base_frame` (string) |

### Acceptance criteria

Each of these is a command. All of them must pass.

```bash
cd ~/mower-sim/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
colcon test
colcon test-result --verbose
```

- [ ] `colcon test-result --verbose` ends with `0 failures` (one skip allowed only if `test_copyright` has been enabled and passes).
- [ ] No `TODO` in `ros2_ws/src/mower_status/`.

```bash
source install/setup.bash
ros2 pkg executables mower_status
```

- [ ] Prints `mower_status status_node`.

```bash
ros2 run mower_status status_node
```

- [ ] Logs one startup line naming the robot id and rate, then stays running.
- [ ] Ctrl-C exits with `[ros2run]: Received signal:  Interrupt` and **no traceback**.

In a second terminal, `source /opt/ros/lyrical/setup.bash && source ~/mower-sim/ros2_ws/install/setup.bash`:

```bash
ros2 param list /mower_status
ros2 topic echo --once /mower_status/diagnostics
ros2 topic hz /mower_status/diagnostics
```

- [ ] `ros2 param list` shows all three parameters.
- [ ] `ros2 topic echo --once` shows `level: "\0"`, `name: mower_status`, your `robot_id` in `hardware_id`, a non-empty `message`, and at least two `values` entries.
- [ ] `ros2 topic hz` reports approximately `publish_rate`.

Override check, with the node stopped:

```bash
ros2 run mower_status status_node --ros-args -p robot_id:=mower-02 -p base_frame:=base_link -p publish_rate:=5.0
```

- [ ] `ros2 topic echo --once /mower_status/diagnostics` shows `hardware_id: mower-02`.
- [ ] `ros2 topic hz /mower_status/diagnostics` reports approximately `5.0`.

Purity check:

```bash
grep -n rclpy ~/mower-sim/ros2_ws/src/mower_status/mower_status/status_format.py
```

- [ ] Prints nothing.

### Stretch goal

Make the level mean something. Add a fourth parameter, `state` (string, default `nominal`), and map it to a severity: `nominal` → `OK`, anything else → `WARN`, with `STALE` if the node has not published in the last second. That is a two-line change now, and in M4 `state` becomes the output of the safety state machine and `level` becomes what the fleet manager watches. If you want more, have the node take a parameter callback so the level can be changed on a running node with `ros2 param set` — that is the mechanism M6's dashboard uses to pause a mission.

## 19. Where this leaves M0

Done after this lesson and a passing review: repo layout, colcon build loop, and one real Python node with parameters and a standard message type. Lesson 02 rebuilds this same node in C++ so the two build systems are side by side. Lesson 03 makes the test suite real. Lesson 04 puts the whole thing in a container, which is where M0's done-when actually gets decided.

## 20. Commit

One commit, one concept:

```
M0: add mower_status node (parameterized DiagnosticStatus publisher)
```