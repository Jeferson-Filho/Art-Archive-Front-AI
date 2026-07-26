# Functional and Non-Functional Requirements — Art Archive AI

## Conventions

- **RF-XXX** — Functional requirement
- **RNF-XXX** — Non-functional requirement
- Full descriptions and Gherkin scenarios for each requirement live in the block documents, this document only indexes titles and cross-requirement relations.

---

## Functional Requirements

### Block 1 — Insight Card

- RF-001 — Triggering Insight Card generation and existence check
- RF-002 — Generation of the historical context block
- RF-003 — Generation of the comparative analysis block
- RF-004 — Persisting the generated content after the first generation
- RF-005 — Displaying the Insight Card on the detail page
- RF-006 — Insight Card loading state
- RF-007 — Insight Card error state
- RF-008 — AI-generated content disclosure
- RF-009 — Open web search as an LLM capability
- RF-010 — Returning sources used for the generated text

### Block 2 — Alt Text

- RF-011 — Alt Text generation via LLM
- RF-012 — Applying the Alt Text to the artwork's image
- RF-013 — Independent generation of the Alt Text

### Block 3 — Screen Reader Support / ARIA

- RF-014 — ARIA label on the Insight Card
- RF-015 — ARIA live region for loading and error states
- RF-016 — Accessible identification of the AI-disclosure notice
- RF-017 — Accessible sources list
- RF-018 — Semantic landmarks and page structure
- RF-019 — Accessible names for icon-only controls
- RF-020 — Semantic interactive elements and keyboard operability
- RF-021 — Dialog semantics and focus management for modal/overlay UI
- RF-022 — Custom dropdown/listbox ARIA pattern
- RF-023 — Form labeling and error announcement
- RF-024 — Sitewide keyboard navigation and visible focus
- RF-025 — Accessible error/empty/404 states

### Block 4 — Authentication

- RF-026 — User authentication via email and password
- RF-027 — Account creation
- RF-028 — Logout
- RF-029 — Password recovery request (Forgot Password)
- RF-030 — Setting a new password (Change Password)
- RF-031 — Session persistence

---

## Non-Functional Requirements

- RNF-001 — Response time for already-persisted content
- RNF-002 — Maximum generation time (first visit)
- RNF-003 — Persistence reliability
- RNF-004 — Compliance with WCAG 2.1 level AA across the platform
- RNF-005 — API credential security
- RNF-006 — Prompt versioning
- RNF-007 — Loading state usability
- RNF-008 — Degraded availability without AI

---

## Relationships Between Requirements

### RF ↔ RF

- RF-004 → RF-001, RF-002, RF-003
- RF-007 → RF-002, RF-003, RF-005, RF-010
- RF-009 → RF-002, RF-003, RF-010
- RF-010 → RF-005
- RF-012 → RF-011, RF-013
- RF-013 → RF-011, RF-012
- RF-014 → RF-005
- RF-015 → RF-006, RF-007
- RF-016 → RF-008, RF-014
- RF-017 → RF-010
- RF-022 → RF-020
- RF-023 → RF-026, RF-027
- RF-030 → RF-029

### RNF ↔ RF

- RNF-001 → RF-001, RF-004, RF-012, RF-013
- RNF-002 → RF-001, RF-002, RF-003, RF-011, RF-013
- RNF-003 → RF-004, RF-013
- RNF-004 → RF-014 until RF-025
- RNF-005 → _(none)_
- RNF-006 → RF-002, RF-003, RF-011
- RNF-007 → RF-006
- RNF-008 → RF-007
