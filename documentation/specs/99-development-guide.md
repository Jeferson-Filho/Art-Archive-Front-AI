# Development Guide — Art Archive AI

**Version:** 1.0
**Date:** 2026-07-02
**Status:** Living document — updated continuously during development
**Base documents:** [01 — Vision and Scope](./01-vision-scope.md), [02 — Requirements](./02-requirements.md)

---

## How to Use This Document

This document is not a functionality specification — it is an operational guide to orient the implementation order. It translates the requirements (doc 02) into a practical execution plan, organized so that no step is left blocked waiting on an artifact, document, or infrastructure that does not yet exist.

Each checklist item references, where applicable, the FR/NFR it implements (doc 02) and the specification document it depends on (doc 03–19). Items without a prior specification must not be started — the corresponding specification must be written first.

This document will be revised as documents 03 to 19 are created. Structural updates (change of phases, new blocks) will be proposed to the user before being applied.

---

## 1. Functionality Blocks

| Block | Name                                                   | Related FRs/NFRs                                 |
| ----- | ------------------------------------------------------ | ------------------------------------------------ |
| **0** | Base Infrastructure                                    | RNF-005                                          |
| **1** | Database and Persistence on Demand                     | RF-016, RF-017, RF-018, RF-019, RNF-001, RNF-003 |
| **2** | AI Pipeline (Insight Card + Alt Text)                  | RF-002, RF-003, RF-007, RF-009, RNF-002, RNF-006 |
| **3** | API Contract                                           | RF-001, RNF-001                                  |
| **4** | Frontend: Insight Card and Alt Text                    | RF-004, RF-005, RF-006, RF-008                   |
| **5** | Accessibility (ARIA)                                   | RF-010, RF-011, RF-012, RNF-004                  |
| **6** | Authentication over PostgreSQL (Firebase Discontinued) | RF-013, RF-014                                   |
| **7** | Administrative Panel                                   | — (outside the formal FRs, operational support)  |
| **8** | Testing and Quality                                    | All FRs/NFRs                                     |
| **9** | Continuous Documentation and Closeout                  | —                                                |

---

## 2. Dependencies Between Blocks

| Block                              | Depends On                     | Can Run in Parallel With |
| ---------------------------------- | ------------------------------ | ------------------------ |
| 0 — Infrastructure                 | —                              | —                        |
| 1 — Database and Persistence       | 0                              | 6 (independent schemas)  |
| 2 — AI Pipeline                    | 0                              | 1, 6                     |
| 3 — API Contract                   | 1, 2                           | —                        |
| 4 — Insight Card Frontend          | 3                              | —                        |
| 5 — Accessibility                  | 4                              | —                        |
| 6 — Authentication over PostgreSQL | 0, 1 (user schema)             | 1 (AI content), 2        |
| 7 — Administrative Panel           | 1, 3                           | —                        |
| 8 — Testing and Quality            | 4, 5, 6 (partial, incremental) | —                        |
| 9 — Continuous Documentation       | — (continuous from the start)  | All                      |

**Key insight:** the AI pipeline (Block 2) is testable in isolation via script, without depending on a ready HTTP endpoint or frontend. This allows validating the quality of the generation before any API or UI layer exists.

---

## 3. Recommended Execution Order

```
Phase 1  → Base Infrastructure                          (Block 0)
Phase 2  → Database Schemas                             (Block 1, DB part)
Phase 3  → Isolated AI Pipeline (script/CLI)             (Block 2)
Phase 4  → Persistence on Demand (integration)           (Block 1, integration)
Phase 5  → API Contract                                  (Block 3)
Phase 6  → Frontend: Insight Card + Alt Text              (Block 4)
Phase 7  → Accessibility (ARIA)                           (Block 5)
Phase 8  → Authentication over PostgreSQL  [parallelizable from Phase 1]  (Block 6)
Phase 9  → Administrative Panel                           (Block 7)
Phase 10 → Testing and Quality                            (Block 8)
Phase 11 → Closeout and Final Documentation               (Block 9, continuous)
```

Phase 8 (authentication over PostgreSQL) does not depend on any artifact from the AI pipeline — it only shares the database infrastructure (Phase 1/2). It can be developed in parallel with Phases 3–7 without risk of blocking.

---

## 4. Detailed Checklist

### Phase 0 — Pending Specifications (documentary prerequisite)

None of the implementation phases below should begin before the corresponding specification exists and is approved.

- [x] Doc 03 — Use Cases (Gherkin)
- [x] Doc 04 — System Architecture
- [x] Doc 05 — Database (ERD, schema, dictionary)
- [x] Doc 06 — Persistence Flow Diagram
- [x] Doc 07 — Interface Specification (API Contract)
- [x] Doc 08 — Navigation and Flow
- [x] Doc 09 — AI Pipeline
- [x] Doc 10 — Card Design _(content ready; `.png` file still to be included in `documentation/specs/` — does not block Phases 1–5, 7–9; it only blocks the effective start of Phase 6)_
- [x] Doc 11 — Prompt Engineering

> Docs 12–19 (tests, quality, risks, traceability, journal, final report, feasibility study) do not block the start of implementation and can be written close to the corresponding phases (see Phases 10–11).

---

### Phase 1 — Base Infrastructure

**Block 0** · Depends on: doc 04 (infrastructure decisions)

- [ ] Provision a PostgreSQL instance (local development environment)
- [ ] Create the Azure OpenAI resource and obtain the key/endpoint for the multimodal model
- [ ] Configure environment variables (.env) on the backend and frontend, without committing secrets (RNF-005)
- [ ] Validate connectivity with PostgreSQL via a simple test script
- [ ] Validate a test call to Azure OpenAI (one fixed image + fixed prompt, no business logic)
- [ ] Confirm the validity of the Harvard Art Museums API key (already existing from the MVP)

---

### Phase 2 — Database Schemas

**Block 1 (DB part)** · Depends on: doc 05 (Database)

- [ ] Model the AI content table per artwork (historical contextualization, comparative analysis, alt text, prompt version, timestamps)
- [ ] Model the users table for the new authentication system, created from scratch (independent of the table above — can be done in the same phase, with no ordering between them)
- [ ] Create migrations (e.g., Alembic) for both tables
- [ ] Apply migrations in the development environment
- [ ] Populate a test seed with 2–3 fictitious artworks to validate the schema
- [ ] Resolve the pending issues from doc 07 (§8) before finalizing the schema: add `is_admin` to `users` (needed for Phase 9) and create the `password_reset_tokens` table (needed for Phase 8)

---

### Phase 3 — Isolated AI Pipeline

**Block 2** · Depends on: doc 09 (AI Pipeline — completed), doc 11 (Prompt Engineering — completed, `v1` prompt defined)

Developed and tested via script/CLI, without depending on an HTTP endpoint or frontend.

- [ ] Implement proactive verification of image accessibility before any call to the LLM (doc 09, §4 — `ImageUnavailableError`)
- [ ] Implement prompt assembly (system message + user message) using the `v1` prompt text (doc 11, §3) from the metadata selected in `ArtworkMetadata` (doc 09, §3 and §5)
- [ ] Implement the call to Azure OpenAI with structured output (JSON Schema, doc 11 §3.3) for the 3 simultaneous fields (doc 09, §5 and §6 — RF-002, RF-003, RF-007, RF-009)
- [ ] Implement completeness validation of the response (`is_complete()`), including the 50–300 character range for the Alt Text (doc 09, §7 — RF-007)
- [ ] Test the pipeline with 3–5 real artworks from the Harvard API, validate quality manually
- [ ] Confirm that no automatic retry attempt is implemented (doc 09, §8, decision 3) and that the total timeout respects the 60s of RNF-002

---

### Phase 4 — Persistence on Demand (Integration)

**Block 1 (integration)** · Depends on: Phase 2 + Phase 3 completed; doc 06 (Persistence Flow)

- [ ] Implement a function to look up content by artwork ID in the database
- [ ] Implement the verification logic: exists → return from the database; does not exist → trigger the pipeline (Phase 3) and persist (RF-016, RF-017, RF-018)
- [ ] Handle persistence failure without breaking the response to the user (RF-017, scenario 2)
- [ ] Test the complete flow via script: first call generates and persists; second call does not invoke the AI

---

### Phase 5 — API Contract

**Block 3** · Depends on: Phase 4 completed; doc 07 (API Contract)

- [ ] Implement the search/generation endpoint for the Insight Card per artwork (triggers the Phase 4 logic)
- [ ] Define the response format (contextualization, comparative, alt_text, status)
- [ ] Implement HTTP error handling (LLM timeout, nonexistent artwork — RF-019)
- [ ] Test the endpoint via cURL/Postman with real artworks

---

### Phase 6 — Frontend: Insight Card and Alt Text

**Block 4** · Depends on: Phase 5 completed; doc 08 (Navigation), doc 10 (Card Design — content ready, awaiting inclusion of the `.png` file in `documentation/specs/`)

- [ ] Create the Insight Card component (contextualization and comparative analysis sections)
- [ ] Integrate the component with the Phase 5 endpoint
- [ ] Implement the loading state (RF-005)
- [ ] Implement the error state (RF-006)
- [ ] Apply the generated Alt Text to the artwork's `<img>` tag, with a generic fallback if absent (RF-008)

---

### Phase 7 — Accessibility (ARIA)

**Block 5** · Depends on: Phase 6 (component already existing); doc 03 (use cases with screen reader)

- [ ] Add `aria-label`/`aria-labelledby` to the Insight Card sections (RF-010)
- [ ] Add `aria-live="polite"` to the loading/error states (RF-011)
- [ ] Validate keyboard navigation (Tab/Shift+Tab) in the component (RF-012)
- [ ] Test manually with NVDA or VoiceOver (RNF-004)

---

### Phase 8 — Authentication over PostgreSQL (Firebase Discontinued)

**Block 6** · Parallelizable from Phase 1 · Depends on: Phase 2 (user schema); doc 04 (authentication strategy)

> Database created from scratch — no Firebase data is migrated (see Change Note in doc 02, doc 04, and doc 05).

- [ ] Implement authentication endpoints using PostgreSQL (registration, login, logout, session, password recovery — doc 07 §5)
- [ ] Fully remove Firebase code, configuration, and credentials (frontend and backend), including `.firebaseAdminSDK.json` — no data needs to be preserved before removal
- [ ] Validate end-to-end functional parity (login, logout, password recovery, session persistence) with new accounts created in PostgreSQL (RF-014)

---

### Phase 9 — Administrative Panel

**Block 7** · Depends on: Phase 4 (existing persisted data), Phase 5 (available endpoint)

- [ ] Create a screen listing artworks processed by the AI (status, generation date)
- [ ] Allow viewing the generated content for a specific artwork
- [ ] _(Optional, low priority)_ Allow manually re-triggering the generation for an artwork

---

### Phase 10 — Testing and Quality

**Block 8** · Depends on: docs 12, 13, 14; functionalities from Phases 3–8 implemented

- [ ] Write test cases from the Gherkin scenarios in doc 02
- [ ] Run an Alpha test round (functional)
- [ ] Run a quality evaluation of the generated content (historical accuracy, hallucination, coherence)
- [ ] Run formal accessibility tests
- [ ] Run a Beta test round (usability)

---

### Phase 11 — Closeout and Final Documentation

**Block 9** · Continuous from the start of development

- [ ] Keep the Development Journal (doc 17) updated at every relevant milestone
- [ ] Update the Traceability Matrix (doc 16) as requirements are implemented and tested
- [ ] Update the Risk Management Plan (doc 15) as risks materialize or are mitigated
- [ ] Write the Technical Feasibility Study — RAG/Embeddings (doc 19) — can occur at any time after Phase 3, since it neither blocks nor is blocked by any other phase
- [ ] Consolidate the Final Technical Report (doc 18) at the end of the semester

---

## 5. Non-Blocking Rules

- The AI pipeline (Phase 3) is validated via an isolated script, without waiting for a ready endpoint or frontend — allowing prompt quality issues to be detected early.
- The AI content schema and the users schema (Phase 2) are independent of each other — there is no mandatory order between them.
- The authentication implementation (Phase 8) depends only on the base infrastructure (Phase 1) and the users schema (Phase 2) — it can be developed in parallel with the AI pipeline and the frontend, since it shares no code with those blocks.
- The RAG/Embeddings feasibility study (doc 19) is isolated and can be produced at any time without impacting the implementation schedule.
- Continuous documentation (journal, risks, traceability) runs in parallel with all phases, avoiding an accumulation of documentation work at the end of the semester.

---

## 6. Maintenance Note

This document must be revised as documents 03 to 19 are produced, since each one may refine or alter the execution order proposed here. Any structural update to this guide (change of phases, blocks, or dependencies) will be proposed to the user before being applied.
