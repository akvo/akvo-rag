---
name: nextjs-patterns
description: Next.js 14 best practices and patterns. Use when creating pages, components, data fetching, or optimizing the frontend. Covers App Router conventions, RSC boundaries, server actions, error handling, Tailwind CSS patterns, and performance optimization.
---

# Next.js 14 Patterns

## File Conventions

### Special Files (App Router)

| File | Purpose |
|------|---------|
| `page.tsx` | Route page component |
| `layout.tsx` | Shared layout (persists across navigations) |
| `loading.tsx` | Loading UI (Suspense fallback) |
| `error.tsx` | Error boundary for route |
| `not-found.tsx` | 404 UI |
| `template.tsx` | Re-rendered layout |

### Route Segments

| Pattern | Syntax | Example |
|---------|--------|---------|
| Dynamic | `[param]` | `/users/[id]` |
| Catch-all | `[...param]` | `/docs/[...slugs]` |
| Optional catch-all | `[[...param]]` | `/shop/[[...categories]]` |
| Route groups | `(group)` | `/(auth)/login` |

## RSC Boundaries

### Server Components (default)

```tsx
// No directive needed — server by default
export default async function Page() {
  const data = await fetchData()  // Direct async fetch
  return <div>{data.title}</div>
}
```

**Can:** async/await, access backend, read files, use secrets
**Cannot:** hooks, event handlers, browser APIs, state

### Client Components

```tsx
'use client'

import { useState } from 'react'

export default function Counter() {
  const [count, setCount] = useState(0)
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>
}
```

**Rule:** Keep `'use client'` as low in the tree as possible.

### Invalid Patterns

```tsx
// ❌ Async client component (INVALID in React 19)
'use client'
export default async function Page() { ... }

// ❌ Non-serializable props to client components
<ClientComp callback={() => {}} />  // Functions can't serialize
```

## Route Segments (Next.js 14)

In Next.js 14, `params`, `searchParams` are plain objects in Server Components:

```tsx
// ✅ Correct (Next.js 14)
export default function Page({
  params,
}: {
  params: { id: string }
}) {
  const { id } = params
  return <div>{id}</div>
}
```

## Data Fetching

### Server Components (preferred)

```tsx
async function UserPage({ params }: { params: { id: string } }) {
  const { id } = params
  const res = await fetch(`http://backend:8000/api/users/${id}`)
  const user = await res.json()
  return <UserProfile user={user} />
}
```

### Avoid Waterfalls

```tsx
// ❌ Sequential (waterfall)
const user = await fetchUser(id)
const posts = await fetchPosts(id)

// ✅ Parallel
const [user, posts] = await Promise.all([
  fetchUser(id),
  fetchPosts(id),
])
```

### Client-Side Data Fetching

Use SWR or Axios for client components:

```tsx
'use client'
import useSWR from 'swr'
import axios from 'axios'

const fetcher = (url: string) => axios.get(url).then(r => r.data)

function UserList() {
  const { data, error, isLoading } = useSWR('/api/users', fetcher)
  if (isLoading) return <Loading />
  if (error) return <Error error={error} />
  return <ul>{data.map(u => <li key={u.id}>{u.name}</li>)}</ul>
}
```

## Error Handling

```
app/
├── global-error.tsx   # Root error boundary (catches layout errors)
├── error.tsx          # App-level error boundary
├── not-found.tsx      # 404 page
└── users/
    ├── error.tsx      # Route-specific error boundary
    └── not-found.tsx  # Route-specific 404
```

```tsx
// error.tsx
'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={() => reset()}>Try again</button>
    </div>
  )
}
```

## Performance Quick Reference

| Priority | Category | Key Rules |
|----------|----------|-----------|
| CRITICAL | Waterfalls | Use `Promise.all()`, Suspense boundaries |
| CRITICAL | Bundle size | Direct imports (no barrel files), `next/dynamic` |
| HIGH | Server perf | Minimize client component props, parallel fetches |
| MEDIUM | Re-renders | `useMemo`/`useCallback` only when profiling shows need |

## Image & Font Optimization

```tsx
import Image from 'next/image'

// ✅ Always use next/image
<Image src="/photo.jpg" alt="Photo" width={800} height={600} />

// ❌ Never use raw img
<img src="/photo.jpg" />
```

## Tailwind CSS Patterns

### Layout Utilities

```tsx
// Flexbox layout
<div className="flex items-center justify-between gap-4">
  <h1 className="text-2xl font-bold">Title</h1>
  <button className="btn">Action</button>
</div>

// Grid layout
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {items.map(item => <Card key={item.id} {...item} />)}
</div>

// Container with responsive padding
<div className="container mx-auto px-4 sm:px-6 lg:px-8">
```

### Responsive Design (Mobile-First)

**Breakpoint Reference:**
| Prefix | Min Width | Typical Device |
|--------|-----------|----------------|
| (none) | 0px | Small mobile |
| `sm:` | 640px | Large mobile |
| `md:` | 768px | Tablet |
| `lg:` | 1024px | Laptop |
| `xl:` | 1280px | Desktop |
| `2xl:` | 1536px | Large desktop |

```tsx
// Base = mobile, then scale up
<div className="
  text-sm          {/* mobile */}
  md:text-base     {/* tablet */}
  lg:text-lg       {/* desktop */}
">

// Stack → side-by-side
<div className="flex flex-col md:flex-row gap-4">

// Responsive grid
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">

// Auto-fit grid (fluid, no breakpoints needed)
<div className="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-4">

// Hide/show at breakpoints
<nav className="hidden md:flex">        {/* Desktop nav */}
<button className="md:hidden">☰</button> {/* Mobile hamburger */}

// Responsive padding
<div className="px-4 sm:px-6 lg:px-8">

// Responsive spacing
<section className="py-8 md:py-12 lg:py-16">
```

### Responsive Containers & Aspect Ratios

```tsx
// Container with max-width
<div className="container mx-auto px-4">

// Aspect ratio (video, cards, images)
<div className="aspect-video">      {/* 16:9 */}
<div className="aspect-square">     {/* 1:1 */}
<div className="aspect-[4/3]">      {/* 4:3 */}

// Full viewport sections
<section className="min-h-screen flex items-center justify-center">
```

### Responsive Tables

```tsx
// Horizontal scroll on mobile, full table on desktop
<div className="overflow-x-auto">
  <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
    {/* table content */}
  </table>
</div>

// Alternative: card layout on mobile, table on desktop
<div className="hidden md:block">{/* Table view */}</div>
<div className="md:hidden space-y-4">{/* Card view */}</div>
```

### Responsive Forms

```tsx
// Full-width inputs on mobile, side-by-side on desktop
<form className="space-y-4">
  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    <input className="w-full px-3 py-2 border rounded-md min-h-[44px]" />
    <input className="w-full px-3 py-2 border rounded-md min-h-[44px]" />
  </div>
  <button className="w-full md:w-auto px-6 py-2 min-h-[44px]">
    Submit
  </button>
</form>
```

### Dark Mode

```tsx
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
  <p className="text-gray-600 dark:text-gray-400">Subtitle</p>
</div>
```

**Manual Dark Mode Toggle (Tailwind v4):**
```css
/* In your global CSS — replaces tailwind.config.ts darkMode setting */
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));
```
Then toggle the `dark` class on `<html>` via JavaScript/React state + `localStorage`.

### State Variants

```tsx
// Hover, focus, active
<button className="bg-violet-500 hover:bg-violet-600 focus:outline-2
  focus:outline-offset-2 focus:outline-violet-500 active:bg-violet-700" />

// Focus-visible (keyboard-only focus)
<input className="ring-0 focus-visible:ring-2 focus-visible:ring-blue-500" />

// Disabled state
<button disabled className="disabled:opacity-50 disabled:cursor-not-allowed" />

// Group hover — style children when parent is hovered
<a className="group block p-4 hover:bg-sky-50">
  <h3 className="text-gray-900 group-hover:text-sky-600">Project</h3>
  <p className="text-gray-500 group-hover:text-sky-400">Description</p>
</a>

// Named groups for nested hover contexts
<li className="group/item">
  <a className="group/edit invisible group-hover/item:visible">
    <span className="group-hover/edit:text-gray-700">Edit</span>
  </a>
</li>

// List styling
<li className="first:pt-0 last:pb-0">
<tr className="odd:bg-white even:bg-gray-50 dark:odd:bg-gray-900 dark:even:bg-gray-950">
```

### Color Opacity Modifier

```tsx
// Opacity shorthand with /value
<div className="bg-sky-500/20" />      {/* 20% opacity */}
<div className="text-white/75" />      {/* 75% opacity */}
<div className="border-gray-300/25" /> {/* 25% opacity */}
<div className="bg-black/50" />        {/* 50% opacity */}

// Works with all color utilities: bg-*, text-*, border-*, ring-*, shadow-*
```

### Arbitrary Values

```tsx
// One-off values with [] syntax
<div className="bg-[#316ff6]" />            {/* Custom hex color */}
<div className="top-[117px]" />              {/* Exact pixel value */}
<div className="grid-cols-[24rem_2.5rem_minmax(0,1fr)]" />

// CSS variables with () shorthand
<div className="fill-(--my-brand-color)" />  {/* Same as fill-[var(--my-brand-color)] */}

// Combine with variants
<div className="lg:top-[344px] hover:bg-[#1a73e8]" />

// Arbitrary CSS property
<div className="[--gutter-width:1rem] lg:[--gutter-width:2rem]" />
```

### Container Queries

```tsx
// Component-level responsive (based on container width, not viewport)
<div className="@container">
  <div className="flex flex-col @min-md:flex-row @min-md:gap-6">
    <img className="w-full @min-md:w-48" />
    <div className="p-4">Content</div>
  </div>
</div>

// Named containers
<div className="@container/sidebar">
  <div className="@min-sm/sidebar:grid-cols-2" />
</div>
```

### Conditional Classes Pattern

Use `clsx` or a `cn()` helper for conditional Tailwind classes:

```tsx
import { clsx } from 'clsx'

function Button({ variant = 'primary', disabled, children }) {
  return (
    <button
      className={clsx(
        'px-4 py-2 rounded font-medium transition-colors',
        {
          'bg-blue-600 text-white hover:bg-blue-700': variant === 'primary',
          'bg-gray-200 text-gray-800 hover:bg-gray-300': variant === 'secondary',
          'opacity-50 cursor-not-allowed': disabled,
        }
      )}
    >
      {children}
    </button>
  )
}
```

**⚠️ Never construct dynamic class names:**
```tsx
// ❌ WRONG — Tailwind scans files as plain text, can't resolve interpolation
<div className={`bg-${color}-500`} />

// ✅ CORRECT — Map props to complete, static class name strings
const colorVariants = {
  blue: "bg-blue-600 hover:bg-blue-500 text-white",
  red: "bg-red-500 hover:bg-red-400 text-white",
  yellow: "bg-yellow-300 hover:bg-yellow-400 text-black",
}
<div className={colorVariants[color]} />
```

### Tailwind v4 CSS Directives

```css
/* Theme customization — replaces tailwind.config.ts */
@import "tailwindcss";
@theme {
  --font-display: "Satoshi", "sans-serif";
  --color-brand-500: oklch(0.84 0.18 117.33);
  --breakpoint-3xl: 120rem;
}

/* Reusable component classes */
@layer components {
  .card {
    background-color: var(--color-white);
    border-radius: var(--radius-lg);
    padding: --spacing(6);
    box-shadow: var(--shadow-xl);
  }
}

/* Custom utility that works with all variants */
@utility tab-4 {
  tab-size: 4;
}

/* Use @variant in custom CSS */
.my-element {
  background: white;
  @variant dark {
    background: black;
  }
}

/* Register extra source paths for class detection */
@source "../node_modules/@my-company/ui-lib";
```

### Animation Utilities

```tsx
// Transitions
<button className="transition-colors duration-200 hover:bg-blue-700">

// Transform on hover
<div className="transition-transform hover:scale-105">

// Built-in animations
<div className="animate-spin">⟳</div>
<div className="animate-pulse">Loading...</div>
```

## Responsive Testing

**Every page must pass at these widths before merge:**

| Width | What to Check |
|-------|---------------|
| 320px | No overflow, readable text, stacked layout |
| 375px | Standard mobile — touch targets ≥44px |
| 768px | Tablet — grid switches, nav transitions |
| 1024px | Desktop layout fully kicks in |
| 1440px+ | No awkward stretching, max-width containers |

**Common Responsive Bugs to Avoid:**
- Horizontal scrollbar at any breakpoint
- Fixed-width elements that break on mobile
- Text too small to read without zooming
- Buttons/links too close together for touch
- Images overflowing their containers
- Modals/dialogs not fitting mobile viewport

## Metadata

```tsx
// Static metadata
export const metadata = {
  title: 'My Page',
  description: 'Page description',
}

// Dynamic metadata
export function generateMetadata({ params }: { params: { id: string } }) {
  const { id } = params
  return { title: `User ${id}` }
}
```

## Rule Compliance

- NextJS Frontend @nextjs-frontend.md
- Docker Commands @docker-commands.md
- Testing Strategy @testing-strategy.md
