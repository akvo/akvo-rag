---
name: add-stack
description: Step-by-step guide for adding a new fullstack tech stack to the repo. Use when creating a new stack directory with rules, skills, and workflows.
---

# Add Stack Skill

## Overview

Guide for adding a new fullstack tech stack skeleton to the current repo.

## Steps

### 1. Research the Stack

Before creating files, research:
- The stack's conventions and idioms (check official documentation)
- Docker/container setup for the stack
- Testing frameworks and conventions
- Security best practices specific to the stack
- Skill discovery resources:
    - [Anthropic Skills](https://github.com/anthropics/skills)
    - [Awesome AGV](https://github.com/wayangalihpratama/awesome-agv)
    - [Skills.sh](https://github.com/skills/skills.sh)
- **BMAD Integration**: Use `bmad-architect` and `bmad-analyst` roles to validate the stack's fit and requirements.

### 2. Create the Directory

```bash
mkdir -p <stack-name>/.agent/{rules,skills,workflows}
```

### 3. Create Core Rules

Adapt the following from the `fastapi-nextjs` reference:

| File | Adapt From | What to Change |
|------|-----------|----------------|
| `rule-priority.md` | `fastapi-nextjs` | Update stack-specific rule names |
| `security-mandate.md` | `fastapi-nextjs` | Adapt framework-specific security patterns |
| `docker-commands.md` | Create new | Stack's Docker commands and service URLs |
| `error-handling.md` | `fastapi-nextjs` | Framework-specific error patterns |
| `testing-strategy.md` | `fastapi-nextjs` | Stack's test runners and conventions |
| `git-workflow.md` | Copy as-is | Usually stack-agnostic |

Then add stack-specific rules (e.g., `laravel-backend.md`, `vue-frontend.md`).

### 4. Create Core Skills

| Skill | Purpose |
|-------|---------|
| `debugging-protocol/SKILL.md` | Adapt commands for the stack's Docker setup |
| `guardrails/SKILL.md` | Adapt checklists for the stack's tools |
| Stack CRUD skill | Framework-specific resource creation guide |
| Stack patterns skill | Framework best practices |

### 5. Create Workflows

Copy workflow structure from `fastapi-nextjs/.agent/workflows/` and adapt:
- Research, Implement, Integrate, Verify, Commit phases
- Stack-specific commands and file paths

### 6. Adapt and Localize [CRITICAL]

When sourcing rules, skills, or workflows from external repositories:
- **Rename Commands**: Replace generic `python`, `node`, `yarn` with stack-specific Docker wrappers (e.g., `./dc.sh exec backend`).
- **Adjust Paths**: Update directory structures to match the local repo.
- **Update References**: Ensure `@filename.md` links point to existing files within the new stack.
- **Localize Examples**: Change variable names and examples to be relevant to the specific framework.

### 7. Update Root README

Add the new stack to the "Available Stacks" table in the root `README.md`.

### 8. Verify

- [ ] All SKILL.md files have valid frontmatter
- [ ] All rules have correct trigger values
- [ ] All commands use Docker wrappers
- [ ] Cross-references are consistent
- [ ] Root README updated

## Rule Compliance

- Repo Structure @repo-structure.md
- Stack Creation @stack-creation.md
