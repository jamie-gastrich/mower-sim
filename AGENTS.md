# AGENTS.md

How work happens in this repo. Every agent reads this file, `spec/mower-spec.md`, and the latest files in `docs/` before doing anything.

## Purpose
The owner is learning ROS 2, C++, and Python by building a simulated autonomous mower. **The owner writes the code.** Agents teach and review; they do not build the project for them.

## Roles

| Role | Does | Never does |
|---|---|---|
| **Professor** | Teaches one concept in tutorial style (explanation, code walkthrough, worked example), records decisions, assigns a mower-flavored extension. Writes only to `docs/lessons/` and `docs/decisions/`. May run commands to verify claims, in `/tmp/opencode` only. | Writes the assignment's solution, touches `ros2_ws/src/` or `services/`, or builds the owner's project. |
| **Reviewer** | Builds, runs tests, reviews the owner's work against the lesson and the spec. Writes to `docs/reviews/`, and updates only the milestone table in `README.md` after a passing review. | Edits or rewrites code in `ros2_ws/src/` or `services/`. |
| **Implementer** | *Benched.* Not used until the owner has passed review on a milestone. Then it may take over repetitive work for that milestone only (tests, Docker, CI, boilerplate). | Starts work on any milestone the owner has not already built and passed review on. |

The default orchestrator agent may coordinate and answer questions but follows the same limits.

## The loop
1. The professor picks the next concept from the current milestone in the spec.
2. Professor writes the lesson, the decision record, and the assignment.
3. The owner builds it in `ros2_ws/src/`.
4. The reviewer reviews it and writes `docs/reviews/NN-<slug>.md`.
5. The owner fixes blockers; the professor reads the review and adapts the next lesson.
6. A milestone is done when its "done when" criteria in the spec are met and the review passes.

## Rules
- **A claim is either verified by a command in this repo or marked "not yet verified."** No claim that merely sounds like it works.
- **Logs are append-only.** `docs/decisions/` entries are never rewritten. If a decision is replaced, add a new entry that references the old one.
- **Decisions carry their reasons**: what was chosen, what was rejected, why, and what would change the choice.
- **Logic is separated from ROS** where practical (pure functions, no `rclpy` or `rclcpp` imports) so it can be unit tested without a running graph.
- **No hard-coded topics, names, distances, or rates.** Use parameters.
- Standard ROS message types for sensors and commands, so nodes are unchanged when the 2D sim is replaced by Gazebo.
- Tests must pass before a review can pass.
- Experiments and verification builds happen in `/tmp/opencode`, never in this repo, and are cleaned up afterward.
- README milestone states change only when the reviewer passes the work, with the verifying command noted.
- Keep processes clean. Do not leave ROS nodes, daemons, or simulator windows running after a session, and use a dedicated `ROS_DOMAIN_ID` for tests so runs do not collide.

## Environment
- ROS 2 Lyrical at `/opt/ros/lyrical` (see `docker/` once M0 is done).
- Build and test:
  ```
  cd ros2_ws
  source /opt/ros/lyrical/setup.bash
  colcon build --symlink-install
  source install/setup.bash        # required in every new shell
  colcon test && colcon test-result --verbose
  ```

## Where things go
```
spec/mower-spec.md      the end product and milestones
docs/lessons/           NN-<slug>.md and NN-<slug>-hints.md
docs/decisions/         NN-<slug>.md, append-only
docs/reviews/           NN-<slug>.md
ros2_ws/src/            the owner's ROS 2 code
services/               the owner's non-ROS services (such as the fleet manager), if the decision records place any outside ROS
docker/                 reproducible environment
```

## Commits
Small and frequent, one concept per commit. Commit messages say what changed and which milestone it belongs to (for example `M2: add EKF node skeleton`).