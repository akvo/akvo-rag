---
trigger: model_decision
description: When writing or modifying frontend code (Next.js pages, React components, TypeScript, styles)
---

## Next.js Frontend Standards

### Technology Stack

- **Next.js 14** with App Router
- **React 18** with TypeScript (strict mode)
- **Tailwind CSS** for styling (utility-first)
- **Shadcn/UI** for base components
- **pnpm** as package manager (inside container)
- **Axios** for API communication
- **Vercel AI SDK** for RAG streaming

### Code Style

- Use **ESLint** with Next.js configuration
- Use **Prettier** for code formatting
- Run linter: `./dev.sh exec frontend pnpm lint`

### Component Patterns (Shadcn/UI)

We use **Shadcn/UI** as the primary component library. Components are located in `frontend/src/components/ui/`.

```tsx
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function MyComponent() {
  return (
    <div className="flex flex-col gap-4 p-4">
      <Input placeholder="Search..." />
      <Button variant="default">Search</Button>
    </div>
  )
}
```

### Responsive Design (Mandatory)

**Every page and component MUST be responsive.** Port 80 is the default.

- [ ] Works on 320px (small mobile)
- [ ] Works on 768px (tablet)
- [ ] Works on 1024px (desktop)
- [ ] No horizontal scroll at any breakpoint

### Performance Rules

1. **Eliminate waterfalls** — Use `Promise.all()` for independent operations.
2. **Optimize bundle** — Import directly (avoid barrel files).
3. **Server-side perf** — Minimize data in client component props.

### Deployment & Running

- **Development Port**: `80` (mapped to `3000` in some configs, check `.env`)
- **Alternative Port**: `81`
- **Build**: `./dev.sh exec frontend pnpm build`

### Related Rules
- Docker Commands @docker-commands.md
- Testing Strategy @testing-strategy.md
- Security Mandate @security-mandate.md
