# 01 - The status node's names, and the diagnostics-feed question for M6

**Date:** 2026-10-06 · **Milestone:** M0 · **Status:** accepted · **Relates to:** [01-package-layout.md](01-package-layout.md), [01-status-message-type.md](01-status-message-type.md), [review 01](../reviews/01-workspace-and-first-node.md)

## Context

Lesson 01 passed review. The status node is built, tested, and named, and the names are about to become expensive to change: M1 records `ros2 bag` on these topic names, and M7 starts the same package under multiple robot namespaces. Two open ends from the first review need a permanent home, because the review file is not durable across milestones:

1. **The names themselves.** A blocker in the first review was that the lesson contradicted itself on `mower_status` vs `status_node`. The lesson and hints now agree, and the code passes review on both. Left to a per-milestone vote, the question will keep resurfacing.
2. **The diagnostics-feed question.** The message survey ([01-status-message-type.md](01-status-message-type.md)) chose `diagnostic_msgs/DiagnosticStatus` on a node-private topic and never acknowledged the ecosystem's standard shape — `diagnostic_msgs/DiagnosticArray` on a namespaced `/diagnostics`, which `diagnostic_aggregator` and existing dashboards already consume. M6 (command and control, web dashboard) is the first milestone that would want a fleet-wide or aggregate view, so the question has a natural deadline.

## Decision

1. **The M0–M1 names are final.** Package `mower_status`, executable `status_node`, node name `status_node`, private topic `/status_node/diagnostics` (`/<namespace>/status_node/diagnostics` under a robot namespace, verified running two instances concurrently in review 01). Any rename after M1 bags exist invalidates recorded bag topic names; a rename therefore requires a new decision record that writes down the bag-migration cost first.
2. **Keep `DiagnosticStatus` on the node-private topic through M5, and force the aggregate question before M6.** M4's safety state machine publishes per-machine state and M7 polls per-machine status; neither needs an aggregate feed in M0–M5. Before M6's dashboard is built, a new decision record must compare the accepted private `DiagnosticStatus` feed against publishing `diagnostic_msgs/DiagnosticArray` on the namespaced `~/diagnostics`, and must decide whether several mower feeds are aggregated in the fleet manager (MQTT/REST side, per the transport clause in 01-status-message-type.md) rather than on a ROS bus.

## Reasons

- The names are committed in code, lesson, and hints, and passed review; the only earlier argument for a different node name (`mower_status`) was stylistic. Re-opening them is churn across four documents for no new evidence.
- A decision record is the one document AGENTS.md guarantees is read across milestones (append-only, filed in `docs/decisions/`), which is exactly what a far-out-horizon constraint like "decide before M6" needs. The review file is not — it tailors the next lesson only.
- Giving the aggregate question a deadline instead of leaving it as a wish is what "what would change this" sections are for: the failure mode of the accepted document is silent drift.

## Rejected

- **Choosing now** whether M6's dashboard consumes private topics or an aggregated feed. That depends on M5 outcomes (final mower count, what the dashboard must show), and deciding blind would reintroduce the premature-custom-message trap ("one package for the whole robot" / custom `mower_msgs`) that the two earlier records already refused.

## What would change this

- M1 bag recording exposes a collision or discoverability problem with `/status_node/diagnostics` across namespaces → re-open the naming decision with the measured failure as the evidence.
- The fleet manager (M7) proves it needs a ROS-side aggregated diagnostics feed rather than field-level status over MQTT → the pre-M6 decision record takes the `DiagnosticArray` path instead of the private-topic one.
- A future distro deprecates or changes `DiagnosticStatus` → 01-status-message-type.md already has the clause; this record inherits it.