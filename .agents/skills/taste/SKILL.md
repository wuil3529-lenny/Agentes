---
name: taste
description: >-
  Frontend design judgment and anti-slop skill for landing pages, dashboards, web applications,
  and portfolios. Evaluates audience, infers design direction ("Read the Room"), prevents AI-defaults
  (purple gradients, identical feature cards, generic glassmorphism), and sets intentional typography and palettes.
---

# Taste Skill: Anti-Slop Frontend Design Judgment

When creating or redesigning a frontend interface, apply deliberate design judgment rather than AI defaults.

## 0. Brief Inference (Read the Room)
Before writing code, declare a one-line Design Read:
> **"Reading this as: <page kind> for <audience>, with a <vibe> language, leaning toward <aesthetic family>."**

- **B2B SaaS / Developers**: Linear-style, dark minimal, Geist typography, subtle 1px borders, restrained motion.
- **Corporate / Finance / Enterprise**: Trust-first, high density, WCAG AAA contrast, Inter Display + deep navy/slate.
- **Editorial / Culture**: Swiss precision, Instrument Serif + Plus Jakarta, asymmetrical grid, stark whitespace.
- **Modern Brutalist / Web3**: Hard shadows (4px solid), 2px black borders, Cabinet Grotesk + JetBrains Mono.
- **Calm / Humanist**: Soft rounded cards (16-20px radius), warm earth tones, Fraunces serif.

## Anti-Default Discipline
1. **Never default to purple AI gradients** on a dark mesh.
2. **Never default to 3 identical feature cards** with generic icons. Use asymmetrical Bento Grids.
3. **Never overuse glassmorphism** (`backdrop-blur`). Reserve it for navigation bars or floating modals.
4. **Never use flat typography**. Differentiate headings with tight tracking (`tracking-tight`) and intentional fonts.
