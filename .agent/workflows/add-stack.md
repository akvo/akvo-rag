---
description: How to add a new tech stack to the repository
---

# Add New Tech Stack Workflow

Follow these steps to add a new self-contained tech stack to the repo.

## 1. Research & Discovery
1. Identify the stack (e.g., Django/React, Rails).
2. Use `bmad-architect` to design the directory structure and Docker setup.
3. Search for existing skills/rules in:
   - [Anthropic Skills](https://github.com/anthropics/skills)
   - [Awesome AGV](https://github.com/wayangalihpratama/awesome-agv)

## 2. Initialize Structure
1. Create the stack directory: `mkdir -p <stack-name>/.agent/{rules,skills,workflows}`.
2. Initialize Docker configuration (Dockerfile, docker-compose.yml, wrapper script).

## 3. Populate Rules
1. Create mandatory rules: `rule-priority.md`, `security-mandate.md`, `docker-commands.md`.
2. Adapt framework-specific rules (e.g., `error-handling.md`, `testing-strategy.md`).
3. **CRITICAL**: Adapt all commands to use the Docker wrapper.

## 4. Populate Skills
1. Create mandatory skills: `debugging-protocol`, `guardrails`.
2. Create stack-specific patterns and CRUD skills.

## 5. Populate Workflows
1. Create standard workflows: `1-research`, `2-implement`, `3-integrate`, `4-verify`, `5-commit`.
2. Adjust commands and paths to match the stack.

## 6. Integration & Verification
1. Add the stack to the root `README.md`.
2. Run a "smoke test" using the new `1-research` workflow.
3. Fix any broken cross-references (@links).
