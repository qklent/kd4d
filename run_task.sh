#!/usr/bin/env bash
set -euo pipefail

TASKS_DIR="$(cd "$(dirname "$0")/tasks" && pwd)"
USE_PLANNER=false

# Parse flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --plan)
            USE_PLANNER=true
            shift
            ;;
        -*)
            echo "Unknown flag: $1"
            echo "Usage: ./run_task.sh [--plan] [task-file]"
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# Pick task file: from argument or random
if [[ $# -ge 1 ]]; then
    TASK_FILE="$TASKS_DIR/$1"
    if [[ ! -f "$TASK_FILE" ]]; then
        echo "Error: task file not found: $TASK_FILE"
        exit 1
    fi
else
    # Pick a random .md task file (excluding README)
    mapfile -t candidates < <(find "$TASKS_DIR" -maxdepth 1 -name '*.md' ! -name 'README.md' | shuf)
    if [[ ${#candidates[@]} -eq 0 ]]; then
        echo "No task files found in $TASKS_DIR"
        exit 1
    fi
    TASK_FILE="${candidates[0]}"
fi

TASK_NAME="$(basename "$TASK_FILE")"
echo "=== Running task: $TASK_NAME ==="
echo ""

# Step 1: Clarify
echo "--- Step 1: Clarifying task with task-clarifier agent ---"
claude "/clarify-task $TASK_FILE"

# Step 2 (optional): Plan
if [[ "$USE_PLANNER" == true ]]; then
    echo ""
    echo "--- Step 2: Planning implementation with planner agent ---"
    claude --agent planner \
        -p "Create a detailed implementation plan for the task in $TASK_FILE. Read CLAUDE.md first, then read the full task file including the refined spec. Write the plan into the Implementation Plan section." \
        --allowedTools "Read,Grep,Glob,Edit,Write"
fi

# Step 3: Implement
echo ""
STEP_NUM=$( [[ "$USE_PLANNER" == true ]] && echo "3" || echo "2" )
echo "--- Step $STEP_NUM: Implementing task with coder agent ---"
claude --agent coder \
    -p "Implement the task described in $TASK_FILE. Read CLAUDE.md first, then read the full task file including the refined spec. Follow the spec and implement it step by step." \
    --allowedTools "Read,Write,Edit,Bash,Grep,Glob"

echo ""
echo "=== Task $TASK_NAME complete ==="
