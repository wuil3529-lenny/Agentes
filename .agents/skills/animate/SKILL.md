---
name: animate
description: >-
  Build an animation from scratch or integrate rich UI motion into web pages, dashboards,
  and applications based on Emil Kowalski's animation philosophy. Determines proper frequency
  gates, easing curves, hardware-accelerated transforms, spring physics, layout animations,
  and accessible reduced-motion states.
---

# Building Animations (Emil Kowalski Philosophy)

When asked to animate something, add motion, build a dashboard transition, or make a component feel alive, follow Emil Kowalski's strict craft standards.

## Operating Posture

You are a senior design engineer building purposeful animations. The bar is Emil Kowalski's animation philosophy:
1. Never animate something that shouldn't animate (keyboard shortcuts, high-frequency toggles).
2. Never animate the right thing with the wrong ingredients (no `scale(0)`, no `ease-in` on UI entry, no `transition: all`, no durations over 300ms).

## The Build Sequence

### 1. Should this animate at all?
- **100+ times/day** (keyboard shortcuts, command palette toggle): **No animation. Ever.** Instant state change.
- **Tens of times/day** (hover effects, list navigation): Near-imperceptible (< 150ms), subtle, or nothing.
- **Occasional** (modals, drawers, toasts, dropdowns): Standard animation (150–250ms).
- **Rare / First-time** (onboarding, success celebration): The delight budget lives here.

### 2. What is the purpose?
Must be one of:
- **Feedback** — confirming the interface heard the user.
- **Spatial consistency** — showing where something came from or went.
- **State indication** — making a state change legible.
- **Preventing a jarring change** — bridging content that would otherwise teleport.
- **Explanation** — demonstrating how something works (marketing/onboarding).
- **Delight** — allowed *only* at the rare/first-time tier.

### 3. Tool Selection
- **CSS Transitions**: Hover, press, color, state toggle with class/attribute.
- **CSS `@starting-style`**: Entry animation on mount without JS state.
- **CSS Animations**: Predetermined motion that must run off the main thread under load.
- **WAAPI (`element.animate()`)**: Programmatic control with CSS performance.
- **Motion (`motion.dev` / `framer-motion`)**: Springs, layout animations, exit animations (`AnimatePresence`), gesture-driven drag.

### 4. Properties (GPU Accelerated Only)
- **`transform` and `opacity` only.** Skip layout and repaint.
- **Never `scale(0)`.** Start from `scale(0.95)` + `opacity: 0`.
- **`transform-origin` at the trigger** for dropdowns, popovers, tooltips. Modals stay centered.
- **Motion transforms**: Use full transform string (`transform: "translateY(...) scale(...)"`) to avoid dropped frames.

### 5. Easing and Duration
```css
:root {
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);     /* strong ease-out for UI entries */
  --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1); /* strong ease-in-out for movement */
  --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);  /* iOS-like drawer curve */
}
```
- **UI Duration**: Keep under 300ms (120ms button press, 150ms tooltip, 180ms dropdown, 220ms modal, 300ms drawer).
- **Springs**: `{ type: "spring", duration: 0.5, bounce: 0.2 }` for Apple-like fluid feel.

### 6. Accessibility & Pointer Gating
Always ship with the animation:
```css
@media (prefers-reduced-motion: reduce) {
  .element { transition: opacity 0.15s ease !important; transform: none !important; }
}

@media (hover: hover) and (pointer: fine) {
  .element:hover { transform: translateY(-1px); }
}
```

## Never Ship Checklist
- [x] No `transition: all` (name specific properties).
- [x] No `scale(0)` (use `scale(0.95)`).
- [x] No `ease-in` on UI entry.
- [x] No animating `width`, `height`, `top`, `left`, `margin`, `padding`.
- [x] No duration > 300ms on UI controls.
- [x] Always include `prefers-reduced-motion`.
