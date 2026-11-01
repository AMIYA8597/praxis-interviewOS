# PRAXIS InterviewOS — Phase 3 Accessibility & WCAG 2.1 AA Compliance

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: ACCESSIBILITY SPECIFICATION & AUDIT  

---

## 1. Compliance Standards

PRAXIS web and desktop applications conform to **WCAG 2.1 Level AA** standards.

---

## 2. Accessibility Engineering Details

### 2.1 Contrast & Readability (WCAG 1.4.3)
- Background (`#09090b`) to primary text (`#fafafa`) contrast ratio: **18.2:1** (exceeds 4.5:1 requirement).
- Muted helper text (`#a1a1aa`) to card background (`#18181b`) contrast ratio: **5.8:1** (exceeds 4.5:1 requirement).
- Verification badges utilize high-contrast borders and foreground tones for both light and dark modes.

### 2.2 Screen Reader Support (WCAG 4.1.2)
- All interactive controls have accessible names (`aria-label`, `title`, or explicit text).
- Accordions (`EvidenceReference`) toggle `aria-expanded` and convey state transitions.
- Progress bars (`AudioControl` volume meter, `ScoreDisplay` bars) declare `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, and `aria-valuemax`.
- Realtime transcript updates use semantic live regions where appropriate.

### 2.3 Keyboard Navigation (WCAG 2.1.1 & 2.4.7)
- Full tab sequence across navigation, modals, device selectors, and action buttons.
- Visible, high-contrast focus rings (`focus:ring-2 focus:ring-indigo-500 focus:outline-none`).
- Esc key dismisses open modals.
- Enter/Space triggers buttons and accordion toggles.

### 2.4 Degraded & Text Mode Accessibility
- For candidates with speech impairments or lacking functional audio devices, the practice arena provides a fully accessible text-input fallback (`candidate.text_answer`) allowing complete participation in practice sessions.
