# 04 - Docker for a reproducible environment

**Date:** 2026-10-06 · **Milestone:** M0 · **Status:** accepted · **Relates to:** [01-package-layout.md](01-package-layout.md), [02-language-allocation-and-cpp-timing.md](02-language-allocation-and-cpp-timing.md), [03-testing-pytest-and-gtest.md](03-testing-pytest-and-gtest.md)

## Context

M0's "done when" is: *clean build in a fresh container, tests pass* (spec § "Milestones" / M0). The spec also states: *"Docker for reproducible builds from M0 onward"* (spec § "Constraints"). Lesson 03 makes `colcon test` mean something (unit tests + linters), producing passing results for `mower_math` (13 tests, 0 failures, 0 skipped) and `mower_status` (7 tests, 0 failures, 0 skipped) as verified in review 03's re-verification run. The `docker/` directory exists but is currently **empty**. README's "Quick start" is still a placeholder and will hold Docker + colcon commands once M0 is verified.

The goal of this decision is to pick a minimal, reproducible container workflow that lets the owner (who writes code) build and test in a clean, disposable environment identical in spirit to what a CI runner would provide, without adding a CI service yet. A scripted in-container run satisfies "a test that runs in CI-style" for M0; the spec does not require a GitHub Actions file at M0.

## Options

1. **Official ROS 2 Lyrical image (`ros:lyrical-ros-base`)** — use the Docker Library `ros:lyrical-ros-base` (Ubuntu 24.04 + ROS 2 Lyrical core). Measured: `docker manifest inspect ros:lyrical-ros-base` succeeds. Mount/copy the repo into the container workspace, source `/opt/ros/lyrical/setup.bash`, run `colcon build --symlink-install` and `colcon test`. If `colcon` is missing in the pulled image, install `python3-colcon-common-extensions`.
2. **Ubuntu 24.04 + install ROS 2 Lyrical packages from apt in Dockerfile** — start from `ubuntu:24.04`, add ROS 2 apt sources and `ros-lyrical-ros-base`, install tooling as needed.
3. **Host-based reproducibility only (no Dockerfile now)** — do not create a Dockerfile in `docker/` yet; rely on host environment. This conflicts with spec constraint "Docker for reproducible builds from M0 onward" and M0's done-when requiring a *fresh container*.

## Decision

**Option 1: use `ros:lyrical-ros-base` (Docker Library).**

Reasons (with measurements backing where possible):

- **Correct tag measured.** `docker manifest inspect ros:lyrical-ros-base` succeeds. `docker manifest inspect osrf/ros:lyrical` fails ("no such manifest: docker.io/osrf/ros:lyrical"). The `osrf/ros` lyrical variants on Docker Hub include `lyrical-desktop*`, `lyrical-simulation*` but no plain `lyrical` or `lyrical-ros-base` under `osrf/ros` at the checked time. Docker Library `ros` has `lyrical`, `lyrical-ros-base`, `lyrical-ros-core`, etc. We pick the minimal `ros:lyrical-ros-base`.
- **Matches the target distro.** Host has ROS 2 Lyrical at `/opt/ros/lyrical` and `ROS_DISTRO=lyrical`. Same distro on Ubuntu 24.04.
- **Minimal bootstrap friction.** `ros-base` is the smallest core variant; if `colcon` is not present, install `python3-colcon-common-extensions`. Avoids `desktop`/simulation packages.
- **Satisfies M0 done-when.** Disposable container can run: source `/opt/ros/lyrical/setup.bash`, `colcon build --symlink-install`, `colcon test`, `colcon test-result --test-result-base build/mower_math`, `colcon test-result --test-result-base build/mower_status` — producing 13/7 tests with 0 failures, 0 skipped (per review 03). Fresh container proof requires copying only source (no host build artifacts); see lesson for `.dockerignore` guidance.
- **Keeps scope tight.** No CI service added now; scripted in-container run is sufficient. `docker/` is the reproducible environment location.
- **Respects existing decisions.** 01, 02, 03 unchanged.
- **No changes to repo code.** Only `docker/`, `docs/lessons/`, `docs/decisions/`.

Rejected:

- **Option 2 (Ubuntu 24.04 + apt install).** Also correct; rejected as default to avoid duplicating canonical bootstrap. Revisit if needed.
- **Option 3 (host-only).** Violates spec constraints and M0 done-when.

## What would change this

- **If `ros:lyrical-ros-base` lacks colcon.** The Dockerfile installs `python3-colcon-common-extensions` (owner confirms during acceptance). 
- **If base tag becomes unavailable/problematic.** Switch to `ros:lyrical` (larger) or Ubuntu 24.04 + ROS 2 Lyrical apt packages (option 2), recording measured reason in a new decision record.
- **If we need GUI/Gazebo later.** M8 may use `ros:lyrical-desktop` or Gazebo variant; not M0.
- **If CI is added later.** Can reuse same Dockerfile/commands; workflow is separate decision.
- **If image pulls blocked.** Mark claims "not yet verified" and document verification commands.