# Tailwind CSS v4 & shadcn/ui Design Tokens Guide

## ⚠️ The single most important rule in this file

Tailwind v4's CSS-first config only turns a custom property into a real utility
class (`bg-primary`, `text-muted-foreground`, `rounded-lg`, ...) when that
property is registered inside an `@theme` block. A `:root { --primary: ...; }`
declaration **outside** `@theme` compiles with zero errors, zero warnings —
and silently produces no `.bg-primary` rule at all. Every component that uses
it renders unstyled: no background, no border, no accent color. This shipped
undetected in this skill's own scaffold for its first two releases; the entire
color system was inert (font, layout, and spacing utilities still worked,
which is why it wasn't obviously broken — it just looked flat and generic).

**Verify it after every change to `index.css`:**

```bash
npm run build
grep -c '\.bg-primary\b' dist/client/assets/*.css   # must be > 0
grep -c '\.bg-card\b' dist/client/assets/*.css      # must be > 0
```

Zero means the `@theme` block is missing, misspelled, or the custom
properties it references don't exist. This is Phase 1's baseline check in
SKILL.md — never skip it.

---

## Tailwind CSS v4 Architecture

Tokens live in `client/src/index.css`. There are three parts, and all three
are required:

1. **`@theme inline { ... }`** — maps each semantic token to Tailwind's
   `--color-*` / `--radius-*` namespace, which is what actually generates the
   utility classes. `inline` (not plain `@theme`) is required here because
   these map to *other* custom properties (`var(--primary)`), not literal
   values — Tailwind only resolves `var()` references at this point when the
   block is marked `inline`.
2. **`:root { ... }` / `.dark { ... }`** — the actual color values, one
   declaration per token, swapped by the `.dark` class that `App.tsx` toggles
   on `<html>`.
3. **`@layer base { ... }`** — a handful of plain CSS rules (`body` font/bg/fg,
   global `border-color`) that reference the tokens directly via `var()`, not
   through Tailwind utilities.

```css
/* client/src/index.css */
@import "tailwindcss";

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);

  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}

:root {
  --radius: 0.75rem;

  --background: oklch(1 0 0);
  --foreground: oklch(0.16 0.014 264.2);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.16 0.014 264.2);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.16 0.014 264.2);
  --primary: oklch(0.546 0.226 264.4);
  --primary-foreground: oklch(0.98 0.005 264);
  --secondary: oklch(0.965 0.004 264.5);
  --secondary-foreground: oklch(0.24 0.02 264.4);
  --muted: oklch(0.965 0.004 264.5);
  --muted-foreground: oklch(0.51 0.018 264.4);
  --accent: oklch(0.95 0.02 264.4);
  --accent-foreground: oklch(0.24 0.02 264.4);
  --destructive: oklch(0.58 0.22 27.3);
  --destructive-foreground: oklch(0.98 0.005 264);
  --border: oklch(0.91 0.006 264.5);
  --input: oklch(0.91 0.006 264.5);
  --ring: oklch(0.546 0.226 264.4);
}

.dark {
  --background: oklch(0.16 0.012 264.2);
  --foreground: oklch(0.97 0.004 264.5);
  --card: oklch(0.205 0.013 264.4);
  --card-foreground: oklch(0.97 0.004 264.5);
  --popover: oklch(0.205 0.013 264.4);
  --popover-foreground: oklch(0.97 0.004 264.5);
  --primary: oklch(0.685 0.19 264.4);
  --primary-foreground: oklch(0.16 0.012 264.2);
  --secondary: oklch(0.27 0.014 264.4);
  --secondary-foreground: oklch(0.97 0.004 264.5);
  --muted: oklch(0.27 0.014 264.4);
  --muted-foreground: oklch(0.66 0.014 264.4);
  --accent: oklch(0.3 0.03 264.4);
  --accent-foreground: oklch(0.97 0.004 264.5);
  --destructive: oklch(0.65 0.2 25);
  --destructive-foreground: oklch(0.97 0.004 264.5);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(0.685 0.19 264.4);
}
```

**Why OKLCH, not HSL:** perceptually-uniform lightness across hues (an
`L 0.55` primary and an `L 0.55` destructive read as the same visual weight,
which HSL doesn't guarantee), a wider gamut, and it's what current shadcn/ui
v4 themes ship natively. The hue `264.4` throughout is a deliberate
indigo-violet accent — change it (and only it) to re-brand the whole palette
without breaking contrast relationships between tokens.

**Radius:** `--radius: 0.75rem` (not the old shadcn default `0.5rem`) is a
deliberate choice — the softer, more generous corner radius reads as
contemporary (Linear/Vercel/Notion-adjacent) rather than the sharper-cornered
2022-era default. Every `rounded-md`/`rounded-lg`/`rounded-xl` in every
component automatically follows this because of the `--radius-*` mappings in
`@theme inline` — don't hardcode radius values in component files.

---

## Radix UI & CVA Component Pattern

Components are code-owned in `client/src/components/ui/` and styled with `class-variance-authority` (cva) and `tailwind-merge`:

```tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

export const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background cursor-pointer select-none',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'underline-offset-4 hover:underline text-primary',
      },
      size: {
        default: 'h-10 py-2 px-4',
        sm: 'h-9 px-3 rounded-md text-xs',
        lg: 'h-11 px-8 rounded-md text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);
```

---

## Theming Guidelines

1. **Light/Dark Synchrony**: Always verify elements render legibly in both `.dark` and root themes.
2. **Semantic Classes**: Never hardcode colors like `bg-[#0070F3]`. Use `bg-primary`, `bg-card`, `text-muted-foreground`, etc.
3. **Smooth Transitions**: Apply `transition-colors` on interactive surfaces.
4. **Prefer canonical Tailwind classes over arbitrary values**: `w-17` not `w-[68px]`, `h-4.5` not `h-[18px]`, `bg-linear-to-tr` not `bg-gradient-to-tr`. If your IDE flags a `suggestCanonicalClasses` warning, apply it — v4 has fractional spacing (`4.5` = 18px) and renamed gradient utilities that make most arbitrary-value escapes unnecessary.
5. **A stat tile / metric card is a single flat `CardContent`, not a `CardHeader` + `CardContent` split**: label + value on the left, a `size-10 rounded-full` tinted icon badge (`bg-<color>/10 text-<color>`) on the right. This is the modern pattern (Linear/Vercel-style dashboards) — a bare label-over-number with a plain gray icon reads as dated.
6. **A hero section benefits from one subtle background glow**, not a busy image: an absolutely-positioned, `blur-3xl`, `opacity-60`, `bg-primary/30`-to-transparent radial shape behind the heading, `pointer-events-none` and `aria-hidden`. Keep it faint — it should be felt, not seen directly.

---

## Sidebar collapse (client/src/lib/state.ts)

Desktop collapse (`sidebarOpen`, icon-rail vs. full width) and the mobile
drawer overlay (`mobileNavOpen`) are **separate** boolean fields in the auth
store, not one shared flag. Conflating them means either the sidebar starts
as a blocking overlay on mobile on first load, or there's no way to collapse
it on desktop without also hiding it on mobile. `Sidebar.tsx` owns the
collapse toggle button (bottom of the rail, `PanelLeftClose`/`PanelLeftOpen`,
`hidden md:flex` — desktop only); `Navbar.tsx` owns the mobile hamburger
(`Menu`/`X`, `md:hidden`). Both write to the same store; neither reads the
other's field.
