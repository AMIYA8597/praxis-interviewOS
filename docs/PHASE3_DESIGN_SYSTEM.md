# PRAXIS InterviewOS — Phase 3 Design System & Component Library

**Milestone**: Phase 3 — Web & Desktop Client Engineering  
**Branch**: `phase3-web-desktop`  
**Date**: 2026-11-01  
**Classification**: DESIGN SPECIFICATION  

---

## 1. Visual Identity & Design Principles

The PRAXIS design system provides a focused, accessible, and high-performance visual language designed for intense technical interview practice.

### Core Principles:
- **Clarity Under Stress**: High legibility, dark-mode first, zero unnecessary visual clutter.
- **Evidence-First Color Coding**: Semantic colors directly signify verification confidence and grounded status.
- **Zero Simulation / Transparent Indicators**: Explicit status badges indicating whether data is `MEASURED`, `ESTIMATED`, `DEGRADED`, or `UNAVAILABLE`.
- **Accessibility by Default**: Strict adherence to WCAG 2.1 AA standards for contrast, keyboard focus, and screen-reader semantics.

---

## 2. Design Tokens

### 2.1 Palette & Semantic Mapping
| Token | Light Value | Dark Value | Usage |
| :--- | :--- | :--- | :--- |
| `bg-canvas` | `#ffffff` | `#09090b` (`zinc-950`) | Primary application surface |
| `bg-card` | `#f4f4f5` | `#18181b` (`zinc-900`) | Containers, cards, dialogs |
| `border-subtle` | `#e4e4e7` | `#27272a` (`zinc-800`) | Dividers, card borders |
| `text-primary` | `#09090b` | `#fafafa` (`zinc-50`) | Headings, primary text |
| `text-muted` | `#71717a` | `#a1a1aa` (`zinc-400`) | Helper text, secondary metrics |
| `brand-primary` | `#4f46e5` | `#6366f1` (`indigo-500`) | Primary buttons, active tabs |
| `status-verified` | `#059669` | `#10b981` (`emerald-500`)| Supported claim, optimal metric |
| `status-warning` | `#d97706` | `#f59e0b` (`amber-500`)  | Partially supported, filler warning |
| `status-danger` | `#dc2626` | `#ef4444` (`rose-500`)   | Contradicted claim, critical error |

### 2.2 Typography
- **Primary Sans**: Inter / system-ui (`sans-serif`) for crisp UI rendering.
- **Monospace**: JetBrains Mono / Fira Code (`font-mono`) for timings, WPM, tokens, and code snippets.
- **Serif Excerpt**: Georgia / serif (`font-serif`) for quoted document excerpts in evidence grounding.

---

## 3. Shared Component Library Inventory (`packages/ui`)

1. **`EvidenceReference`**:
   - Visualizes candidate spoken claims grounded against documents.
   - Five distinct classification styles:
     - `SUPPORTED`: Emerald green border & badge ("Verified Fact").
     - `PARTIALLY_SUPPORTED`: Amber yellow border & badge ("Partially Supported").
     - `UNSUPPORTED`: Neutral slate border & badge ("Unverified").
     - `CONTRADICTED`: Rose red border & badge ("Contradicted").
     - `UNCERTAIN`: Indigo border & badge ("Needs Clarification").
   - Expandable source citation accordion disclosing source chunk and original document excerpt.

2. **`ScoreDisplay`**:
   - Renders 6 evaluation dimensions: Relevance, Technical Correctness, Structure, Specificity, Evidence Grounding, Conciseness.
   - Renders overall score and evaluator rationale.
   - Transparently handles `measurement_status` (`MEASURED`, `ESTIMATED`, `DEGRADED`, `UNAVAILABLE`).
   - Visualizes STAR completeness (Situation, Task, Action, Result) with clear status tags.

3. **`ReadinessCard`**:
   - Presents calibrated multi-session PRAXIS Readiness Estimate.
   - Prominently displays mandatory preparatory disclaimer:
     *"PRAXIS Readiness Estimate is a calibrated preparatory indicator, not an employment guarantee."*
   - Displays `INSUFFICIENT_EVIDENCE` fallback when session count is zero, prompting candidate to practice.

4. **`AudioControl`**:
   - Audio input device dropdown with real device enumeration.
   - Visual volume meter with dynamic level animation.
   - Mute/unmute toggles and permission error handling with retry capability.

5. **Fundamental Primitives**:
   - `Button`, `Input`, `Modal`, `Card`, `Badge`, `Table`, `Tabs`, `Spinner`, `Skeleton`, `MetricsDisplay`, `TranscriptDisplay`, `CoachingFeedback`, `HintCard`.
