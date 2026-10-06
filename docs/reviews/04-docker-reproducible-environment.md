# Review 04 — Lesson 04: Docker / reproducible environment

Reviewed against `docs/lessons/04-docker-reproducible-environment.md` §10 (assignment and acceptance criteria), `docs/decisions/04-docker-reproducible-environment.md`, `docs/lessons/04-docker-reproducible-environment-hints.md`, and `spec/mower-spec.md` (M0 "done when": *clean build in a fresh container, tests pass*). Expected test counts per review 03: `mower_math` 13/0/0/0, `mower_status` 7/0/0/0.

**Environment:** host Docker `29.8.1`, base `ros:lyrical-ros-base` already present in the local image store (owner had built `mower-sim:m0` before this review; I rebuilt it myself, including a `--no-cache` pass). No ROS sourcing on the host for any Docker step. No nodes, daemons, or containers left running (all runs used `--rm`; only a pre-existing 8-day-old `hello-world` container remains in `docker ps -a`).

## Verdict: **pass**

Every acceptance checkbox below passed with the exact expected output, on a build and test run I executed myself from a `--no-cache` rebuild. Two non-blocking quality items are open (dead `entrypoint.sh`, see issue 1) and are tracked for the next review. The garbled commit message and README staleness are flagged as issues, not verdict-changers.

**Skills applied:** `ros2` (workspace/container flow, `colcon` semantics), `cpp-style`/`python-style` (n/a — no code touched this lesson; package state carried over from review 03 unchanged).

## Acceptance criteria (lesson §10) — each run by me

```bash
docker build -t mower-sim:m0 -f docker/Dockerfile .        # from repo root
```

- [x] **Image builds successfully from a clean state.** Both the cached rebuild and `docker build --no-cache` completed: `#8 naming to docker.io/library/mower-sim:m0 done`. Reported image size: **1.48 GB**. The `--no-cache` pass re-executes every Dockerfile step (base layer reuse is by definition — the base image *is* the pinned environment), so there is no cache-lulling risk in a COPY-only Dockerfile.
- [x] **No host build artifacts copied.** `docker run --rm mower-sim:m0 ls /ws/ros2_ws` → prints only `src`. Explicit check: `test -d /ws/ros2_ws/build -o -d /ws/ros2_ws/install -o -d /ws/ros2_ws/log` → "no build/install/log in image (fresh)". A first-run container also has no `build/mower_math/pytest.xml` pre-build, proving the compile happens *inside* the container run, not in the image.

```bash
docker run --rm -t mower-sim:m0 bash -lc "cd /ws/ros2_ws && source /opt/ros/lyrical/setup.bash && \
  colcon build --symlink-install && source install/setup.bash && \
  colcon test --packages-select mower_math mower_status && \
  colcon test-result --test-result-base build/mower_math --verbose && \
  colcon test-result --test-result-base build/mower_status --verbose"
```

- [x] `colcon build --symlink-install` → `Summary: 2 packages finished [1.80s]`.
- [x] `colcon test` → `Summary: 2 packages finished [14.7s]`.
- [x] `mower_math`: `Summary: 13 tests, 0 errors, 0 failures, 0 skipped` — exactly matches review 03.
- [x] `mower_status`: `Summary: 7 tests, 0 errors, 0 failures, 0 skipped` — exactly matches review 03.
- [x] **Zero skips in both packages** — `test_copyright` is genuinely enabled in-container, matching review 03.
- [x] **No `TODO`/`FIXME`:** `grep -rnIE 'TODO|FIXME' /ws/ros2_ws/src/mower_math /ws/ros2_ws/src/mower_status` → no output, exit 1.
- [x] Colcon is present in the base image (`/usr/bin/colcon`), so the decision record's conditional apt install was correctly *not* added — no extra apt layer, no version drift risk.
- [x] **Base tag claim confirmed independently:** `docker manifest inspect ros:lyrical-ros-base` succeeds; `docker manifest inspect osrf/ros:lyrical` fails with `no such manifest: docker.io/osrf/ros:lyrical`. Matches the decision record and lesson §2 exactly.

**Process/scope checks:**
- [x] `git diff 44b2b76..HEAD --stat` → only `.dockerignore` (new), `docker/Dockerfile`, `docker/entrypoint.sh`, `docs/decisions/04-…`, `docs/lessons/04-…`, `docs/lessons/04-…-hints` — nothing in `ros2_ws/src/` or `services/`. Working tree clean at review time.
- [x] `entrypoint.sh` file mode `100755` in the git index and on disk (executable as the lesson asked).
- [x] Every line of the lesson's "Concepts this assignment requires" list maps to a taught section (§1–§9); no lesson defect on coverage. One *teaching gap* is flagged below (entrypoint wiring) for lesson 05.

## Top issues

1. **should-fix (open) — `docker/entrypoint.sh` is dead code: not wired into the image in any way.** The Dockerfile only does `COPY ros2_ws/src /ws/ros2_ws/src`, so `entrypoint.sh` is never copied in; `docker inspect mower-sim:m0` shows `Entrypoint=[/ros_entrypoint.sh] Cmd=[bash]` (the base image's defaults), so `docker run mower-sim:m0` drops to an interactive shell and runs nothing. On the host it is equally unusable (`cd /ws/ros2_ws` doesn't exist there). Concretely: the file is not referenced, not reachable, and not documented as a manual step. Why it matters for the end product: the script is a second, drifting copy of the canonical test sequence (the acceptance battery), and exactly this kind of looks-right-but-does-nothing script is how a release gets shipped unverified. It did not block M0 because the lesson made the entrypoint optional ("If provided, make it executable") and the acceptance battery sources ROS explicitly — but the owner should either wire it (`COPY docker/entrypoint.sh` + `ENTRYPOINT`) or delete it. One of the two, next commit.
2. **consider (open) — the Dockerfile's trailing comment is leftover from the abandoned route.** Line 5, `# Or copy repo and rely on .dockerignore`, describes the copy-the-whole-repo alternative that was *not* taken; per AGENTS.md ("no hard-coded…; keep it minimal"), comments should say what the file does, not list rejected alternatives. One-line removal.
3. **consider (open) — commit hygiene slipped.** `dacffdd`'s message pastes the lesson's §12 paragraph, fences and all (`M0: add Dockerfile and entrypoint for reproducible build/test ``` (applies to the files created under docker/ …).`). It still names the change and the milestone, so AGENTS.md's substance is met, but the junk tail is exactly what review 03 praised the owner for *not* doing. It is already pushed (`main` tracks `origin/main` at `dacffdd`), so do **not** force-push history over it; treat it as the one bad commit and keep subsequent messages clean (`M0: …` one concept, no pasted lesson text). Related: `3693742` is titled "add Dockerfile and hints" but adds only `docs/` files — misleading traceability between docs commits and the assignment commit.
4. **consider (open) — the base is pinned by mutable tag, not digest.** `FROM ros:lyrical-ros-base` re-resolves on every build, which is standard for M0 and matches the decision record, but once CI lands (or M1 bags need bit-identical environments) a moving tag silently changes the toolchain. The decision record already anticipates tag problems; fold "pin by digest for CI" into the CI decision when it arrives. Not a defect now.

## What is solid

- **The fresh-container claim is real, not asserted.** The image contains only source (`ls /ws/ros2_ws` → `src`), the `--no-cache` rebuild re-executes all steps, and the compile + test run genuinely happen inside each ephemeral container — verified by the absence of `build/` pre-run, then `Summary: 2 packages finished` and exact 13/0/0/0 + 7/0/0/0 results in-run. This is precisely M0's "clean build in a fresh container, tests pass".
- **`.dockerignore` is complete and better than the minimum:** every entry the lesson listed plus `*.pyc`. Given the Dockerfile copies only `ros2_ws/src`, its practical effect is context-size and hygiene (no `.git`, no caches sneaking in via future COPY changes), which is the right cheap insurance.
- **The `entrypoint.sh` content itself is correct** — `set -euo pipefail`, sources ROS, runs the exact acceptance sequence with both `test-result` summaries. The defect is purely the missing wiring (issue 1), not the script's contents. Executable bit is set (`100755`).
- **No apt layer added where none was needed.** Colcon ships in `ros:lyrical-ros-base`, so the decision record's conditional install was correctly skipped — the image has one fewer moving part.
- **Scope discipline held end to end:** only `docker/`, `.dockerignore`, and lesson docs changed; no package code drifted during the Docker lesson; working tree clean at handoff.

## Revisit list (for the professor, lesson 05)

- **Entrypoint or not, decided and wired:** the lesson said "If provided, make it executable" but never said "or wire it, or document it as manual". With that wording, a student who copies the hints verbatim ships exactly this dead file. The next lesson (or a one-line addendum) should state: an entrypoint that isn't `COPY`ed and referenced by `ENTRYPOINT`/`CMD` is dead code — provide one fully wired, or don't provide one.
- **Commit message discipline:** one sentence, `M0:`-style tag, no pasted assignment text; docs commits should say "docs" when they are docs.
- **Mutable tags vs reproducibility:** when CI arrives, pin `FROM` by digest; the decision record's "what would change this" already names tag availability as the trigger.

## End-product check

This image is M0's CI stand-in and the base every later milestone builds on: M1–M7 add packages under `ros2_ws/src`, which the existing `COPY` picks up with no Dockerfile change, and `--symlink-install` keeps the fast-iteration loop alive for host work. The two real risks carried forward are the dead `entrypoint.sh` (ownership of "how the suite runs" must be single-sourced before the build sequence grows) and the mutable base tag (a silent toolchain change the moment the CI milestone lands — the decision record already names the trigger). M8's Gazebo swap is anticipated in the decision record (desktop/simulation variant then, not now). M0's done-when in the spec — clean build in a fresh container, tests pass — is met and independently re-verified with the exact expected counts. The serializer/interface layer introduced **no** new interface risk, and no interface risk is introduced for Gazebo by anything in this lesson.

**Note for the owner (not the reviewer's file):** the README status blurb (line 7) still says "Remaining for M0: … the Docker image", and the Quick-start section still says "Not available yet" — both are now stale; the milestone table is updated by this review, the prose is yours to refresh.

Verdict: **pass** — acceptance battery green from a `--no-cache` build I ran myself; `mower_math` 13/0/0/0 and `mower_status` 7/0/0/0 in a fresh container; TODO/FIXME grep empty; base-tag claim re-measured. Issue 1 (dead entrypoint) is should-fix and will be re-checked at the next review.