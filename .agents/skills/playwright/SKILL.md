---
name: playwright
description: >-
  Browser automation, visual testing, and end-to-end verification using Playwright and Playwright MCP.
  Use when validating frontend interfaces, checking responsive layouts (desktop and mobile),
  capturing screenshots, detecting console errors, or inspecting accessibility trees.
---

# Playwright & Playwright MCP Browser Verification

When validating, testing, or inspecting live web pages and dashboards, use Playwright to certify that the user experience is flawless.

## Core Capabilities
1. **Responsive Verification**:
   - Desktop (1440x900): Complete grid, expanded navigation, full data tables.
   - Mobile (390x844): Single-column layout, bottom sheets or drawer navigation.
   - **Critical check**: `document.documentElement.scrollWidth <= window.innerWidth` (no horizontal overflow).
2. **Accessibility Snapshots**:
   - Inspect the accessibility tree (`page.accessibility.snapshot()`) to locate elements by semantic role (`button`, `heading`, `link`, `tab`) rather than brittle visual coordinates.
3. **Console & Error Sniffing**:
   - Intercept runtime exceptions with `page.on('console')` and `page.on('pageerror')`.
4. **Visual Evidence**:
   - Take full-page screenshots (`page.screenshot({ fullPage: true })`) to verify final render.
