# Hints for 04 - Docker / reproducible environment

Three tiers. Read tier 1 first. Only if stuck, read tier 2. Tier 3 is near-solution — use to check reasoning, not to skip thinking.

---

## Tier 1: nudges

**`docker/` is empty and the assignment says create files there.**
Only create files under `docker/`, `docs/lessons/`, and `docs/decisions/` as instructed. Do not edit `ros2_ws/src/`, `services/`, or `README.md`.

**Docker build fails to find files.**
When using `COPY . /ws`, run `docker build` from the repo root (`~/mower-sim`) so the build context includes `ros2_ws/` and `docker/`.

**Base image tag issues.**
The correct tag is `ros:lyrical-ros-base` (Docker Library). Measured: `docker manifest inspect ros:lyrical-ros-base` succeeds; `docker manifest inspect osrf/ros:lyrical` fails ("no such manifest: docker.io/osrf/ros:lyrical"). Docker may need to pull the image on first build; if network is constrained, note it. If `colcon` is missing in the pulled image, install `python3-colcon-common-extensions`.

**Tests pass on host but fail in container.**
Common causes: missing dependencies not declared in `package.xml`, or building from a dirty host tree copied in. Use a clean working tree and ensure all packages’ `package.xml` have correct `<depend>` entries (mower_status already has `rclpy`, `diagnostic_msgs`).

**Container exits immediately or with wrong working dir.**
Set `WORKDIR /ws/ros2_ws` or `cd` explicitly in the run command. The provided acceptance command cds to `/ws/ros2_ws`.

---

## Tier 2: directions

**Minimal Dockerfile structure (with clean context):**
Create a `.dockerignore` (e.g. exclude `ros2_ws/build/`, `ros2_ws/install/`, `ros2_ws/log/`, `log/`, `.git/`, `__pycache__/`, `.pytest_cache/`, `.gitignore`) so host artifacts don't enter the image. Then:
```dockerfile
FROM ros:lyrical-ros-base
WORKDIR /ws
# Copy only source to keep build fresh
COPY ros2_ws/src /ws/ros2_ws/src
# Or copy repo and rely on .dockerignore
```
If `colcon` is missing, add `RUN apt-get update && apt-get install -y python3-colcon-common-extensions && rm -rf /var/lib/apt/lists/*`. That keeps the "fresh container" claim real.

**Entry point (optional):**
A simple `docker/entrypoint.sh` might source ROS and run the standard sequence. Make it executable (`chmod +x`). Example:
```bash
#!/usr/bin/env bash
set -e
cd /ws/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --packages-select mower_math mower_status
```

**Run command form.**
Use `bash -lc` to ensure login shell sources behave predictably. The acceptance criteria shows the exact chained command.

**Test counts verification.**
After tests, check verbose results for both packages:
- `mower_math`: **13 tests, 0 failures, 0 skipped**
- `mower_status`: **7 tests, 0 failures, 0 skipped**

Match review 03 exactly.

---

## Tier 3: near-solution

**`.dockerignore` (repo root):**
```text
ros2_ws/build/
ros2_ws/install/
ros2_ws/log/
log/
.git/
__pycache__/
*.pyc
.pytest_cache/
.gitignore
```

**`docker/Dockerfile` (minimal):**
```dockerfile
FROM ros:lyrical-ros-base
# If colcon missing: uncomment next line
# RUN apt-get update && apt-get install -y python3-colcon-common-extensions && rm -rf /var/lib/apt/lists/*
WORKDIR /ws
COPY ros2_ws/src /ws/ros2_ws/src
```

**`docker/entrypoint.sh` (optional convenience):**
```bash
#!/usr/bin/env bash
set -euo pipefail
cd /ws/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --packages-select mower_math mower_status
colcon test-result --test-result-base build/mower_math --verbose
colcon test-result --test-result-base build/mower_status --verbose
```
Make executable: `chmod +x docker/entrypoint.sh`.

**Build and test (from repo root):**
```bash
cd ~/mower-sim
docker build -t mower-sim:m0 -f docker/Dockerfile .
# Verify no host artifacts copied
docker run --rm mower-sim:m0 ls /ws/ros2_ws
docker run --rm -t mower-sim:m0 bash -lc "\
  cd /ws/ros2_ws && \
  source /opt/ros/lyrical/setup.bash && \
  colcon build --symlink-install && \
  source install/setup.bash && \
  colcon test --packages-select mower_math mower_status && \
  colcon test-result --test-result-base build/mower_math --verbose && \
  colcon test-result --test-result-base build/mower_status --verbose"
```

Expected tail of verbose results shows the two package summaries with 0 failures, 0 skipped. This satisfies M0 done-when.