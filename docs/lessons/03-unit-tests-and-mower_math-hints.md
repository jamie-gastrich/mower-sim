# Hints for 03 - Making `colcon test` mean something

Three tiers. Read the first. Only if you are stuck, read the second. The third is close to a solution — use it to check your reasoning, not to skip the thinking.

---

## Tier 1: nudges

**`colcon test` says all your tests passed, but you know you wrote a failing case.**

pytest only collects files named `test_*.py` in the `test/` directory. If your file is `math_utils.py` or `test_math.py` in the wrong folder, it is silently ignored. Check the file name, then re-run `colcon test`. Also: `colcon test` can serve a cached (green) result — if you change a test, rebuild first or run `colcon test --packages-select <pkg>` again.

**`ModuleNotFoundError: No module named 'mower_math'` from a unit test.**

The test imports the package, so the package must be importable. Two requirements: you built (`colcon build --symlink-install`) and you sourced `install/setup.bash` in this shell. Both, in that order — the lesson-01 trap, alive again.

**`mower_math` still shows a skipped test after you added source files.**

The `@pytest.mark.skip(...)` line is still in `mower_math/test/test_copyright.py`. Delete that decorator (keep the line below it). Then add an Apache header — `# Copyright 2026 Jamie` plus the licence block — to every source file you wrote, or `test_copyright` fails on your new files instead of skipping.

**You get TWO `2.0` in `status_node.py` and a voice in your head says "that's review 01 again".**

Yes. The whole point of requirement 5–6 is to have exactly one copy of the default: the constant `DEFAULT_PUBLISH_RATE` in `status_format.py`, imported into the node. Declare the parameter with the constant, and make the fallback come out of `validate_publish_rate`. If you can `grep -n 2.0` the node file, you have not finished.

**The refactored node warns but the message still reads "Publish rate must be positive…".**

Review 01 asked for the warning to name the parameter: `publish_rate must be positive, falling back to X Hz`. `Publish rate` (human case) will not match a log grep for `publish_rate`. Use the small `f'publish_rate must be positive, falling back to {self.rate} Hz'` form, or your own wording that contains the parameter's name exactly.

**pytest left a `__pycache__/` or `.pytest_cache/` behind.**

Expected and fine — do not commit them.

---

## Tier 2: directions

**Structure for `mower_math`.** Add two files next to the scaffold files:

- `ros2_ws/src/mower_math/mower_math/math_utils.py` — both pure functions, types on the signature and parameters, no ROS import.
- `ros2_ws/src/mower_math/test/test_math_utils.py` — imports from the installed package: `from mower_math.math_utils import clamp, wrap_angle_rad`. No `sys.path` hacks; the workspace being sourced is what makes the import work.

**Enabling copyright in `mower_math`.** This is exactly lesson 01 §16, second package: open `test/test_copyright.py`, delete the whole `@pytest.mark.skip(reason='No copyright header has been placed in the generated source file.')` line, then put the 13-line Apache-2.0 header on `math_utils.py`. Leave the scaffold's own `test/` files alone — they keep OSRF's copyright; that is the template, not your work.

**`clamp` and `wrap_angle_rad` shapes.** Both stay boringly pure:

- `clamp`: `return max(low, min(high, value))` — that is the whole body. Verify it by hand on the three parametrize rows before you write them.
- `wrap_angle_rad`: subtract/add `2.0 * math.pi` in a loop until the angle sits in `(-π, π]`. Be careful with the exact boundary — a case like exactly `+π` should land on `-π` or `+π` but must not hang the loop. `import math` inside the function (or at module top) is fine; it is not a ROS import.

**Unit tests for `mower_status`.** Add `test/test_status_format.py` next to the scaffold linters:

```python
import pytest

from mower_status.status_format import (
    DEFAULT_PUBLISH_RATE,
    format_status_message,
    validate_publish_rate,
)
```

Then two groups of cases:

- `format_status_message(robot_id, state) == f'{robot_id}: {state}'`.
- `validate_publish_rate`: positive value comes back unchanged; `0.0` and a negative value both come back equal to `DEFAULT_PUBLISH_RATE`; and the odd-but-true case `validate_publish_rate(DEFAULT_PUBLISH_RATE)` returns it unchanged. Use `pytest.approx` if floats are involved anywhere.

**The node-side refactor**, if you are not sure where the three changes go in `status_node.py`:

1. Import the constant and the function next to `format_status_message`.
2. Replace `self.declare_parameter('publish_rate', 2.0)` with the constant.
3. After reading the parameter, run it through `validate_publish_rate`, remember the raw value, and log only when they differ.

The rest of the node does not change.

**Command order for a clean check:**

```bash
cd ~/mower-sim/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --packages-select mower_math mower_status
colcon test-result --verbose --test-result-base build/mower_math
colcon test-result --verbose --test-result-base build/mower_status
```

---

## Tier 3: near-solution

Close enough to check yourself against. Do not paste without understanding each line — the reviewer will ask.

**`mower_math/mower_math/math_utils.py`**

```python
# Copyright 2026 Jamie
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ... full Apache-2.0 block, copy it ...

import math


def clamp(value: float, low: float, high: float) -> float:
    """Return value restricted to [low, high]."""
    return max(low, min(high, value))


def wrap_angle_rad(angle: float) -> float:
    """Normalise an angle in radians to the interval (-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle <= -math.pi:
        angle += 2.0 * math.pi
    return angle
```

Boundary choice to think about: this version folds `-π` up to `+π` (the `<=` branch) so the result is *always* in `(-π, π]`.

**`mower_math/test/test_math_utils.py`**

```python
import pytest

from mower_math.math_utils import clamp, wrap_angle_rad


@pytest.mark.parametrize('value, low, high, expected', [
    (5.0, 0.0, 3.0, 3.0),
    (-1.0, 0.0, 3.0, 0.0),
    (2.0, 0.0, 3.0, 2.0),
])
def test_clamp(value: float, low: float, high: float, expected: float) -> None:
    assert clamp(value, low, high) == expected


@pytest.mark.parametrize('angle', [3.5, -3.5, 10.0, -10.0, 3.1415926535])
def test_wrap_angle_rad_stays_in_range(angle: float) -> None:
    assert -math_pi < wrap_angle_rad(angle) <= math_pi
```

(Define `math_pi` — `from math import pi as math_pi` — rather than re-typing π approximations.)

**`mower_status/mower_status/status_format.py` additions**

```python
DEFAULT_PUBLISH_RATE: float = 2.0


def validate_publish_rate(rate: float) -> float:
    """Return rate if positive, else the safe default."""
    return rate if rate > 0.0 else DEFAULT_PUBLISH_RATE
```

**`status_node.py` — the three touched lines**

```python
from .status_format import DEFAULT_PUBLISH_RATE, format_status_message, validate_publish_rate
...
self.declare_parameter('publish_rate', DEFAULT_PUBLISH_RATE)
...
raw_rate = float(self.get_parameter('publish_rate').value)
self.rate = validate_publish_rate(raw_rate)
if self.rate != raw_rate:
    self.get_logger().warning(
        f'publish_rate must be positive, falling back to {self.rate} Hz')
```

**What `colcon test-result --test-result-base build/mower_math --verbose` should end with**

```
Summary: 6 tests, 0 errors, 0 failures, 0 skipped
```

(six = the five linters with copyright now enabled + your unit test file; the exact number counts every parametrized case, so matching the summary number is not what matters — what matters is zero failures **and zero skipped**.)

**The node behaviour re-check after the refactor**

```
[WARN] ... publish_rate must be positive, falling back to 2.0 Hz
```

node stays alive, `grep -c ZeroDivisionError` → `0`. Exactly what lesson 01 certified, now with one source of truth for the default instead of two.