---
name: impeccable
description: >-
  Design direction, UX architecture, and quality auditing based on Paul Bakaus's Impeccable system.
  Provides strict surface modes (Operate for dashboards, Persuade for landings, Read for docs),
  detects 60+ anti-patterns, hardens components against edge cases, and distills unnecessary visual noise.
---

# Impeccable Design System (Paul Bakaus Standard)

When designing, auditing, or polishing frontend interfaces, apply Impeccable design direction to reach commercial-grade craft.

## Surface Modes

- **Operate**: Dashboards, admin tools, editors, data tables. Priorities: Scanability, information density, consistency, and zero friction.
- **Persuade**: Landing pages, marketing, campaigns. Priorities: Earning attention, clarity of value proposition, and conversion.
- **Read**: Technical docs, guides, changelogs. Priorities: Reading comfort, 65-75 ch line lengths, and structured hierarchy.
- **Experience**: Showcases, portfolios. Priorities: Immersive visual narrative.

## Core Commands & Actions
1. **craft**: Build the semantic structure from scratch following the surface mode.
2. **critique**: Inspect visual hierarchy: where does the eye land first? Are primary actions unambiguous?
3. **audit**: Check color contrast (WCAG AA min 4.5:1), keyboard focus-visible, and responsiveness.
4. **distill**: Remove unnecessary container borders ("boxes inside boxes"), divider lines, and redundant badges.
5. **harden**: Handle empty states, loading skeletons, and text truncation (`truncate`).
