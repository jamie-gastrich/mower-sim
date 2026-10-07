# Hints for 05 - Kinematics pure functions (Phase A of M1)

Three tiers. Open only when stuck, and stop at the first tier that unblocks you:

1. **Nudge** — you know the area, you lost the thread.
2. **Direction** — the shape of the fix, in prose.
3. **Near-solution** — enough to type your way out; still *you* writing the real files.

Everything here assumes you have read the lesson section named in each header. The lecture already contains the finished functions — the hints are for when you are staring at your own blank file, not for when you skipped the lecture.

---

## 1. `wrap_angle_rad` fix (requirement 1, lesson §7)

**Nudge.** Pristine measured facts: the docstring says `[-π, π]`, `wrap(-π)` returns `-π`, and the existing row list has no `-π` in it. The red output you are aiming to reproduce first is `1 failed, 8 passed` with `assert -3.141592653589793 < -3.141592653589793`.

**Direction.** Three edits, two files: docstring, guard, row. The guard belongs on the **result** of `atan2`, not on the input — the input can be any float (`3.0 + 0.25` is one of the measured rows that lands on the boundary too). Add `-math_pi` to the existing `@pytest.mark.parametrize('angle', [...])` list; `math_pi` is already imported in that file.

**Near-solution.**

```python
def wrap_angle_rad(angle: float) -> float:
    """Wrap an angle in radians to the range (-π, π]."""
    res = math.atan2(math.sin(angle), math.cos(angle))
    if res == -math.pi:
        return math.pi
    return res
```

Sanity: `python3 -m pytest test/test_math_utils.py -q` → `9 passed` (8 before + your row).

---

## 2. `limit_twist` (requirement 2, lesson §5)

**Nudge.** Three limits can bind: `max_linear`, `max_angular`, and the radius. The radius one is a *ratio*, so it has to be evaluated against the speed you actually ended up with — clamp `v` first, then derive the `ω` bound from the clamped value. And two inputs switch the radius rule off entirely: `v == 0` (in-place spin — teleop's `j`/`l` really commands it) and `min_radius <= 0` (disabled/invalid parameter).

**Direction.** Structure:

1. `v_clamped = clamp(v, -max_linear, max_linear)`.
2. Start `limit_w = max_angular`.
3. If `v_clamped != 0.0 and min_radius > 0.0`: `limit_w = min(max_angular, abs(v_clamped) / min_radius)` — the `min` is what makes *both* angular limits bind; `abs()` is what makes reversing behave.
4. Return `(v_clamped, clamp(w, -limit_w, limit_w))`.

Check your work against §5's seven measured rows — especially `(0.0, 5.0, 1.0, 2.0, 0.5) → (0.0, 2.0)` and `(-0.5, 1.5, ...) → (-0.5, 1.0)`.

**Near-solution.** The lesson §5 block is the function; retype it rather than scroll back — the typing is where you notice the `min` and the `and`.

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

---

## 3. `step_unicycle` (requirement 2, lesson §6)

**Nudge.** Body frame: forward is along the *current* heading, so both `x` and `y` use `cos/sin` of the **old** `yaw`. The heading update is the only place a wrap is needed, and it is needed unconditionally.

**Direction.** Three statements, three returns: `x + v * cos(yaw) * dt`, `y + v * sin(yaw) * dt`, `wrap_angle_rad(yaw + w * dt)`. If one of your five rows fails on the last element only (something near `±3.03`), you forgot the wrap.

**Near-solution.** §6 has it; the only line people get wrong is comparing Euler vs exact — the assignment's rows are for *this* Euler body, not the exact-arc formulas in §6's accuracy discussion.

---

## 4. `yaw_to_quaternion` (requirement 2, lesson §8)

**Nudge.** One rotation axis (z), one angle (the whole `yaw`, halved), and ROS's field order is `x, y, z, w` — the identity is `(0, 0, 0, 1)`.

**Direction.** `half = yaw / 2.0`; return `(0.0, 0.0, sin(half), cos(half))`. The half-angle is the entire function; if your `π/2` row comes back `(0, 0, 0.479..., 0.877...)`, you skipped the `/2`.

**Near-solution.**

```python
def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    """Return the (x, y, z, w) quaternion for a planar yaw about z."""
    half = yaw / 2.0
    return (0.0, 0.0, math.sin(half), math.cos(half))
```

Your test row for `π/2` must use `pytest.approx` — measured, the two halves come back one ulp apart (`...5475` vs `...5476`), and bare `==` fails.

---

## 5. `expand_covariance_diagonal` (requirement 2, lesson §9)

**Nudge.** The message wants 36 floats in row-major order: element `(i, j)` lives at `i * 6 + j`. Only the diagonal of the 6×6 is ours to fill; everything else stays `0.0`. Length is a contract, not a hope — a wrong-length input must raise, because the alternative is a silently wrong covariance.

**Direction.** Validate `len(diagonal) == 6` first and raise `ValueError('diagonal must have length 6')`; build `[0.0] * 36`; loop `enumerate(diagonal)` writing `cov[i * 6 + i] = float(value)`; return it. Non-zero indices must come out as `[0, 7, 14, 21, 28, 35]`.

**Near-solution.**

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

---

## 6. The 16 test cases and the count (requirement 3, lesson §10)

**Nudge.** §10's table *is* the specification — inputs and expected values are already decided there; your job is transcription into three `parametrize` blocks (`limit_twist` 7 rows, `step_unicycle` 5, `yaw_to_quaternion` 2) plus two single-case functions for `expand_covariance_diagonal` — one asserting the 36-length/index layout, one the `raises` behaviour. Fast loop while working, from inside `ros2_ws/src/mower_math/`:

```bash
python3 -m pytest test/test_add_kinematics.py -q      # expect 16 passed
python3 -m pytest test/test_add_kinematics.py -k limit_twist -v
```

**Direction.**

- Count arithmetic: 13 baseline + 1 wrap row + 16 = 30. `29` = a dropped row (diff your table against §10); `31` = an extra row (fine only as stretch, and say so).
- `approx` for every trig-derived expectation (`step_unicycle` rows, both quaternion rows); plain `==` is correct for `limit_twist` and for the covariance indices.
- `raises` for the wrong-length row: `with pytest.raises(ValueError):` — add `match='diagonal must have length 6'` if you want it tight (the toy's §12 version shows `match` in use).
- Import order: `from math import pi as math_pi`, blank line, `from mower_math.add_kinematics import (...)`, blank line, `import pytest`? — no: `pytest` is third-party like the project import, and flake8's google style will tell you exactly what it wants if you get it wrong (`I100`, measured in §11). Run it and read the message rather than guessing.
- Pytest IDs for tuple expectations read `expected0`, `expected1`, … — that is normal (measured), not a bug in your rows.

**Near-solution — structure only, one sample row.** The remaining 15 rows come from §10's table; you transcribe them:

```python
@pytest.mark.parametrize(
    'v, w, max_linear, max_angular, min_radius, expected',
    [
        (0.3, 0.4, 1.0, 2.0, 0.5, (0.3, 0.4)),
        # ... rows 2..7 from the §10 table ...
    ],
)
def test_limit_twist(v, w, max_linear, max_angular, min_radius, expected):
    assert limit_twist(v, w, max_linear, max_angular, min_radius) == expected
```

Same pattern for `step_unicycle` (7 params, `== pytest.approx(expected)`) and `yaw_to_quaternion` (2 params, `approx`), then two plain functions: one asserting length-36/indices-`0,7,14,21,28,35`/zeros elsewhere, one wrapped in `pytest.raises(ValueError)`.

---

## 7. Linters, style, and the leftovers (requirements 1–4, lesson §11)

**Nudge.** `colcon test` fails names the file and the rule: `I100`/`I201` = import groups (stdlib block, blank line, third-party block; `pytest` and `mower_math` are both third-party from flake8's view), `E501` = line too long, `Q000` = double quotes. The measured `I201` in your tree's leftover `add_kinematics.py` is `import math` and the `from mower_math...` import sharing a group — the blank line between them is the whole fix.

**Direction.**

- Line target is **79** (PEP 8, this project's files); the linter only bites at **99**, and long comments slip past it entirely (measured) — so a green flake8 does not mean on-style.
- Docstrings and type hints are **not** linted (the `ament` convention ignores D100–D107, measured) — they are review requirements. Every public function gets both.
- Keep `test_copyright.py` decorator-free (it ships with a `skip` in fresh scaffolds; `mower_math`'s was cleaned in lesson 03) or your summary line stops saying `0 skipped`.
- Overwrite both leftover files; do not keep the existing `add_kinematics.py` content as-is (it fails `I201` today), and the empty `test_add_kinematics.py` must end up with your 16 cases.

**Near-solution.** Import block pattern for the new test file, in the order flake8's google style expects:

```python
from math import pi as math_pi

from mower_math.add_kinematics import (
    expand_covariance_diagonal,
    limit_twist,
    step_unicycle,
    yaw_to_quaternion,
)
import pytest
```

(If flake8 disagrees with this snippet on your machine, believe the linter — it names the rule and the expected order in its message.)

---

## 8. The acceptance battery fails (lesson §13)

**Nudge.** Read which line died. The sanity script is ordered: convention → clamp → integrator → quaternion → covariance. A failure at `wrap(-pi) must be +pi` means the guard is missing or guards the input; a failure at the `yaw` assertion (`-3.033...`) means `step_unicycle` forgot to wrap; a failure at the quaternion assertions means field order or the half-angle; `expected ValueError` means the length check is absent or returns instead of raising.

**Direction.** Run the pieces instead of the whole:

```bash
cd ~/mower-sim/ros2_ws/src/mower_math
python3 -m pytest test/test_math_utils.py test/test_add_kinematics.py -v
```

`-v` shows every case ID, so the failing row tells you which measured expectation you missed — compare that row against §5/§6/§8/§9's tables, which are the same numbers the sanity script uses.

**Near-solution.** If `colcon test-result` shows a failure in one of the five *lint* tests, run just that linter and read its message verbatim:

```bash
python3 -m pytest test/test_flake8.py -q     # or test_pep257 / test_mypy / ...
```

These messages are complete sentences (`I100 Import statements are in the wrong order. 'pytest' should be before ...`) — after the first one, you will not need this hint again.
