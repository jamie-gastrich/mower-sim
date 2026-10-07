# Review 05 — Lesson 05: Kinematics pure functions (Phase A of M1)

Reviewed against `docs/lessons/05-kinematics-pure-functions.md` §13 (requirements/interfaces/acceptance), `docs/lessons/05-kinematics-pure-functions-hints.md`, `docs/decisions/05-kinematics-and-m1-sim-interfaces.md`, and prior reviews. Verified on the host environment (ROS 2 Lyrical at `/opt/ros/lyrical`).

**Environment:** host Linux, ROS 2 sourced from `/opt/ros/lyrical/setup.bash`, Docker 29.8.1 (images `ros:lyrical-ros-base` and `mower-sim:m0` present). Used dedicated `ROS_DOMAIN_ID=45` for all runs. No ROS nodes/daemons left running after tests; scratch temp cleaned.

## Verdict
**pass with nits** (initial review; nits cleared on re-verification — see the final verdict at the bottom)

The acceptance battery from §13 runs verbatim and all checks pass (30 tests, 0 errors, 0 failures, 0 skipped; purity and the sanity script all green). Phase A also passes inside the Docker image with the current codebase. The nits below are alignment/discipline items against the lesson's stated requirements; none are blockers. M1 is **not** complete (Phase A only), so the README milestone table must not be changed.

## Skills applied
- `ros2` (workspace/build/test flow, conventions, no ROS imports in pure logic)
- `python-style` (formatting/import order considerations, type hints)

## Acceptance criteria (§13) — evidence
```bash
cd ~/mower-sim/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install --packages-select mower_math  # finished [1.86s], exit 0
colcon test --packages-select mower_math  # finished [11.6s], exit 0
colcon test-result --verbose --test-result-base build/mower_math  # Summary: 30 tests, 0 errors, 0 failures, 0 skipped
```
- [x] `Summary: 30 tests, 0 errors, 0 failures, 0 skipped` (verified)
- [x] `grep -o '<testcase' build/mower_math/pytest.xml | wc -l` → `30` (30 distinct cases)
- [x] Sanity script (§13): prints `all sanity checks passed`, exit 0 (covering wrap convention, `limit_twist` subcases, `step_unicycle`, `yaw_to_quaternion`, `expand_covariance_diagonal` behavior)
- [x] `grep -rn "import rclpy\|import rclcpp" src/mower_math` → no output (exit 1)
- [x] `grep -n "(-π, π\]" src/mower_math/mower_math/math_utils.py` → `24:    """Wrap an angle in radians to the range (-π, π]."""` (exit 0)
- [x] `grep -rn "TODO\|FIXME" src/mower_math` → no output (exit 1)
- [x] `cd src/mower_math && python3 -m pytest test/test_add_kinematics.py -q` → `16 passed`
- [x] `python3 -m pytest test/test_math_utils.py -q` → `9 passed`
- [x] Zero skips: `test_copyright.py` exists and has no `@pytest.mark.skip` decorator; `grep -rn "pytest.mark.skip" src/mower_math` → no output

**In-container (Phase A exercised in Docker):**
```bash
docker build -t mower-sim:rev05 -f docker/Dockerfile .  # successful
docker run --rm -t mower-sim:rev05  # builds+tests both packages
# → Summary: 2 packages finished [16.8s]
#    mower_math: 30 tests, 0 errors, 0 failures, 0 skipped
#    mower_status: 7 tests, 0 errors, 0 failures, 0 skipped
# exit 0
```
This satisfies §14's note to try running Phase A tests inside the lesson-04 Docker image (done; passes).

## Requirement-by-requirement

**Req 1 (wrap_angle_rad convention `(-π, π]`, guard, boundary row):**
- Docstring updated to `(-π, π]`. Guard added: maps `res == -math.pi` to `+math.pi` (measured correct with the new implementation). `test_math_utils.py` now includes `-3.1415926535` in the parametrized list and the range assertion remains `-math_pi < res <= math_pi`. The sanity script explicitly asserts `wrap_angle_rad(-pi) == pi` and `wrap_angle_rad(pi) == pi`.

**Req 2 (four functions, reuse, purity):**
- `add_kinematics.py` provides `limit_twist`, `step_unicycle`, `yaw_to_quaternion`, `expand_covariance_diagonal`. Reuses `clamp` and `wrap_angle_rad` from `mower_math.math_utils`. No `rclpy`, `rclcpp`, `geometry_msgs`, `os`, or `sys` imports. Module importable in bare Python.
- Signatures/return types match §13 interfaces table; argument names are exactly as specified: `limit_twist(v, w, max_linear, max_angular, min_radius)`, `step_unicycle(x, y, yaw, v, w, dt)`, `yaw_to_quaternion(yaw)`, `expand_covariance_diagonal(diagonal)`.
- `limit_twist` implements the radius rule with in-place-spin exemption (`v_clamped != 0.0`) and `min_radius > 0.0` guard; clamps `v` first, derives `limit_w = min(max_angular, abs(v_clamped)/min_radius)` when applicable, returns `(v_clamped, clamp(w, -limit_w, limit_w))`. Matches the measured table in §5.

**Req 3 (16 cases, parametrized, approx, raises):**
- `test_add_kinematics.py` contains 16 cases across three `parametrize` blocks (7 `limit_twist`, 5 `step_unicycle`, 2 `yaw_to_quaternion`) plus two plain tests (full 36-element structure for a 6-dim diagonal; `ValueError` on wrong length). Inputs/expected values match §10 exactly. `pytest.raises(ValueError)` is used for the rejection case.
- Note (nit 1 below): the trig-derived rows use exact `==` rather than `pytest.approx` as specified in the lesson.

**Req 4 (style):**
- Public functions have docstrings and type hints. `expand_covariance_diagonal` is missing a parameter type hint (`diagonal`) while having a return hint (nit 2). Lines appear ≤ 79 except one line in the test (nit 3). Imports use single quotes where strings appear; import groups separated by blank line in `add_kinematics.py`. `test_copyright` remains enabled (no skip).

## Top issues (ranked)

1. **should-fix (non-blocking) — trig-derived test expectations not compared with `pytest.approx`** (`test_add_kinematics.py` lines ~43-66). The lesson states both quaternion rows and the arc-derived `step_unicycle` row "must be compared with `pytest.approx`" (§8, §10). The committed tests do bare `==` for those rows (verified: `grep -c "approx"` in the committed test is `0`). In this environment values happen to match bitwise, but the requirement is to follow the specified comparison strategy. Fix: import/use `pytest.approx` for `step_unicycle` (the last row) and both `yaw_to_quaternion` rows.
   - Impact: correctness/robustness across platforms/float paths; matches the lesson's explicit instruction and the example in §8.

2. **should-fix (non-blocking) — boundary row uses numeric literal instead of `-math_pi` token** (`test_math_utils.py:33`). Requirement 1 states "add `-math_pi` to the parametrized row list in `test_math_utils.py`". The committed row list includes `-3.1415926535` rather than `-math_pi`. The experiment in scratch shows `-3.1415926535` is a weaker pin (passes the range rows even if the guard is removed in isolation), whereas feeding `-math_pi` directly exposes the `(-π,π]` vs `[-π,π)` distinction with the guard-less implementation. The implementation's guard+docstring are correct; the test row could be strengthened to match the stated requirement.
   - Impact: test fidelity to the stated requirement (doesn't block verification, but the explicit instruction isn't met).

3. **consider (non-blocking) — missing parameter type hint in `expand_covariance_diagonal`** (`add_kinematics.py:47`): `def expand_covariance_diagonal(diagonal) -> list[float]:` lacks `diagonal: list[float]`. Req 4 says "every public function has a full type hint..." — treat as a small style consistency nit.
   - Impact: minor type completeness; linters/mypy in this setup are not strict, but the project convention calls for full hints.

4. **consider (non-blocking) — line > 79 chars in test** (`test/test_math_utils.py:33`, 88 chars). The lesson sets a 79-char target (PEP 8) and the review enforces project style; the installed linter's limit is higher but the project target is 79. Trivial wrap.
   - Impact: style consistency.

5. **consider (non-blocking) — extra file in commit 57afd47**: the commit also includes `.opencode/agents/professor.md` (18 lines). The Phase A scope is four files in `mower_math`. Including agent config in the same commit is not necessary and muddies the "one concept, one commit" traceability for this milestone slice. Not a blocker; just commit hygiene.
   - Impact: clarity of history.

6. **consider (non-blocking) — commit message hygiene (5ce1cb2)**: "Implement code changes to enhance functionality and improve performance" is generic and doesn't follow the AGENTS.md convention ("Small and frequent, one concept per commit. Commit messages say what changed and which milestone it belongs to..."). Already pushed; keep subsequent messages clean.

7. **consider (non-blocking) — untracked draft docs**: `docs/lessons/TEMP-m1-full-draft.md` and `TEMP-m1-full-draft-hints.md` are untracked. These appear to be professor draft material (not owner code). The rules say do not delete them yourself; they should not be committed as part of this review. Recommendation: leave untracked (or move to scratch) and do not commit them.
   - Impact: repo cleanliness.

## What is solid
- The acceptance battery passes exactly as specified on host and in-container; 30/0/0/0 count is independently verified.
- `(-π, π]` convention is correctly implemented with a guard and the sanity script asserts the boundary (`wrap(-pi)==pi`).
- Purity: no ROS imports; pure functions isolated in `add_kinematics.py` reusing `math_utils`.
- All four functions and their interfaces match §13 and decision 05; tests cover the measured tables precisely.
- Scope discipline: only the four Phase A files were modified under `ros2_ws/src/mower_math` (plus the extra `.opencode` file noted above); no changes to `mower_sim`, `docker/`, `README.md`, or `log/`.
- Docker entrypoint is wired in the current Dockerfile and Phase A passes in a fresh container build.

## Revisit list (for professor)
- Clarify whether the boundary row in the test must be `-math_pi` (token) vs a decimal literal; the text says "add `-math_pi` to the parametrized row list" but the committed decimal passes the current guard. The guard is the key behavioral fix; row tokenization is a small instruction detail.
- Explicitly call out `pytest.approx` for trig rows in the assignment text's example if strict adherence is expected (current code meets behavioral intent but not the letter).

## End-product check
Phase A correctly pins the heading convention and provides the four pure kinematic/covariance helpers that M1's `sim_node` (Phase B) will call. The functions are small, testable, and protocol-agnostic (no ROS types), which matches the separation-of-logic rule and keeps interfaces stable for Gazebo replacement at M8. The main risks introduced are minor test precision/style details (nits 1-3); no interface drift or semantic model errors are evident. M1 remains incomplete (B–D pending), so README milestone state must not be changed.

**Verdict:** pass with nits (see 7 issues above; none blocking).

---

## Re-verification (working tree, after owner fixes)

Re-run on the uncommitted working tree (host, `ROS_DOMAIN_ID=45`):

```bash
colcon build --symlink-install --packages-select mower_math   # exit 0
colcon test --packages-select mower_math                      # exit 0
colcon test-result --verbose --test-result-base build/mower_math
# → Summary: 30 tests, 0 errors, 0 failures, 0 skipped
grep -o '<testcase' build/mower_math/pytest.xml | wc -l       # → 30
cd ros2_ws/src/mower_math && python3 -m pytest test/ -q       # → 30 passed
# §13 sanity script → all sanity checks passed (exit 0)
awk 'length > 79 {print FILENAME":"FNR}' mower_math/*.py test/*.py   # → no output
python3 -m pytest test/test_flake8.py test/test_pep257.py \
        test/test_mypy.py test/test_copyright.py -q           # → 4 passed
grep -rn "import rclpy\|import rclcpp" .  # → no output
grep -rn "TODO\|FIXME" .                  # → no output
```

Nit status against the diff (`git diff` = 3 files, 4 lines changed):

| # | nit | status |
|---|---|---|
| 1 | `pytest.approx` on trig-derived rows | **fixed** — `test_add_kinematics.py:54` (arc row, `-3.0331853071795867`) and `:65` (both quaternion rows) now compare with `pytest.approx`, matching §10's "the two quaternion rows **and the arc row**". Verified the comparison still rejects a wrong expectation (`approx((0.0, 0.0, -3.0331853071795867)) == (0.0, 0.0, -3.04)` is `False`), so the tolerance has not become a rubber stamp. |
| 2 | `-math_pi` token row | **fixed** — `test_math_utils.py:33` is now `[... math_pi, -math_pi]`, the literal requirement of requirement 1. |
| 3 | missing `diagonal` type hint | **fixed** — `def expand_covariance_diagonal(diagonal: list[float]) -> list[float]:`. |
| 4 | line > 79 chars | **fixed** — no file in `mower_math` exceeds 79. |
| 5 | `.opencode/agents/professor.md` in `57afd47` | not actionable here (already committed); keep agent config out of future milestone commits. |
| 6 | generic message on `5ce1cb2` | not actionable here (already committed); applies to the commit being prepared. |
| 7 | untracked `TEMP-m1-full-draft*.md` | still untracked — correct; do not stage them. |

Tests, lint, purity greps, and the sanity script are all green on the fixed tree. All four actionable nits (1–4) are now fixed; 5–6 are history, 7 is handled by leaving the drafts untracked.

**Final verdict: pass.** Nits cleared in the working tree, evidence above. M1 Phase A only — Phases B–D remain, so the README milestone table still must not be flipped.