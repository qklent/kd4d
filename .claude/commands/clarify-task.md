---
description: Refine a raw task into a detailed spec through Q&A
---
Read the task file at: $ARGUMENTS

Use the task-clarifier agent to analyze this task.
Read CLAUDE.md first for project context, then read the task file.
Ask me 3-7 clarifying questions about the task — wait for my answers before proceeding.
After I've answered all questions, produce the refined spec and update the task file with:
- Refined Spec section
- Acceptance Criteria section (as checkboxes)
- Files likely to be modified/created
- Test scenarios to cover
