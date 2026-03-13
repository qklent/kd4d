# kd4d

PII Masking Proxy — an async FastAPI service that intercepts LLM requests, detects and masks Russian PII before forwarding to the LLM, then restores original values in the response.

## Development

### Prerequisites

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed

### Setup

```bash
cd pii_proxy
pip install -e ".[dev]"
```

### Running tests

```bash
pytest tests/
```

### Running the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9000
```

### Docker

```bash
docker-compose up
```

### Task-driven development

Tasks live in `tasks/` as markdown files. Each task goes through an automated pipeline using Claude Code agents:

1. **Clarify** — `task-clarifier` agent refines raw notes into a detailed spec
2. **Plan** *(optional)* — `planner` agent creates a step-by-step implementation plan
3. **Implement** — `coder` agent writes the code following the spec

#### Creating a task

Add a markdown file to `tasks/` using this template:

```markdown
# Task title

## Raw Notes

Your rough description of what needs to be done.

## Refined Spec

<!-- Filled by task-clarifier agent -->

## Acceptance Criteria

<!-- Filled by task-clarifier agent -->

## Implementation Plan

<!-- Filled by planner agent -->

## Status

- [ ] Clarified
- [ ] Planned
- [ ] Implemented
```

#### Running a task

```bash
# Random task, 2 steps (clarify → code)
./run_task.sh

# Specific task
./run_task.sh 001-example-task.md

# With planning step (clarify → plan → code)
./run_task.sh --plan

# Specific task with planning
./run_task.sh --plan 001-example-task.md
```
