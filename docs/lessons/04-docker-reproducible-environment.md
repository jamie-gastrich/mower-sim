# 04 - Docker / reproducible environment

**Milestone:** M0 · **Language:** N/A (environment/container) · **Prerequisite:** lesson 03 (unit tests and `mower_math`), and review 03 (passed)

**Concepts this assignment requires** — each line links to the section that teaches it:

- [Where this fits](#1-where-this-fits)
- [Verification table](#2-verification-table)
- [Options survey (what base image and workflow)](#3-options-survey-what-base-image-and-workflow)
- [What "fresh container" means](#4-what-fresh-container-means)
- [What goes in the Docker image](#5-what-goes-in-the-docker-image)
- [Build/run flow (workspace mounting vs copying)](#6-buildrun-flow-workspace-mounting-vs-copying)
- [Running tests inside the container](#7-running-tests-inside-the-container)
- [Environment hygiene (ROS_DOMAIN_ID, cleanup)](#8-environment-hygiene-ros_domain_id-cleanup)
- [Worked example (scratch container)](#9-worked-example-scratch-container)
- [Assignment](#10-assignment-create-docker-for-mower-sim)
- [Where this leaves M0](#11-where-this-leaves-m0)
- [Commit](#12-commit)

---

## 1. Where this fits

M0's done-when is *"clean build in a fresh container, tests pass"* (spec § Milestones). The spec also requires *"Docker for reproducible builds from M0 onward"* (spec § Constraints). Lesson 03 added real unit tests: review 03 shows `mower_math` has **13 tests, 0 failures, 0 skipped** and `mower_status` has **7 tests, 0 failures, 0 skipped**. The Docker lesson is the "runs in CI-style" half of M0: the same `colcon build` and `colcon test` commands must succeed inside a clean, disposable container, not just on the host.

The README's "Quick start" is currently empty and will hold Docker + colcon commands once M0 is verified. The `docker/` directory exists but is empty. This lesson adds the minimal Docker pieces needed to satisfy M0's done-when without adding a CI service. The first C++ node remains at M2 (decision record 02), so the image only needs what Python + ROS 2 Lyrical require to build and test the existing packages.

## 2. Verification table

Everything in this lesson that could be checked on this machine was checked before writing down. Scratch work used `/tmp/opencode/l04-proof` (created, left empty after checks) and throwaway containers only. No builds of the repo happened inside the repo itself.

| Claim | How it was checked | Result |
|---|---|---|
| Docker is available | `docker --version` | `Docker version 29.8.1, build 4a63305` |
| Docker can run a throwaway container | `docker run --rm ubuntu:24.04 echo 'ok'` | `ok` (image pulled) |
| `colcon` is installed on host | `which colcon` | `/usr/bin/colcon` |
| ROS 2 Lyrical present on host | `ls /opt/ros/lyrical` and `env \| grep ROS` | `setup.sh`, `setup.zsh`, `share`, `tools`; `ROS_DISTRO=lyrical`, `ROS_VERSION=2`, `ROS_PYTHON_VERSION=3` |
| `docker/` is empty | `ls /home/jamie/mower-sim/docker` | 0 entries |
| Correct base image tag measured | `docker manifest inspect ros:lyrical-ros-base` and `docker manifest inspect osrf/ros:lyrical` | `ros:lyrical-ros-base` succeeds; `osrf/ros:lyrical` fails ("no such manifest: docker.io/osrf/ros:lyrical") — **verified** |
| Fallback/alternative tags measured | Docker Hub tag checks for `ros` and `osrf/ros` (lyrical) | `ros:lyrical`, `ros:lyrical-ros-base`, `ros:lyrical-ros-core` exist; `osrf/ros` has lyrical-desktop*/simulation* but no plain `lyrical`/`-ros-base` under `osrf/ros` — **verified** |
| "Fresh container" means non-persistent, removed after run | docker semantics (`--rm`) | standard — **verified** conceptually; full in-container build not executed here |

Not yet verified:
- Full `colcon build` and `colcon test` inside a container using `ros:lyrical-ros-base` against this workspace (image pull may be large; owner verifies in acceptance). If `colcon` is missing, owner installs `python3-colcon-common-extensions`.
- Exact behavior of an entrypoint script in the container environment (exit codes). Owner validates via acceptance criteria.

## 3. Options survey: what base image and workflow

Survey is in decision record [`04-docker-reproducible-environment.md`](../decisions/04-docker-reproducible-environment.md).

| Option | Reproducible | Matches Lyrical | Maintenance | CI-style ready | Cost |
|---|---|---|---|---|---|
| **1. `ros:lyrical-ros-base` (Docker Library)** | yes | yes (Ubuntu 24.04) | minimal | yes | standard image |
| 2. Ubuntu 24.04 + ROS 2 Lyrical apt packages | yes | yes | more bootstrap | yes | explicit |
| 3. Host-only (no Docker) | no | host-dependent | none | no | conflicts with spec |

**Chosen:** Option 1 (`ros:lyrical-ros-base`).

## 4. What "fresh container" means

A *fresh container* is:
- Started from the specified base image (no local modifications to that image layer),
- Disposable (`--rm`), with no volumes carrying build artifacts from previous runs except the workspace mounted/read as needed,
- Independent of host build state (`build/`, `install/`, `log/` inside container are created anew),
- Running the same sequence: source ROS, build with `colcon build --symlink-install`, then test with `colcon test` and report results.

The M0 done-when requires this sequence to complete with tests passing.

## 5. What goes in the Docker image

Keep it minimal. For M0, the image needs:
- Base: `ros:lyrical-ros-base` (Ubuntu 24.04, ROS 2 Lyrical core). Measured: `ros:lyrical-ros-base` exists; `osrf/ros:lyrical` does not.
- Workspace directory (e.g. `/ws`)
- ROS sourced via `/opt/ros/lyrical/setup.bash`
- Ability to run `colcon build --symlink-install` and `colcon test` (if missing, install `python3-colcon-common-extensions`)

Optional small conveniences (not required): `git`, basic shell. Do not add GUI packages.

What does **not** belong: Gazebo/desktop, CI service config, large datasets, or anything not needed to build/test the current packages.

## 6. Build/run flow (workspace mounting vs copying)

Two common approaches: copy source into image (fully reproducible, good for CI) or mount source as a volume (faster iteration). For the M0 acceptance and clarity:

- **Create `docker/Dockerfile`** in the empty `docker/` directory (owned by assignment). Base on `ros:lyrical-ros-base`.
- **Copy only source; exclude build artifacts.** Host currently has `ros2_ws/build/`, `ros2_ws/install/`, `ros2_ws/log/` (git-ignored). To keep the "fresh container" claim real, create a `.dockerignore` (at minimum: `ros2_ws/build/`, `ros2_ws/install/`, `ros2_ws/log/`, `log/`, `.git/`, `__pycache__/`, `.pytest_cache/`, `.gitignore`) OR copy only `ros2_ws/src/`. The acceptance criteria below include a check that `/ws/ros2_ws` contains no `build`/`install`/`log`.
- Use `--symlink-install` (consistent with lessons 01/03).
- Source `/opt/ros/lyrical/setup.bash` in every shell step that runs `colcon`. If `colcon` is missing, install `python3-colcon-common-extensions`.

## 7. Running tests inside the container

Same commands as host, but inside container:
```bash
cd /ws/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --packages-select mower_math mower_status
colcon test-result --test-result-base build/mower_math --verbose
colcon test-result --test-result-base build/mower_status --verbose
```

Expected summaries (per review 03): `mower_math` 13 tests 0 failures 0 skipped; `mower_status` 7 tests 0 failures 0 skipped. Zero skips is required (copyright enabled).

## 8. Environment hygiene (ROS_DOMAIN_ID, cleanup)

- Use a dedicated `ROS_DOMAIN_ID` for any runtime checks if nodes are started (assignment acceptance checks for node behavior remain possible, but Docker lesson focuses on build+test). Build/test do not require a running graph.
- Containers are ephemeral (`--rm`). After verification, no ROS nodes/daemons/simulator windows left running.
- Experiments remain in `/tmp/opencode` only (as before). No scratch in `ros2_ws/` or `services/`.

## 9. Worked example (scratch container)

A tiny throwaway check to confirm Docker works and base image is reachable conceptually:
```bash
mkdir -p /tmp/opencode/l04-proof && cd /tmp/opencode/l04-proof
docker run --rm ubuntu:24.04 echo 'ok'
```
Result: `ok`. This is **verified** on this machine. A full ROS base image run is **not yet verified** here (large pull avoided). The assignment requires the owner to perform the full sequence and confirm results. This matches the "not yet verified" marking convention.

## 10. Assignment: create Docker for mower-sim

**Language:** N/A (infrastructure). Create files under `docker/` (empty now), plus a `.dockerignore` at the repo root if taking the copy-repo route; do **not** touch `ros2_ws/src/`, `services/`, `README.md`, or other code.

### Requirements

1. **`docker/Dockerfile`**
   - Base: `FROM ros:lyrical-ros-base` (fallback `ros:lyrical` if unavailable). If `colcon` is missing, install `python3-colcon-common-extensions`.
   - Set working directory, e.g. `WORKDIR /ws`
   - Copy only source into container. Create a `.dockerignore` at repo root (at minimum: `ros2_ws/build/`, `ros2_ws/install/`, `ros2_ws/log/`, `log/`, `.git/`, `__pycache__/`, `.pytest_cache/`, `.gitignore`) and copy the needed source (e.g. `COPY ros2_ws/src /ws/ros2_ws/src` and any other required files), OR copy repo but ensure artifacts excluded. The goal is **no host build artifacts** in the image.
   - Ensure ROS is sourced in build/test context. Provide an entrypoint or document commands.

2. **`docker/entrypoint.sh`** (optional but recommended) — sources ROS and runs the standard sequence. If provided, make it executable.

3. **Build and test in a fresh container** using the Dockerfile. Demonstrate the sequence produces results matching review 03 (13/0/0 for `mower_math`, 7/0/0 for `mower_status`). Prove no host artifacts copied (see check below).

### Acceptance criteria

Each command must pass (run from repo root or as specified). All must succeed.

```bash
cd ~/mower-sim
docker build -t mower-sim:m0 -f docker/Dockerfile .
```
- [ ] Image builds successfully from a clean state.
- [ ] Prove no host artifacts copied: `docker run --rm mower-sim:m0 ls /ws/ros2_ws` shows **no** `build`, `install`, or `log` directories.

```bash
docker run --rm -t mower-sim:m0 bash -lc "\
  cd /ws/ros2_ws && \
  source /opt/ros/lyrical/setup.bash && \
  colcon build --symlink-install && \
  source install/setup.bash && \
  colcon test --packages-select mower_math mower_status && \
  colcon test-result --test-result-base build/mower_math --verbose && \
  colcon test-result --test-result-base build/mower_status --verbose"
```
- [ ] `mower_math`: summary shows **13 tests, 0 errors, 0 failures, 0 skipped**
- [ ] `mower_status`: summary shows **7 tests, 0 errors, 0 failures, 0 skipped**
- [ ] No `TODO`/`FIXME` in tested packages: `grep -rnIE 'TODO|FIXME' /ws/ros2_ws/src/mower_math /ws/ros2_ws/src/mower_status` prints nothing (exit 1 with no matches)

Optional (for README later): document the Quick start using this flow. Not required to edit README in this assignment — professor/agents only write to `docs/lessons/` and `docs/decisions/`.

### Interfaces/notes
- No CI service is created. The scripted in-container run is the CI-style test for M0.
- Base tag: `ros:lyrical-ros-base` (measured valid). `osrf/ros:lyrical` does not exist. If `ros:lyrical-ros-base` lacks `colcon`, install `python3-colcon-common-extensions`. If tag becomes unavailable, owner documents measured fallback.

## 11. Where this leaves M0

After this lesson and a passing review: the whole workspace builds and all M0 tests pass in a *fresh container*. That satisfies M0's done-when ("clean build in a fresh container, tests pass"). With lesson 01 (node) and lesson 03 (unit tests) already passing, M0 is complete. Next work is M1 (mower model and 2D sim) per spec.

## 12. Commit

One commit, one concept:
```
M0: add Dockerfile and entrypoint for reproducible build/test
``` (applies to the files created under `docker/` by the owner as part of this assignment). The lesson and decision record in `docs/` are separate documentation commits if desired, but the assignment is the infrastructure change in `docker/`.