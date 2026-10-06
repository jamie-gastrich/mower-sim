# 03 - Making `colcon test` mean something

**Milestone:** M0 · **Language:** Python · **Prerequisite:** lesson 01 (its §15 purity split and §16 linters)

**Concepts this assignment requires** — each line links to the section that teaches it:

- [What `colcon test` actually runs for a Python package](#4-what-colcon-test-runs-for-a-python-package)
- [Reading a test result](#5-reading-a-test-result)
- [pytest: assert, parametrize, and running a subset](#6-pytest-basics)
- [The pure function is the unit you test](#7-the-pure-function-is-the-unit-you-test)
- [Turning review 01's fix into pure, tested code](#8-turning-review-01s-fix-into-pure-tested-code)
- [`mower_math` gets its first real code](#9-mower_math-gets-its-first-real-code)

---

## 1. Where this fits

Lesson 01's five tests were the scaffold linters. They check *style* — import order, newlines, typing, XML, licence headers — and none of them checks that `status_node` behaves. That is fine for lesson 01 and completely inadequate for the project: M2's done-when is a *measured* pose error, which no linter can express.

Decision record [`03-testing-pytest-and-gtest.md`](../decisions/03-testing-pytest-and-gtest.md) sets the rule: Python logic is tested with **pytest** against the pure functions, run through the same `colcon test` you already know. This lesson makes the rule real in the two places it first applies:

1. `mower_status` — the pure function from §15 (`status_format.py`) gets real unit tests, and the one weakly-designed part the reviewer flagged (the duplicated `2.0` fallback in `status_node.py`) is refactored into *pure, testable* code.
2. `mower_math` — the shared pure-logic package that decision record 01 reserved ("no `rclpy`/`rclcpp` import") gets its first two genuinely-used functions and its own tests. Until now it has been a bare scaffold with a skipping copyright test; lesson 01 said "lesson 03 fills it in." This is that lesson.

## 2. Verification table

Everything in this lesson was run on this machine before being written down. The scratch package was `xp_math`, a toy `ament_python` package in `/tmp/opencode/l03`, built and deleted afterwards. No node was started; unit tests need no ROS graph, no daemon, and no `ROS_DOMAIN_ID`.

| Claim | How it was checked | Result |
|---|---|---|
| A fresh `ament_python` package can gain a pure-function module and a pytest test file and be tested by `colcon test` | scaffolded `xp_math`, added `math_utils.py` + `test/test_math_utils.py`, `colcon build --symlink-install`, `colcon test` | `Finished <<< xp_math ... [ with test failures ]` when a test fails; otherwise `Summary: 1 package finished` |
| `colcon test-result` counts unit tests and linters together | `colcon test-result --test-result-base build/xp_math` | `Summary: 9 tests, 0 errors, 0 failures, 1 skipped` — five scaffold linters (four running + `test_copyright` skipped) plus four unit test cases |
| A parametrized pytest case shows up as one test per case, with an ID built from its arguments | failure message in `colcon test-result --verbose` | `- xp_math.test.test_math_utils test_clamp[5.0-0.0-3.0-7.0]` |
| A failing assertion shows *which* call produced the value | same failure message | `assert 3.0 == 7.0` / `+ where 3.0 = clamp(5.0, 0.0, 3.0)` |
| pytest discovers every `test_*.py` in `test/` and runs it from the source tree with the workspace sourced | `python3 -m pytest test/test_math_utils.py -k clamp -v` inside the package | `collected 4 items / 1 deselected / 3 selected`, `3 passed` in `0.06s` |
| Unit tests run with no ROS layer involved | same run, no node started | `platform linux -- Python 3.14.4, pytest-9.0.2 ... 3 passed in 0.06s` — no daemon, no topic |
| Running pytest directly leaves a `.pytest_cache/` in the package directory | `ls` after the direct run | `.pytest_cache/` present — do not commit it |
| `test_copyright` in a fresh package is skipped until a header exists | `colcon test-result` on the scaffold before adding headers | the only skip is `xp_math.test.test_copyright` |

Not yet verified: nothing in this lesson depends on Docker or CI; the "runs in CI-style" half of M0 is the Docker lesson (04). GTest is *not* exercised here — the first C++ node is M2 per decision record 02; the CMake/GTest wiring is taught when that node is designed.

## 3. Options survey: how should we test the logic?

The survey happened in decision record [`03-testing-pytest-and-gtest.md`](../decisions/03-testing-pytest-and-gtest.md):

| Option | Proves behaviour | Runs without a graph | Cost |
|---|---|---|---|
| **pytest unit tests on pure functions** | yes, per function | yes, ~0.06 s | one test file per module |
| Node-level tests (launch node, echo topic, assert) | yes, end to end | no | graph setup per run, brittle in CI |
| Lint-only | no | n/a | nothing new, proves nothing |

**Chosen: pytest for Python logic, GTest for the C++ packages arriving at M2**, both driven by `colcon test`, `test_copyright` enabled everywhere, zero skips required before a review passes.

## 4. What `colcon test` runs for a Python package

For an `ament_python` package, `colcon test` is two arrows into the same target:

- **pytest** runs over everything named `test_*.py` in the package's `test/` directory. The five scaffold files are pytest tests too — that is why `test_flake8`, `test_mypy`, `test_pep257`, `test_xmllint`, and `test_copyright` show up in the results alongside anything you write.
- So "write a unit test" and "run the linters" are the **same command**. You do not get a separate verification step for style and behaviour; both are part of M0's "tests pass".

Two habits from lesson 01 carry over unchanged:

```bash
cd ~/mower-sim/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
colcon test --packages-select mower_math mower_status
colcon test-result --verbose --test-result-base build/mower_math
```

Scope the *result* reading to one package (`--test-result-base build/<package>`) the way lesson 01 scoped it, so `mower_math`'s results never hide `mower_status`'s failures or vice versa.

## 5. Reading a test result

A green scoped run looks like:

```
Summary: 4 tests, 0 errors, 0 failures, 0 skipped
```

A red one changes two signals at once. In the worked example I deliberately broke one parametrized case; `colcon test` ended with:

```
Finished <<< xp_math [12.9s]   [ with test failures ]

Summary: 1 package finished [13.1s]
  1 package had test failures: xp_math
```

and `colcon test-result --verbose` named the exact test and the exact mismatch:

```
build/xp_math/pytest.xml: 9 tests, 0 errors, 1 failure, 1 skipped
- xp_math.test.test_math_utils test_clamp[5.0-0.0-3.0-7.0]
  <<< failure message
    assert 3.0 == 7.0
     +  where 3.0 = clamp(5.0, 0.0, 3.0)
  >>>
```

That failure message is the whole point of unit testing: it prints the function, the inputs, and the two values. Compare it with the next best alternative — running the node, echoing a topic, and squinting at `message: mower-01: nominal` to see if it is *slightly* wrong.

The test name carries its inputs in brackets: `test_clamp[5.0-0.0-3.0-7.0]` is the parametrized case with those four arguments. When a test fails, the bracket tells you which case to think about before you even open the file.

## 6. pytest basics

**`assert` is the assertion.** No `assertEqual`, no special object, just Python's `assert` with an expression:

```python
def test_clamp_high(high: float) -> None:
    assert clamp(5.0, 0.0, 3.0) == 3.0
```

**`parametrize` turns one function into many cases**, one test per argument tuple, each independently reportable:

```python
@pytest.mark.parametrize('value, low, high, expected', [
    (5.0, 0.0, 3.0, 3.0),
    (-1.0, 0.0, 3.0, 0.0),
    (2.0, 0.0, 3.0, 2.0),
])
def test_clamp(value: float, low: float, high: float, expected: float) -> None:
    assert clamp(value, low, high) == expected
```

Use parametrize for the *table* cases — the boundary values that teach you what "clamp at the top, clamp at the bottom, pass through in the middle" means. Three rows here turned into three tests in the result output.

**You can run a subset without a full loop.** From inside the package directory, with the workspace sourced:

```bash
python3 -m pytest test/test_math_utils.py -k clamp -v
```

```
collected 4 items / 1 deselected / 3 selected
test/test_math_utils.py::test_clamp[5.0-0.0-3.0-3.0] PASSED    [ 33%]
...
======================= 3 passed, 1 deselected in 0.06s ========================
```

`-k` filters by name; `.00`-style paths select a single test. This is your red/green loop when you are iterating on one function: run the one file, see it fail, fix it, see it pass, and only then run the full `colcon test`. One side effect to know about: a direct run drops a `.pytest_cache/` directory in the package — it is generated, never commit it.

Why `0.06s`? Because the test imports `from xp_math.math_utils import clamp` — a plain Python import of a plain module. That speed is what §7 is about.

## 7. The pure function is the unit you test

Lesson 01 §15 made one demand: keep logic out of the node class so it can be tested without a running graph. This lesson cashes that cheque. Compare two ways to test "the node's message field contains the robot id":

- *Through the node:* `rclpy.init()`, construct the node, `rclpy.spin` on a timer, subscribe, wait for a message, parse `hardware_id` from the serialized form, tear everything down. Every run pays graph setup.
- *Through the pure function:* 

```python
from mower_status.status_format import format_status_message

def test_format_status_message() -> None:
    assert format_status_message('mower-01', 'nominal') == 'mower-01: nominal'
```

The second needs nothing ROS: no daemon, no `ROS_DOMAIN_ID`, no executor — just an import and an assertion. That is the structure decision record 01 baked into the layout and lesson 01 §15 taught you to write. Unit tests are where it pays back, and the entire pytest machinery you just saw (`-k`, parametrize, the 0.06 s feedback loop) only works because the code under test is importable and side-effect-free.

The rule of thumb to keep: **the node class should contain no logic you want to read about later.** If it does, you cannot test it this cheaply, and it will end up tested through the graph or not at all.

## 8. Turning review 01's fix into pure, tested code

Review 01 flagged one real defect in the (passed) lesson-01 code. In `status_node.py`:

```python
self.declare_parameter('publish_rate', 2.0)
...
if self.rate <= 0.0:
    self.get_logger().warning('Publish rate must be positive, defaulting to 2.0 Hz')
    self.rate = 2.0
```

Two problems, both "magic numbers": the fallback `2.0` is written a second time, a literal twin of the declared default that a future maintainer must keep in sync; and the decision logic is inside the node, so §7 says it is untestable.

The fix is to make the decision *pure* and put it in `status_format.py` next to the other pure logic:

```python
DEFAULT_PUBLISH_RATE: float = 1.0

def validate_publish_rate(rate: float) -> float:
    return rate if rate > 0.0 else DEFAULT_PUBLISH_RATE
```

One constant, one function, no `rclpy`. The node then:

1. declares the parameter using *the same constant*, so the default and the fallback cannot drift:
   ```python
   self.declare_parameter('publish_rate', DEFAULT_PUBLISH_RATE)
   ```
2. reads the raw value, passes it through the pure function, and only logs when the function changed something:
   ```python
   raw_rate = float(self.get_parameter('publish_rate').value)
   self.rate = validate_publish_rate(raw_rate)
   if self.rate != raw_rate:
       self.get_logger().warning(
           f'publish_rate must be positive, falling back to {self.rate} Hz')
   ```

Now the fallback is testable as a decision, *and* it still names the parameter in the warning (`publish_rate`, the declared name, not the human "Publish rate"), which review 01 also asked for. This is the same shape that M4 will need for safety parameters — geofence distances and stop thresholds — where the decision is "fail closed, do not fall back", and where a tested pure decision is exactly what you want before a fleet goes out.

## 9. `mower_math` gets its first real code

Decision record 01 reserved `mower_math` as the shared pure-logic package: no ROS import, importable anywhere, unit-testable without a graph. It has sat empty since the scaffold. M1 and M3 genuinely need the two functions this lesson adds, so this is not busy-work:

- **`clamp(value, low, high)`** — caps a value into `[low, high]`. M3's tracker will clamp velocity and steering commands to kinematic limits.
- **`wrap_angle_rad(angle)`** — normalises an angle into `(-π, π]`. Heading math in M1's kinematics and M3's cross-track error will need it, and writing it correctly is exactly the border case a unit test should pin down.

Both live in `mower_math/mower_math/math_utils.py`, both fully and simply typed, both with **no ROS import** — the file must pass `grep -n rclpy ...` with no match, same as `status_format.py`. Their tests go in `mower_math/test/test_math_utils.py` with parametrize covering the boundary cases (clamp above/below/inside; angles just under π, just over -π, and a multi-turn value).

`mower_math` is still the untouched scaffold, so its `test_copyright` has the `@pytest.mark.skip(...)` intact and its files carry no header. This lesson expects two changes there, exactly the two lesson 01 §16 taught for `mower_status`: remove the skip, and put an Apache-2.0 header naming you (`Copyright 2026 Jamie`) on every source file you add. Note that the scaffold's own `test/` files keep the OSRF line — those are template files, not yours to re-license; only the code you write needs your header.

Then `colcon test-result` for `mower_math` should show the linters *and* your new tests, with **zero skipped** — the first package in the repo to reach that state fully.

---

## 10. Worked example: a toy math package

I built a throwaway `xp_math` package in `/tmp/opencode/l03` to verify everything above (it is deleted now). It is the same shape as your `mower_math` assignment but on a different subject:

```
xp_math/xp_math/math_utils.py      # pure functions: clamp, wrap_angle_rad
xp_math/test/test_math_utils.py    # pytest: 1 parametrized + 1 plain case
```

The test file began with:

```python
import pytest

from xp_math.math_utils import clamp, wrap_angle_rad


@pytest.mark.parametrize('value, low, high, expected', [
    (5.0, 0.0, 3.0, 3.0),
    (-1.0, 0.0, 3.0, 0.0),
    (2.0, 0.0, 3.0, 2.0),
])
def test_clamp(value: float, low: float, high: float, expected: float) -> None:
    assert clamp(value, low, high) == expected


def test_wrap_angle_rad_keeps_range() -> None:
    angle = wrap_angle_rad(3.0 * 3.14)
    assert -3.141593 <= angle <= 3.141593
```

`colcon build --symlink-install` then `colcon test`:

```
Summary: 9 tests, 0 errors, 0 failures, 1 skipped
```

Nine = five scaffold linters (with `test_copyright` the sole skip) + the three parametrized cases + one plain test. Then I broke the first row's expected value to see the failure format in §5, fixed it, and re-ran:

```
collected 4 items / 1 deselected / 3 selected
... 3 passed, 1 deselected in 0.06s
```

That red→green cycle *is* the workflow this lesson wants you inside. Write a case that describes the behaviour, watch it fail for the right reason, make it pass with the smallest real change, and let `colcon test` be the thing that certifies the whole package.

---

## 11. Assignment: unit tests, and the first code in `mower_math`

**Language: Python.** Two packages change: `mower_status` and `mower_math`. Do not touch the node code's ROS behaviour — `status_node` must still do everything lesson 01 certified.

### Requirements

**`mower_math` — its first real functionality**

1. `mower_math/mower_math/math_utils.py` with two pure functions: `clamp(value: float, low: float, high: float) -> float` and `wrap_angle_rad(angle: float) -> float` ([§9](#9-mower_math-gets-its-first-real-code)). Typed, documented, logic-only — the file must contain no ROS import.
2. `mower_math/test/test_math_utils.py` with pytest unit tests: parametrized cases for `clamp` covering above, below, and inside the range, and for `wrap_angle_rad` covering the two range edges and one multi-turn angle ([§6](#6-pytest-basics), [§9](#9-mower_math-gets-its-first-real-code)).
3. Enable `test_copyright`: remove the `@pytest.mark.skip(...)` line in `mower_math/test/test_copyright.py` and put an Apache-2.0 header naming **you** on every source file you add ([§9](#9-mower_math-gets-its-first-real-code), lesson 01 §16).
4. Scoped test result for `mower_math` shows all tests passing with **zero skipped** ([§4](#4-what-colcon-test-runs-for-a-python-package)).

**`mower_status` — real tests and a cleaner validation**

5. Move the `publish_rate` validation into pure code: add `DEFAULT_PUBLISH_RATE: float` and `validate_publish_rate(rate: float) -> float` to `mower_status/mower_status/status_format.py` ([§8](#8-turning-review-01s-fix-into-pure-tested-code)). `status_format.py` must still contain no `rclpy`.
6. Refactor `status_node.py` to use them: declare the parameter with the constant, run the raw value through `validate_publish_rate`, and log a warning that names the actual parameter `publish_rate` only when the value had to be replaced ([§8](#8-turning-review-01s-fix-into-pure-tested-code)). Behaviour from lesson 01's acceptance criteria must not change: `publish_rate:=0.0` still warns and still runs at the safe default, and **no second literal copies the default anywhere**.
7. `mower_status/test/test_status_format.py` with pytest unit tests for both pure functions: `format_status_message` (the `robot_id: state` composition from §15) and `validate_publish_rate` (positive passes through unchanged, zero and negative fall back to `DEFAULT_PUBLISH_RATE`) ([§7](#7-the-pure-function-is-the-unit-you-test), [§8](#8-turning-review-01s-fix-into-pure-tested-code)).
8. Purity, twice: `grep -n rclpy` over `mower_status/mower_status/status_format.py` **and** `mower_math/mower_math/math_utils.py` prints nothing ([§9](#9-mower_math-gets-its-first-real-code)).

### Acceptance criteria

Each of these is a command. All must pass.

```bash
cd ~/mower-sim/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
colcon test --packages-select mower_math mower_status
colcon test-result --verbose --test-result-base build/mower_math
colcon test-result --verbose --test-result-base build/mower_status
```

- [ ] `mower_math`: the summary shows **zero failures and zero skipped**, and the linters plus your unit tests all appear in the verbose listing.
- [ ] `mower_status`: the summary shows **zero failures and zero skipped** (it already ran 5/0/0/0; now it runs those **plus** your new test file).
- [ ] No `TODO` anywhere in the two packages.

```bash
grep -n rclpy ~/mower-sim/ros2_ws/src/mower_status/mower_status/status_format.py
grep -n rclpy ~/mower-sim/ros2_ws/src/mower_math/mower_math/math_utils.py
```

- [ ] Both print nothing.

Bad-parameter re-check, to prove the refactor kept the behaviour (node stopped first):

```bash
source install/setup.bash
ros2 run mower_status status_node --ros-args -p publish_rate:=0.0
```

- [ ] Within a second a warning names `publish_rate` (for example `publish_rate must be positive, falling back to 1.0 Hz`) and the node keeps running; `grep -c ZeroDivisionError` prints `0`. The safe default is whatever `DEFAULT_PUBLISH_RATE` is — check the running node with `ros2 param get /status_node publish_rate` and the startup log agree.

Optional (no credit, but practice): iterate on `wrap_angle_rad` with the direct loop — `python3 -m pytest test/test_math_utils.py -k wrap -v` from inside `mower_math/` ([§6](#6-pytest-basics)).

## 12. Where this leaves M0

After this lesson and a passing review: `colcon test` asserts real behaviour, `mower_status`'s one brittle line is pure and covered, and `mower_math` — the shared-logic home decision 01 promised — finally holds code and tests that the sim, tracker, and EKF will import. Lesson 04 puts the whole thing in a container, which is where M0's done-when ("clean build in a fresh container, tests pass") is actually decided.

## 13. Commit

Two commits, one concept each:

```
M0: add unit tests and make publish_rate validation pure (mower_status)

M0: fill mower_math with clamp and wrap_angle_rad plus tests
```

The lesson and this commit are separate: the lesson (and the hints file) land in a docs commit, the two package changes in code commits.