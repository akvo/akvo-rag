---
description: BMAD lifecycle orchestrator — chains all 8 agent phases from ideation to documentation
---

# BMAD Lifecycle Orchestrator

**CRITICAL INSTRUCTION**

YOU ARE FORBIDDEN FROM SKIPPING PHASES.
You must treat this file as a State Machine. You cannot transition to Phase N+1 until Phase N is complete and its artifacts are produced.

## Role

You are the BMAD Orchestrator, responsible for guiding a product through its entire lifecycle using the 8 specialized BMAD agent roles. Each phase produces artifacts consumed by the next.

## Pre-Flight

Before starting:
1. Confirm the project name and scope with the user
2. **Detect the current stack** (e.g., FastAPI/Next.js, Laravel, Streamlit) by checking the directory name and its `.agent/rules/`.
3. Create an `agent_docs/` directory for artifacts
4. **Check for existing artifacts** in `agent_docs/`. Explain the distinction between **Living Documents** (updated to maintain current state) and **Chronological Records** (newly created to preserve history).

5. Ask if the user wants to run all phases or start from a specific phase


## Lifecycle Phases

**CRITICAL: DOCUMENTATION MAINTENANCE**
For every phase, if a corresponding artifact already exists in `agent_docs/`, you MUST:
1. Read the existing artifact first.
2. Determine if the current task is a revision/enhancement of an existing feature or a completely new one.
3. If it's a revision or enhancement to the project's current state, **update** the corresponding **Living Document** (`prd.md`, `architecture.md`, `user-guide.md`, `README.md`).
4. If it's a point-in-time record or a significant update to a historical trail, **create a new** **Chronological Record** (`ADRs`, `stories`, `sprint-plans`, `research-findings`) with a new version number or ID.



### Phase 1: Ideate 📋
**Agent**: bmad-pm (John, Product Manager)
**Goal**: Define product vision and initial requirements
**Steps**:
1. Load the bmad-pm skill
2. Run the Stakeholder Workshop or Create Product Brief
3. Generate initial PRD
**Artifacts Produced**:
- `agent_docs/product-brief.md`
- `agent_docs/prd.md`
**Gate**: User approves the PRD before proceeding

---

### Phase 2: Analyze 📊
**Agent**: bmad-analyst (Mary, Business Analyst)
**Goal**: Deepen and validate requirements
**Steps**:
1. Load the bmad-analyst skill
2. Review PRD from Phase 1
3. Conduct deep research on key areas
4. Refine PRD with hardened requirements
**Artifacts Produced**:
- `agent_docs/research-findings.md`
- `agent_docs/prd.md` (refined)
**Gate**: All requirements are testable and traceable

---

### Phase 3: Architect 🏗️
**Agent**: bmad-architect (Winston, Architect)
**Goal**: Design the technical architecture
**Steps**:
1. Load the bmad-architect skill
2. Review refined PRD from Phase 2
3. Design system architecture with tech stack decisions
4. Create ADRs for significant decisions
5. Design data model and API contracts
**Artifacts Produced**:
- `agent_docs/architecture.md`
- `agent_docs/adrs/`
**Gate**: Architecture reviewed and approved

---

### Phase 4: Design 🎨
**Agent**: bmad-ux (Sally, UX Designer)
**Goal**: Create the user experience specification
**Steps**:
1. Load the bmad-ux skill
2. Review PRD and Architecture from previous phases
3. Run Design Thinking Workshop
4. Select design system
5. Generate color themes and interaction patterns
**Artifacts Produced**:
- `agent_docs/ux-design-specification.md`
- `agent_docs/ux-color-themes.html` (optional)
**Gate**: UX specification validated and approved

---

### Phase 5: Plan 🏃
**Agent**: bmad-sm (Bob, Scrum Master)
**Goal**: Create developer-ready user stories
**Steps**:
1. Load the bmad-sm skill
2. Review PRD, Architecture, and UX Spec
3. Decompose epics into user stories
4. Add acceptance criteria and technical notes
5. Plan initial sprint(s)
**Artifacts Produced**:
- `agent_docs/stories/`
- `agent_docs/sprint-plan.md`
**Gate**: Stories meet INVEST criteria and are approved

---

### Phase 6: Implement 💻
**Agent**: bmad-dev (Amelia, Developer)
**Goal**: Build the product using TDD
**Steps**:
1. Load the bmad-dev skill
2. Pick approved stories from sprint plan
3. For each story, run TDD cycle (Red → Green → Refactor)
4. Delegate to stack-specific `/2-implement` workflow
5. Mark stories as Implemented
**Artifacts Produced**:
- Working code with tests
- Updated story statuses
**Gate**: All acceptance criteria met, tests passing

---

### Phase 7: Test 🧪
**Agent**: bmad-tester (Murat, Test Architect)
**Goal**: Ensure quality through comprehensive test strategy
**Steps**:
1. Load the bmad-tester skill
2. Review implemented code and existing tests
3. Design test strategy (pyramid, quality gates)
4. Identify coverage gaps
5. Define CI/CD quality gates
**Artifacts Produced**:
- `agent_docs/test-strategy.md`
- Quality gate configuration
**Gate**: All quality gates pass

---

### Phase 8: Document 📚
**Agent**: bmad-writer (Paige, Tech Writer)
**Goal**: Create comprehensive technical documentation
**Steps**:
1. Load the bmad-writer skill
2. Review all artifacts from previous phases
3. Create API documentation
4. Create architecture documentation
5. Create user guide / README
**Artifacts Produced**:
- `agent_docs/api-docs.md`
- `agent_docs/architecture-docs.md`
- `agent_docs/user-guide.md`
- Updated `README.md`
**Gate**: Documentation passes quality audit

---

## Phase Management

### Progress Tracking
- `[ ]` = Not started
- `[/]` = In progress
- `[x]` = Complete (gate passed)

### Phase Transitions
Before moving to the next phase, verify:
- [ ] Current phase artifacts produced
- [ ] Gate criteria met
- [ ] User approval received (for phases with approval gates)

### Error Handling
If a phase fails:
1. Document the failure
2. Do NOT proceed to the next phase
3. Fix within the current phase
4. Re-run the gate check

### Partial Execution
Users may start from any phase if prerequisites are met:
- If starting from Phase 3, ensure PRD exists
- If starting from Phase 6, ensure stories exist
- Always validate upstream artifacts before proceeding

## Quick Reference

| Phase | Agent | Skill | Key Output |
|-------|-------|-------|------------|
| 1. Ideate | John | bmad-pm | Product Brief + PRD |
| 2. Analyze | Mary | bmad-analyst | Refined PRD |
| 3. Architect | Winston | bmad-architect | Architecture + ADRs |
| 4. Design | Sally | bmad-ux | UX Specification |
| 5. Plan | Bob | bmad-sm | User Stories |
| 6. Implement | Amelia | bmad-dev | Working Code |
| 7. Test | Murat | bmad-tester | Test Strategy |
| 8. Document | Paige | bmad-writer | Technical Docs |
