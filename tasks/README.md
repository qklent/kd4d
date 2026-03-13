# Tasks

Drop markdown files here following this template:

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

Run tasks with: `./run_task.sh [task-file]`

- No argument: picks a random uncompleted task
- With argument: runs the specified task file (path relative to `tasks/`)
