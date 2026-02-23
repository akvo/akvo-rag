## Rule Priority (When Rules Conflict)

When two rules pull in opposite directions, use this priority to decide:

### Priority Order (Highest to Lowest)

1. **Security Mandate** — always wins. Never compromise security for velocity, simplicity, or convenience.
2. **Docker Commands** — all execution must go through `./dev.sh exec`. No bare commands.
3. **Error Handling** — validation is non-negotiable. Never ship unvalidated code.
4. **Testing Strategy** — testability-first design enables future improvements.
5. **API Design / FastAPI Backend / NextJS Frontend** — context-dependent guidance for the task at hand.
6. **Git Workflow** — commit hygiene and branch conventions.
7. **YAGNI / KISS** — only when no security, reliability, or maintainability trade-off exists.

### Common Conflict Resolutions

| Conflict | Resolution |
|----------|------------|
| YAGNI vs Security ("don't add input validation, it's not needed yet") | **Security wins.** Input validation is always needed. |
| KISS vs Testability ("adding an interface makes it more complex") | **Testability wins.** Interfaces enable testing. |
| Performance vs YAGNI ("should I optimize this now?") | **Measure first.** Only optimize after profiling shows a real bottleneck. |
| DRY vs Clarity ("should I abstract this into a shared utility?") | **Clarity wins** until duplication reaches 3+ instances (Rule of Three). |
| Speed vs Logging ("skip logging to ship faster") | **Logging wins.** Silent failures are the enemy. |

### Guiding Principle

When in doubt, ask: *"Which choice makes the code more defensible and maintainable?"*

If both options are equally defensible, choose the simpler one (KISS).
