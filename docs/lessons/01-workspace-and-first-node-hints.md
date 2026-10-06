# Hints for 01 - The workspace, the package, and your first node

Three tiers. Read the first. Only if you are stuck, read the second. The third is close to a solution — use it to check your reasoning, not to skip the thinking.

---

## Tier 1: nudges

**"Package not found" after a successful build.**

You have not sourced the workspace in this shell. `source install/setup.bash` from `ros2_ws/`, in every terminal, every time.

**`ros2 run mower_status status_node` says the executable does not exist, but you just added it to `setup.py`.**

Two possibilities. You did not rebuild. Or you did not source again after rebuilding. Both are common; do both.

**`ros2 topic list` does not show `/status_node/diagnostics`.**

Check three things in order: is the node actually running, is the topic name `~/diagnostics` (with the tilde, and spelled `diagnostics`), and are you looking at the same `ROS_DOMAIN_ID` as the node. Run `ros2 node list` — if your node is not in that list, nothing else matters.

**`ros2 topic echo --once` prints nothing and hangs.**

Nothing has been published yet. Wait, or check the node is alive. Also check you did not mistype the topic: `ros2 topic list` shows the real name, including the node name prefix.

**`colcon test` fails with `I100 Import statements are in the wrong order`.**

Sort imports alphabetically by the top-level module name, mixing `import X` and `from X import` together. `diagnostic_msgs` comes before `rclpy`.

**`colcon test` fails with `W292 no newline at end of file`.**

The file does not end with a newline character. Add one.

**Your status message looks empty in `ros2 topic echo`.**

You probably created the `DiagnosticStatus()`, filled it in a local variable, and published a *different*, fresh instance. Or you forgot `msg.values = [...]` and never appended, so the list is empty.

**`ros2 topic hz` reports a different rate than you set.**

You set `publish_rate` but the node was started without the override, or you are watching a leftover node from a previous run. `ros2 node list` and `ros2 param get /status_node publish_rate` will tell you which node you are actually looking at.

---

## Tier 2: directions

**Scaffolding the package.** Run this from inside `ros2_ws/src/` (the scaffolder creates the package folder in your current directory, so run it one level above where the package should end up). Full command:

```bash
cd ~/mower-sim/ros2_ws/src
source /opt/ros/lyrical/setup.bash
ros2 pkg create --build-type ament_python \
  --license Apache-2.0 \
  --maintainer-name "Jamie" \
  --maintainer-email "jamie-gastrich@users.noreply.github.com" \
  --description "Publishes mower health as diagnostic_msgs/msg/DiagnosticStatus" \
  mower_status
```

**Wiring the executable.** `setup.py` already has an `entry_points={'console_scripts': []}` block. Add one string per executable in the form `command_name = package.module:function`. Your module is `mower_status.status_node` and your function is `main`.

**Which module goes where.** Two files inside the inner package directory:

- `mower_status/status_format.py` — the pure function. Imports nothing from ROS. This is the file the `grep -n rclpy` check must come back empty for.
- `mower_status/status_node.py` — the node class plus `main()`.

Both live in `ros2_ws/src/mower_status/mower_status/`, next to the `__init__.py` the scaffold created.

**Reading a declared parameter back out.** `declare_parameter` registers the name and default; it does not hand you a usable value. You need a second call to read it. The type coming back is a generic parameter value, so wrap it: `float(...)` for the rate, `str(...)` for the ids.

**Filling the message.** Build it once per callback:

```python
msg = DiagnosticStatus()
msg.level = DiagnosticStatus.OK
```

The constants live on the class you imported, so `DiagnosticStatus.OK` works without importing anything else. For the key/value pairs you need the element type too: `from diagnostic_msgs.msg import DiagnosticStatus, KeyValue`, then `msg.values = [KeyValue(key='base_frame', value=self.base_frame)]`.

**The runtime-changing value.** Keep a counter on the node, `self.publish_count = 0`, increment it in the callback, and put it in a `KeyValue` formatted as a string. Key and value are both strings in this message, so `str(self.publish_count)`.

**The pure function's signature.** Keep it boring: take the plain values it needs, return a string. Something like `format_status_message(robot_id: str, state: str) -> str`. The node reads the parameters and passes them in. If your function needs `self`, it is not pure yet.

**Clean shutdown.** Three things, all in `main()`: `rclpy.init()` before you construct the node, a `try` around `rclpy.spin(node)`, and a `finally` that calls `node.destroy_node()` then `rclpy.shutdown()`. The `except` clause catches a tuple of two exception types, one of which you must import from `rclpy.executors`.

**The Apache header.** Every file in `ros2_ws/src/mower_math/test/` starts with a 13-line Apache-2.0 comment block — copy the structure, but **change the first line to `Copyright 2026 Jamie`**, not OSRF's. Those test files say `Copyright 2017 Open Source Robotics Foundation, Inc.` because OSRF wrote them for the template; that name is not the holder of your code. `ament_copyright` checks the licence text, not who claims it, so a wrong name passes silently. Then open `ros2_ws/src/mower_status/test/test_copyright.py`, find the `@pytest.mark.skip(...)` line, and delete it, so the copyright test actually checks something.

---

## Tier 3: near-solution

Close enough to check yourself against. Do not paste this without understanding each line — the reviewer will ask.

**`mower_status/status_format.py`**

```python
# Copyright 2026 Jamie
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ... full Apache-2.0 block, copy it ...

def format_status_message(robot_id: str, state: str) -> str:
    return f'{robot_id} reporting {state}'
```

**`mower_status/status_node.py`**

```python
# Copyright 2026 Jamie
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ... full Apache-2.0 block, copy it ...

from diagnostic_msgs.msg import DiagnosticStatus, KeyValue
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from mower_status.status_format import format_status_message


class MowerStatus(Node):
    """Publishes this mower's health as a diagnostic_msgs/msg/DiagnosticStatus."""

    def __init__(self) -> None:
        super().__init__('status_node')
        self.declare_parameter('robot_id', 'mower-01')
        self.declare_parameter('publish_rate', 1.0)
        self.declare_parameter('base_frame', 'base_link')

        self.robot_id = str(self.get_parameter('robot_id').value)
        self.rate = float(self.get_parameter('publish_rate').value)
        self.base_frame = str(self.get_parameter('base_frame').value)
        self.publish_count = 0

        self.publisher = self.create_publisher(DiagnosticStatus, '~/diagnostics', 1)
        self.timer = self.create_timer(1.0 / self.rate, self.on_publish)
        self.get_logger().info(
            f'status_node up: id={self.robot_id} rate={self.rate} frame={self.base_frame}')

    def on_publish(self) -> None:
        self.publish_count += 1
        msg = DiagnosticStatus()
        msg.level = DiagnosticStatus.OK
        msg.name = 'status_node'
        msg.hardware_id = self.robot_id
        msg.message = format_status_message(self.robot_id, 'nominal')
        msg.values = [
            KeyValue(key='base_frame', value=self.base_frame),
            KeyValue(key='publish_count', value=str(self.publish_count)),
        ]
        self.publisher.publish(msg)


def main() -> None:
    rclpy.init()
    node = MowerStatus()
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

**`setup.py`**

```python
    entry_points={
        'console_scripts': [
            'status_node = mower_status.status_node:main',
        ],
    },
```

**`package.xml`**

```xml
  <depend>rclpy</depend>
  <depend>diagnostic_msgs</depend>
```

**What `ros2 topic echo --once /status_node/diagnostics` should look like**

```
level: "\0"
name: status_node
message: mower-01 reporting nominal
hardware_id: mower-01
values:
- key: base_frame
  value: base_link
- key: publish_count
  value: '1'
---
```

`level: "\0"` is correct, not a bug. See lesson section 10.

**If the stretch goal is confusing**, the smallest version is a fourth parameter and a dict lookup, chosen in `__init__`:

```python
self.declare_parameter('state', 'nominal')
self.state = str(self.get_parameter('state').value)
```

then inside the callback, instead of the fixed `DiagnosticStatus.OK`:

```python
levels = {
    'nominal': DiagnosticStatus.OK,
    'degraded': DiagnosticStatus.WARN,
}
msg.level = levels.get(self.state, DiagnosticStatus.WARN)
```

and pass `self.state` into `format_status_message`. The parameter-callback version (`add_on_set_parameters_callback`) is the follow-on; do the lookup first.