# SYNETRA hackathon delivery pack

Prepared 18 September 2026 from the official challenge, supplied model discussion and local implementation audit. **This is an execution plan, not a completed benchmark or production certification.**

Start with the [final product plan](FINAL_PRODUCT_PLAN.md). It contains scope, architecture, models, observation workflow, cross-camera association, schema/API design, UI/GenUI, security, owners, deadline gates and submission requirements.

For presentations, use the [analytics workflow overview](ANALYTICS_WORKFLOW_OVERVIEW.md). This Notion-ready Markdown document describes the intended product architecture, including Mermaid diagrams, FastReID cross-camera appearance matching, Qwen investigation assistance, integration, bonus features, and regional scaling. It describes the target design rather than implementation status or benchmark results.

The [feature implementation plan](BONUS_FEATURE_IMPLEMENTATION_PLAN.md) defines the agreed priorities, implementation steps, proposed APIs, data records, owners, and validation for routes, incidents/sharing, sensitive areas, camera health, plate review, and traffic analytics.

Use the [benchmark and operations plan](BENCHMARK_AND_OPERATIONS.md) for release targets, measurement definitions, hardware sizing, replica experiments, simulated-load boundaries, failure drills, deployment and cost inputs.

The [readable backlog](PROJECT_BACKLOG.md) contains 26 cards with owners, dependencies and acceptance checks. [PROJECT_BACKLOG.json](PROJECT_BACKLOG.json) is the structured copy for GitHub Projects. Target repository: [InferiaAI/Synetra](https://github.com/InferiaAI/Synetra).

The hardware path is **local laptop → self-hosted AWS GPU workers → portable departmental deployment**. Local model execution on AWS does not use a hosted intelligence API. No AWS resources have been provisioned.

The internal targets remain **20 September build freeze / 21 September submission**. The [official page](https://sentinel.gujarat.gov.in/problems) currently lists 28 September submission and 12–13 October event dates.

## Reproduce the planning arithmetic

```bash
python3 docs/hackathon/capacity_model.py --cameras 50
python3 docs/hackathon/capacity_model.py --cameras 80000
```

The generated examples are [50-camera assumptions](CAPACITY_50_ASSUMPTIONS.json) and [80,000-camera assumptions](CAPACITY_80000_ASSUMPTIONS.json). They deliberately contain no measured hardware capacity. The calculator requires a measurement-evidence reference before deriving host counts from a supplied stream capacity. Its output remains a projection, not empirical proof.

## Publication state

The local documents and backlog are complete. GitHub repository access is verified; Project publishing is awaiting the separate `project` permission. No completed implementation or performance result is implied by the existence of a Project card.
