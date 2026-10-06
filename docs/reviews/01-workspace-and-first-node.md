# Review 01 — workspace and first node (`mower_status`)

**Milestone:** M0 · **Scope:** `ros2_ws/src/mower_status/` (commit `6e56e16`) · **Reviewer:** Reviewer agent
**Yardsticks:** `docs/lessons/01-workspace-and-first-node.md` §18 + hints, `docs/decisions/01-package-layout.md`, `docs/decisions/01-status-message-type.md`
**Build environment:** native, no Docker. Docker is lesson 04, so M0's "clean build in a fresh container" criterion is **not yet testable**; everything below was run natively on this machine.

Commands used (fresh shell state each time):

```
cd ros2_ws && source /opt/ros/lyrical/setup.bash && colcon build --symlink-install   # exit 0, 2 packages
colcon test --packages-select mower_status                                           # exit 0
colcon test-result --verbose --test-result-base build/mower_status                   # 5 tests, 0 errors, 0 failures, 1 skipped
colcon test-result --verbose                                                         # 10 tests, 0 errors, 0 failures, 2 skipped (workspace-wide)
```

Runtime checks used `ROS_DOMAIN_ID=81`. All nodes I started were stopped and waited on; `ros2 daemon stop` run for my domain; no `status_node` process left behind.

---

## Verdict: **not yet**

Two things block it.

1. **Requirement 10 is not done.** `test/test_copyright.py` still carries `@pytest.mark.skip`, so the licence check never runs. That is an explicit §18 requirement, it fails as written, and I verified the fix passes: running `ament_copyright` by hand returns `rc = 0`, `No problems found, checked 8 files`.
2. **The assignment cannot be passed as written, because §18 now contradicts itself** — and the contradiction was introduced by an edit to `docs/lessons/01-workspace-and-first-node.md` that rode along in the code commit `6e56e16`. Requirement 7 (`name = 'status_node'`) and the acceptance criterion (`name: mower_status`) are mutually exclusive; requirement 4 (node name `mower_status`) and the interfaces table (Node `status_node`) are mutually exclusive. Whichever way the owner codes it, at least one box fails. This is a lesson defect and it must be reconciled before any verdict can be a pass.

The code itself is close to right: build green, tests green, parameters genuinely drive behaviour, the purity split is real, and two namespaced instances ran side by side without collision. One line edit unblocks issue 1; issue 2 is the professor's to fix.

---

## Acceptance criteria

### §18 requirements 1–10

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | Scaffolded `ament_python` package, real description/maintainer, Apache-2.0, no `TODO` | **PASS** | Scaffold fingerprints intact: `setup.cfg` `install_scripts=$base/lib/mower_status`, `resource/mower_status` is 0 bytes, `py.typed`, `LICENSE` = Apache 2.0 (202 lines), 5 scaffold tests. `grep -rn "TODO" ros2_ws/src/mower_status/` → no output (rc 1). |
| 2 | `<depend>rclpy</depend>` and `<depend>diagnostic_msgs</depend>` | **PASS** | `package.xml:10-11`. |
| 3 | One `console_scripts` executable named `status_node` | **PASS** | `setup.py:28`; `ros2 pkg executables mower_status` → `mower_status status_node`. |
| 4 | Node class inherits `Node`, **node name `mower_status`**, registered as `status_node` | **FAIL (as written)** | `status_node.py:27` is `super().__init__('status_node')`. Matches the interfaces table *as edited in the same commit*, contradicts requirement 4 and hints Tier 1/Tier 3. `ros2 param list /mower_status` → `Node not found`. See Top issue 2. |
| 5 | Exactly three parameters, all declared, no magic numbers | **PASS (with note)** | `ros2 param list /status_node` → `base_frame`, `publish_rate`, `robot_id`, `state` (+ `use_sim_time`, `start_type_description_service`, which are not yours). The 4th is the stretch goal, which §18 explicitly instructs, so "exactly three" and the stretch goal contradict each other — lesson tension, not an owner failure. `level` comes only from `DiagnosticStatus.OK`/`WARN` (`status_node.py:44,45,47`); no raw integers anywhere. |
| 6 | `DiagnosticStatus` on `~/diagnostics`, QoS depth 1, timer at `publish_rate` | **PASS** | `status_node.py:37-38`; `ros2 topic list` → `/status_node/diagnostics`; `ros2 topic hz` → `average rate: 2.003` (default 2.0), `average rate: 4.999` with `-p publish_rate:=5.0`. |
| 7 | `level` named constant; `name`; `hardware_id` = `robot_id`; `message` = pure-function return; ≥2 `values` incl. `base_frame` and a runtime-changing one | **PASS on content, FAIL on the acceptance line** | Measured `ros2 topic echo --once`: `level: "\0"`, `hardware_id: mower-01`, `message: 'mower-01: nominal'`, `values: publish_count` + `base_frame`. `publish_count` changes across runs: `'15'`, `'23'`, `'5'`, `'7'`. `msg.name` is `'status_node'` (`status_node.py:48`), which satisfies edited requirement 7 but **fails** the acceptance criterion that demands `name: mower_status`. |
| 8 | Pure function in its own module, no `rclpy`, node only calls it | **PASS** | `grep -n rclpy .../status_format.py` → no output (rc 1). `status_format.py:15-16` is `format_status_message(robot_id, state)` — no `self`, no ROS state. Called at `status_node.py:50`. |
| 9 | `main()` shutdown pattern; `get_logger()` not `print()` | **PASS** | `status_node.py:58-67` matches §14 exactly (init / try / `except (KeyboardInterrupt, ExternalShutdownException)` / finally destroy+shutdown). `grep -rn "print("` in the package → no output. 6 SIGINT trials: **5 clean exits rc=0**, 1 exit rc=1 with `RCLError: failed to initialize wait set` — this is the Lyrical race §14 documents at 5/6, reproduced by me, **not the owner's bug**. |
| 10 | Apache header on sources **and** `@pytest.mark.skip` removed from `test_copyright` | **FAIL** | Header present on `status_node.py` and `status_format.py` — but it reads `Copyright 2017 Open Source Robotics Foundation, Inc.` (see Top issue 3), and `test/test_copyright.py:20` still has `@pytest.mark.skip(reason='No copyright header has been placed...')`. Result: `5 tests, 0 errors, 0 failures, 1 skipped`. Hand-run `ament_copyright` → `rc = 0, No problems found, checked 8 files`, so enabling it is a one-line fix that passes. |

### §18 acceptance-criteria checklist (each run by me)

- [x] `colcon build --symlink-install` → `Summary: 2 packages finished`, exit 0 (native, no container).
- [x] No `TODO` in `ros2_ws/src/mower_status/` → grep empty (rc 1).
- [ ] **`colcon test-result --verbose` ends with `0 failures` (one skip allowed only if `test_copyright` has been enabled and passes)** — **FAIL.** mower_status alone: `5 tests, 0 errors, 0 failures, 1 skipped`, and the single skip *is* `test_copyright`, which was never enabled. Workspace-wide: `10 tests, 0 failures, 2 skipped` (the second is out-of-scope `mower_math`).
- [x] `ros2 pkg executables mower_status` → `mower_status status_node`.
- [x] Startup line names robot id and rate, node stays running → `[INFO] ... [status_node]: status_node up at 2.0 Hz for mower-01`.
- [x] Ctrl-C → `[ros2run]: Received signal:  Interrupt`, no traceback → 5 of 6 trials; the 6th reproduced the documented Lyrical `RCLError` race (lesson §14: same 5/6). Environment quirk, confirmed by my own measurement, not attributed to the owner.
- [ ] **`ros2 param list /status_node` shows all three parameters** → shows all three *and* `state`. Passes on `/status_node`; fails on `/mower_status` (`Node not found`) because requirement 4 says the node is called `mower_status`. Judged **pass**, with the naming contradiction recorded as a lesson defect.
- [ ] **`ros2 topic echo --once /status_node/diagnostics` shows `level: "\0"`, `name: mower_status`, `hardware_id`, non-empty `message`, ≥2 `values`** → **FAIL.** Everything matches except `name: status_node`, not `mower_status`. This box and edited requirement 7 cannot both be satisfied.
- [x] `ros2 topic hz /status_node/diagnostics` ≈ `publish_rate` → `average rate: 2.003` (default 2.0).
- [x] Override `-p robot_id:=mower-02` → `hardware_id: mower-02` (and `message: 'mower-02: nominal'`).
- [x] Override `-p publish_rate:=5.0` → `average rate: 4.999`, startup line `up at 5.0 Hz for mower-02`. No rebuild — parameters genuinely drive behaviour.
- [x] Purity check `grep -n rclpy .../status_format.py` → prints nothing (rc 1).

**Environment behaviour I measured myself (recorded so it is not blamed on the owner):** the Ctrl-C `RCLError` race (1 in 6), and `ament_flake8` in this distro does not flag a single blank line before a top-level `def` in `status_format.py` (it reports `9 files checked / No problems found`), so that nit is not a test failure here.

---

## Top issues, ranked

**1. blocker — Requirement 10 not done: `test_copyright` is still skipped.**
`ros2_ws/src/mower_status/test/test_copyright.py:20` still carries `@pytest.mark.skip`. The licence gate is the one automated check that catches missing/incorrect attribution, and it is switched off — while issue 3 shows the attribution is in fact wrong. Fix is one line and I verified it passes (`ament_copyright` → `rc 0`). Why it matters now: a repository that ships a license check that never runs will keep not running it for every later package.

**2. blocker — The yardstick was edited inside the code commit and is now self-contradictory.**
Commit `6e56e16` changes `docs/lessons/01-workspace-and-first-node.md` alongside the code: requirement 7 `name` `'mower_status'` → `'status_node'`, interfaces table Node `mower_status` → `status_node`, and every acceptance command `/mower_status/...` → `/status_node/...`. It did **not** update requirement 4 (still "node name `mower_status`"), the acceptance criterion at line 853 (still `name: mower_status`), or the hints (Tier 1 and Tier 3 still `/mower_status/diagnostics`, `super().__init__('mower_status')`, `msg.name = 'mower_status'`). Requirement 7 and line 853 are mutually exclusive, so §18 is currently unpassable. Process problem too: the assignment must not be rewritten in the same commit as the answer to it — the reviewer has no stable target. Professor: reconcile §4/§7/§18/hints to one naming decision, in its own commit.

**3. should-fix — Wrong copyright holder on the owner's own source files.**
`status_node.py:1` and `status_format.py:1` say `Copyright 2017 Open Source Robotics Foundation, Inc.` This is Jamie's code. §18 requirement 10 says "copy it from `ros2_ws/src/mower_math/test/test_flake8.py`", which carries OSRF's line, while the hints' Tier 3 show `# Copyright 2026 Jamie` — **the lesson contradicts itself**, so the owner did what §18 said. `ament_copyright` passes anyway because it only checks that *a* copyright statement exists, so nothing caught it. Why it matters: on a portfolio project the copyright line is a claim of authorship, and it is currently false. Lesson fix (§18 requirement 10) + owner fix (line 1 of both source files).

**4. should-fix — Per-publish `info` log, and it lies.**
`status_node.py:55` logs `published OK for {robot_id}` on every tick: 16 seconds produced 32 identical lines at 2 Hz. §13 says "one startup line and one line when something changes is plenty", and the hints' Tier-3 near-solution omits the line entirely. Worse, it says **OK** while the node publishes **WARN**: with `-p state:=degraded` I measured `level: "\x01"` in the message and `published OK for mower-01` in the log. Why it matters: `/rosout` noise costs disk and signal-to-noise on an edge machine, and a log line that contradicts the severity is worse than no line — M6's dashboard and M7's fault recovery will both read this stream.

**5. consider — `publish_rate` is never validated; `0.0` crashes the node.**
`ros2 run mower_status status_node --ros-args -p publish_rate:=0.0` exits 1 with `ZeroDivisionError: division by zero` at `status_node.py:38` (`1.0 / self.rate`), traceback and all. Not taught in §11, so this is partly a lesson gap — but a one-line guard (`if self.rate <= 0: raise ValueError(...)` or clamp with a warning) is the difference between a bad launch file producing a diagnosable message and a node that dies on startup in a three-mower fleet.

---

## What is solid

- The scaffold was respected, not hand-rolled: `setup.cfg`, the 0-byte resource marker, `py.typed`, Apache `LICENSE`, and the five linter tests are all where `ros2 pkg create` puts them, and `ament_flake8`/`ament_pep257`/`ament_mypy`/`ament_xmllint` all pass.
- Parameters actually reconfigure the node: measured `2.003 Hz → 4.999 Hz` and `hardware_id: mower-01 → mower-02` with no rebuild. This is the lesson's central claim, demonstrated.
- The purity split is real, not decorative: `status_format.py` has no `rclpy` (grep empty), is a genuine pure function, and the node is a thin wrapper — exactly what `python-style` and the `ros2` skill ask for, and what lesson 03's tests need.
- The shutdown pattern is copied correctly and works: 5/6 clean Ctrl-C exits, with the 6th reproducing the exact Lyrical race §14 documents.
- Namespacing proven, not assumed: two instances under `/mower_01` and `/mower_02` ran concurrently with distinct topics (`/mower_01/status_node/diagnostics`), distinct `hardware_id`s, and no collisions. That is the M7 shape working today.
- The stretch goal works and uses only named constants: `state:=degraded` → `level: "\x01"` via `DiagnosticStatus.WARN`.

---

## Revisit list (for the professor, next lesson)

1. **§18 is internally inconsistent** (requirement 4 vs interfaces table; requirement 7 vs the `name:` acceptance line; §18 vs hints Tier 1/Tier 3). Pick one node name — and note that changing it after M1 bags exist rewrites recorded topic names, so decide *now*.
2. **§18 requirement 10 vs hints Tier 3 on the copyright line** — one says "copy OSRF's header", the other says `Copyright 2026 Jamie`. Fix §18.
3. **§17 worked example contradicts §13.** The example logs `published OK` on every publish; §13 then tells the student not to. The student copied the example. Fix the example or the rule.
4. **Test-result criterion needs scoping.** `colcon test-result --verbose` is workspace-wide, and `mower_math`'s `test_copyright` stays skipped until lesson 03, so "one skip allowed only if test_copyright has been enabled" is unsatisfiable for the whole-workspace command. Scope it to `--test-result-base build/mower_status`.
5. **Parameter validation is not taught anywhere** (§11 stops at `declare_parameter`/`get_parameter`), yet requirement 5 says "no magic numbers" and a rate of 0 is a division by zero. Teach the guard.
6. **Skill vs lesson disagreement — flagging rather than picking silently.** The `python-style` skill says "never hard-code topic names or rates"; §9 teaches that the topic name *is* the interface and belongs in code, with parameters for configuration. The owner followed §9 (`~/diagnostics` in code, rate as a parameter). I side with the lesson — the skill should be read as "no magic *config*". Someone should reconcile the wording so the two documents stop disagreeing.
7. **Decision record gap, not an owner error.** `01-status-message-type.md` never surveyed `diagnostic_msgs/DiagnosticArray` on a namespaced `/diagnostics` — the ecosystem's standard diagnostics shape, which `diagnostic_aggregator` and dashboards already understand. The choice of `DiagnosticStatus` on a private topic is defensible and already accepted, but the "what would change this" section should acknowledge the aggregator. (Append a new entry; do not edit the existing one.)

Out of scope, one line each: `mower_math/` is still a bare scaffold with its `test_copyright` skip (expected until lesson 03); and commit `375f72c` tracked a colcon `log/` directory at the repo root, which `.gitignore` only covers as `ros2_ws/log/` — worth a `.gitignore` line.

---

## End-product check

The interface is the right shape for where this is going. `diagnostic_msgs/DiagnosticStatus` carries a severity level (M4's state machine output), an extensible `KeyValue[]` (M6's dashboard numbers), and `hardware_id` for per-robot identity (M7's fleet health), and I verified the namespacing claim by running two mowers concurrently — `/mower_01/status_node/diagnostics` and `/mower_02/status_node/diagnostics` did not collide, and the node code was unchanged. Three risks to carry forward: (a) the message has no `Header`, so no timestamp — already recorded as an accepted consequence in the decision record, but it means STALE detection has to be consumer-side or carried as a `KeyValue`; (b) a `DiagnosticStatus` on a *private* topic is not the ecosystem's diagnostics bus, so if M6/M7 ever want `diagnostic_aggregator` or a single fleet-wide diagnostics feed, the topic shape changes — worth one line in a new decision record before M6; (c) the node's name and topic are being finalised while the lesson still disagrees with itself, and renaming after M1 bags exist will invalidate recorded topic names. Fix the naming and the per-publish log before M1, when it is still free.
