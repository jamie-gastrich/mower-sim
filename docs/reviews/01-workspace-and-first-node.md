# Review 01 — workspace and first node (`mower_status`)

**Milestone:** M0 · **Scope:** `ros2_ws/src/mower_status/` (post-`6e56e16` working tree, fixes not yet committed at review time) · **Reviewer:** Reviewer agent
**Yardsticks:** `docs/lessons/01-workspace-and-first-node.md` §18 + hints, `docs/decisions/01-package-layout.md`, `docs/decisions/01-status-message-type.md`
**Build environment:** native, no Docker. Docker is lesson 04, so M0's "clean build in a fresh container" criterion is still **not testable**; everything below was run natively. ROS 2 Lyrical.
**Skills applied:** `ros2`, `python-style`.

**Supersedes** the earlier "not yet" review of this lesson. Its two blockers are gone: requirement 10 now runs (`test_copyright` enabled, verified), and the §18 naming contradiction was reconciled in a dedicated lesson commit that normalized everything to `status_node` (requirement 4, 7, interfaces table, acceptance criteria, and hints Tier 1/Tier 3 all agree now).

Commands used (every run in a fresh `env -i` shell so `AMENT_PREFIX_PATH` carried nothing from the robotics-factory workspace; runtime checks on dedicated `ROS_DOMAIN_ID` 82/83):

```
cd ros2_ws && source /opt/ros/lyrical/setup.bash && colcon build --symlink-install   # Summary: 2 packages finished [2.41s]
colcon test --packages-select mower_status                                           # exit 0
colcon test-result --verbose --test-result-base build/mower_status                   # 5 tests, 0 errors, 0 failures, 0 skipped
colcon test-result                                                                   # 10 tests, 0 failures, 1 skipped (mower_math, out of scope)
```

All nodes/daemons I started were stopped and waited on; `ros2-daemon` processes killed for domains 82/83; no `status_node` left behind.

---

## Verdict: **pass**

The two blockers from the first review are cleared, the code meets every acceptance criterion I can build and run, and the lesson is now internally consistent. Verdict attaches to the working tree as reviewed; the fixes were not yet committed, so the milestone stays **in progress** until commit 02 (C++ node) and 04 (Docker) land, per the reviewer rules.

---

## Acceptance criteria (§18), each run or observed by me

### Requirements 1–11

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | Scaffolded `ament_python` package, real description/maintainer, Apache-2.0, no `TODO` | **PASS** | `setup.py`/`package.xml` intact scaffolds; `setup.py:19` description "Reports the status of the mower"; `grep -rn TODO ros2_ws/src/mower_status/` → rc 1 (none). |
| 2 | `<depend>rclpy</depend>` + `<depend>diagnostic_msgs</depend>` | **PASS** | `package.xml:10-11`. |
| 3 | One `console_scripts` executable named `status_node` | **PASS** | `setup.py:28`; `ros2 pkg executables mower_status` → `mower_status status_node`. |
| 4 | Node name `status_node`, matching the executable | **PASS** | `status_node.py:27` `super().__init__('status_node')`; `ros2 node list` → `/status_node`. |
| 5 | Three core parameters declared; `state` allowed as stretch | **PASS** | `ros2 param list /status_node` → `base_frame`, `publish_rate`, `robot_id`, `state` (+ `use_sim_time`, `start_type_description_service`). All values read back via `get_parameter`; no magic numbers in the message path. |
| 6 | `DiagnosticStatus` on `~/diagnostics`, QoS depth 1, timer at `publish_rate` | **PASS** | `status_node.py:40-41`; `ros2 topic list` → `/status_node/diagnostics` only (plus the two free topics). |
| 7 | `level` named constant; `name`; `hardware_id`; `message`; ≥2 `values` incl. `base_frame` + runtime value | **PASS** | `status_node.py:44-57`. Measured `ros2 topic echo --once`: `level: "\0"`, `name: status_node`, `hardware_id: mower-01`, `message: 'mower-01: nominal'`, `values: publish_count` (changes across runs: 10, 16) + `base_frame`. |
| 8 | Pure function, own module, no `rclpy` | **PASS** | `grep -n rclpy .../status_format.py` → rc 1, no output. `format_status_message(robot_id, state)` — no `self`, no ROS. Called at `status_node.py:53`. |
| 9 | §14 shutdown pattern; logger, no `print()` | **PASS** | `status_node.py:60-69` matches §14 exactly. SIGINT: 2 runs, both exit 0 with `[ros2run]: Received signal:  Interrupt` and no traceback. |
| 10 | Apache header naming **you**; `test_copyright` enabled | **PASS** | `status_node.py:1` and `status_format.py:1` read `Copyright 2026 Jamie`; `test_copyright.py:20` has the skip commented out, so the check runs — proven by the green 5-test run. |
| 11 | `publish_rate <= 0` handled cleanly, no `ZeroDivisionError` | **PASS** | With `-p publish_rate:=0.0`: `[WARN] ... Publish rate must be positive, defaulting to 2.0 Hz`, node keeps running (`ros2 node list` → `/status_node` 2 s in), `grep -c ZeroDivisionError` → `0`. |

### Acceptance-criteria checklist

- [x] `colcon build --symlink-install` → `Summary: 2 packages finished [2.41s]`, exit 0 (native, no container).
- [x] No `TODO` in `ros2_ws/src/mower_status/` → grep rc 1.
- [x] Scoped test result: `5 tests, 0 errors, 0 failures, 0 skipped` (workspace-wide `1 skipped` is `mower_math`'s `test_copyright`, explicitly out of scope until lesson 03).
- [x] `ros2 pkg executables mower_status` → `mower_status status_node`.
- [x] One startup line naming robot id and rate, node stays running → `[INFO] [1791308478.605670543] [status_node]: status_node up at 2.0 Hz for mower-01`.
- [x] Ctrl-C → `[ros2run]: Received signal:  Interrupt`, no traceback → 2/2 trials, exit 0.
- [x] `ros2 param list /status_node` → the three core parameters plus `state` (stretch).
- [x] `ros2 topic echo --once /status_node/diagnostics` → `level: "\0"`, `name: status_node`, `hardware_id`, non-empty `message`, two `values`.
- [x] `ros2 topic hz` ≈ `publish_rate` → `average rate: 2.000` (default), `average rate: 5.000` (override).
- [x] Override `-p robot_id:=mower-02 -p publish_rate:=5.0` → `hardware_id: mower-02`, `message: 'mower-02: nominal'`, `average rate: 5.000`. No rebuild — parameters drive behaviour.
- [x] Bad-parameter `-p publish_rate:=0.0` → warning naming the parameter, node alive, zero `ZeroDivisionError`.
- [x] Purity check → `grep -n rclpy .../status_format.py` prints nothing (rc 1).
- [x] Stretch `state` works via named constants only → `state:=degraded` maps to `DiagnosticStatus.WARN` (`status_node.py:46-50`); `STALE` timer clause and the on-set parameter callback remain the documented bonus, not required.

**Concept check:** every line in the lesson's "Concepts this assignment requires" list maps to a taught section (§5–§16) — no gap to flag as a lesson defect this round.

---

## Top issues, ranked

None are blockers.

**1. consider — The validation fallback re-introduces one magic number, and the warning doesn't spell the parameter's name.**
`status_node.py:37-39` hard-codes the fallback `2.0` — the same constant as the `declare_parameter` default, written a second time. §11 teaches exactly this literal fallback, so the student followed the lesson, but req 5 says "no magic numbers anywhere" and a future maintainer now has two 2.0s to keep in sync. Cheap fix later: read the *declared default* instead — `self.rate` stays whatever it was declared to be when the override is invalid. Also, the warning text says "Publish rate" (human form) rather than `publish_rate` (declared name); the criterion accepts it, but any log greping for the parameter name wouldn't match it. Both are cosmetic and the lesson documents the accepted pattern; fold into lesson 02/03, not a re-review.

**2. consider — Environment quirks observed this round, so future reviews don't chase ghosts.**
(a) `ros2 topic hz` in this distro threw `ValueError: list.remove(x): x not in list` once mid-measurement on the default 2.0 Hz stream; the same command converged cleanly on re-runs (1.999 → 2.000, window 7). Tooling hiccup inside the CLI client, not this node. (b) The documented Lyrical `RCLError` race reappeared — but on `ros2 topic hz` and on `timeout`-killed runs, i.e. in *ros2 CLI clients* dying under SIGTERM, not in `status_node` (both SIGINT trials of the node itself were clean). Same root race §14 documents. Neither is the student's code.

**3. consider — Working tree reviewed, not yet committed.**
The passing state is uncommitted (only `6e56e16` exists). The pass verdict is against exactly what I built and ran; commit it as two commits (lesson, then code) so the milestone history records this exact state. The `docs/reviews/` directory is also untracked — this review should be committed with the milestone.

---

## What is solid

- **The two blockers' fixes are real, not cosmetic**: `test_copyright` actually runs (the green `5/0/0/0` proves it, not just a removed decorator), and the copyright lines correctly claim Jamie — the before/after diff shows OSRF's line gone from both source files.
- **Fail-safe, not fail-silent**: the `publish_rate:=0.0` case is genuinely handled — a `WARN` naming the parameter within one second, the node alive on the graph, and no `ZeroDivisionError`. This is the difference between a bad launch file and a three-mower fleet crashing on boot.
- **Logging discipline held**: one startup line per run, nothing per-publish. §13's rule and §17's example now agree with each other and with the code.
- The purity split is structural and testable: `status_format.py` is a pure function with no `rclpy`, exactly what `python-style` asks for and what lesson 03's unit tests will consume.
- Parameters behave: 2.0 → 5.0 Hz, `mower-01` → `mower-02`, no rebuild.
- Namespacing proven: two instances under `/mower_01` and `/mower_02` published distinct topics with identical code — the M7 shape working today.
- Ctrl-C is clean on the node itself: 2/2 exit 0, no traceback.

---

## Revisit list (for the professor, next lesson)

1. **Standardize the validation fallback pattern now that a working answer exists.** Count how many times `2.0` appears and whether a "fall back to the declared default" helper belongs in the lesson's §11. Lesson 03 (real unit tests) will want `validate_rate` as a testable pure function — a natural hook.
2. **Decision-record gap from the first review is now closed.** `01-status-message-type.md` never mentions `diagnostic_msgs/DiagnosticArray` on a namespaced `/diagnostics` — the ecosystem's usual diagnostics bus (what `diagnostic_aggregator` and dashboards consume). The professor has appended [`docs/decisions/01-status-names-and-diagnostics-feed.md`](../decisions/01-status-names-and-diagnostics-feed.md), which pins the naming decision and forces a `DiagnosticArray` comparison into a new decision record before M6. The choice of `DiagnosticStatus` on a private topic stays as accepted; no existing decision was edited.
3. **Renaming risk is now closed and recorded.** The node/topic names are committed to `status_node`/`/status_node/diagnostics`, and a rename after M1 bags invalidates recorded names. The same decision record (`01-status-names-and-diagnostics-feed.md`) pins them, so later milestones cannot relitigate the name without a new record that writes down the bag-migration cost first.
4. **Skill wording still nags.** This review again judged the topic-name-in-code reading (skill "never hard-code topic names") against the lesson's interface argument, and sided with the lesson as flagged in the first review. Not a blocker, but the `python-style` skill sentence remains a permanent ambiguity until someone resolves the two documents' wording.

---

## End-product check

The status node is now a piece the later milestones can build on rather than a photo of the lesson. `diagnostic_msgs/DiagnosticStatus` carries severity (M4), key/values (M6 dashboard), and `hardware_id` (M7 fleet health); the `state` parameter means the stretch hook for the M4 safety state machine is already wired; namespacing runs three-mower-shaped today. The two carry-forward risks from the first review stand: (a) no `Header`/timestamp — accepted in the decision record, but it means STALE detection must be consumer-side; and (b) a `DiagnosticStatus` on a *private* topic is not the ecosystem diagnostics bus, so if M6/M7 want `diagnostic_aggregator` or a fleet-wide feed the topic shape changes — allocate one decision record line before M6. No new interface risk was introduced by this round's fixes.