# Development and Governance Rules — Art Archive AI

**Version:** 1.0
**Date:** 2026-07-03
**Status:** Approved
**Scope:** This document governs all other documents in `/documentation/specs/` and all code produced from them. In case of doubt about how to proceed during development, this is the first document to be consulted.

---

## 1. Purpose

Art Archive AI is developed following **Spec-Driven Development (SDD)**: no functionality is implemented without a prior, approved specification in `/documentation/specs/`. This document exists to make that rule operational — it defines what cannot be broken under any circumstances, how development should be conducted day to day, and what to do when the specification does not cover a scenario found during implementation.

This document does not replace the others — it is the layer of rules that applies _on top of_ all of them.

---

## 2. Hard Rules (Cannot Be Broken Under Any Circumstances)

1. **No functionality is implemented without a corresponding approved specification** in `/documentation/specs/`. If the code needs to do something that no document describes, implementation stops and the specification is written or revised first — never the other way around.
2. **No API key, secret, or credential is exposed on the front-end or committed to the repository.** Every call to Azure OpenAI and to the Harvard Art Museums API happens exclusively on the backend (RNF-005, doc 04 §9 decision 3).
3. **No call to the AI or to the Harvard API originates directly from the front-end.** The front-end only talks to the project's single backend (doc 04 §6).
4. **No existing MVP functionality is removed, rewritten, or has its behavior changed without explicit parity validation before the old code is removed** — this applies especially to the replacement of Firebase Auth with authentication over PostgreSQL (ensuring login, logout, and password recovery keep working, even over a new user base — RF-014) and to the rewrite of the Harvard proxy (doc 04 §11).
5. **_(Removed — 2026-07-03)_** Applied to the migration of data from Firebase to PostgreSQL. No longer applies: by explicit project decision, PostgreSQL is created from scratch and all Firebase user data is discarded without migration (RF-015 and UC-07 removed — see doc 02 and doc 03). This identifier is kept as removed, not reused, for historical traceability.
6. **No structural change to an already existing specification document is made silently.** Content changes (correction, clarification) can be made directly; changes to structure, scope, or architectural decisions are flagged to the author before being applied.
7. **No pending issue identified during development is resolved by assumption.** See Section 4.
8. **All code that implements a Functional Requirement must be validated against that requirement's Gherkin scenarios (doc 02 and doc 03) before being considered complete.**

---

## 3. Development Conduct Rules

1. **Follow the phase order in doc 99**, respecting the dependencies documented there. Do not start a phase whose source specification does not yet exist (doc 99, §4, Phase 0).
2. **Every relevant function, endpoint, or component must reference the FR/NFR/UC it implements** — in a comment, docstring, or in the commit/PR description. This keeps traceability alive between code and specification, beyond doc 16.
3. **Do not introduce abstractions, configurations, or generalizations beyond what the current specification requires.** If a requirement describes a single case, the code implements that single case — not a generic solution for hypothetical future cases.
4. **Keep the specification documents up to date** as implementation progresses: status in the doc 01 index (§9), the doc 99 checklist, and any new decision documented in the appropriate place.
5. **Prefer many small, atomic commits**, each implementing a specific FR/UC or a clear step of a technical document (doc 06, doc 09), making it easier to revert an isolated decision without affecting the rest.
6. **Every technical decision not foreseen in any specification, but necessary for the code to work** (e.g., a specific library, an error-handling pattern not covered), must be recorded as an explicit decision in the document most related to the topic — never left only implicit in the code.

---

## 4. Pending Issue Mitigation Rules

### 4.1 What a pending issue is

A pending issue is any scenario, behavior, or decision that the code **needs to resolve in order to work**, but that **no document in `/documentation/specs/` defines with sufficient clarity**. This has already happened several times during the drafting of these documents (see Section 6) — it is expected to keep happening during implementation.

### 4.2 Central rule

**Nothing is created or decided "in the code" without being within the specifications.** Upon finding a pending issue:

1. **Stop** implementing that specific piece — do not write improvised behavior just to "make it work for now."
2. **Record the pending issue** in the document most related to the topic, in a clear section (following the pattern already used in docs 03 §5, 06 §7, and 07 §8): what is missing, why it is necessary, and a suggested solution, if there is an obvious one.
3. **Communicate the pending issue to the author** before proceeding with the implementation of that piece — never just record it silently and move on with your own assumption.
4. **Wait for the formal definition** (an update to the corresponding document) before implementing the definitive behavior. If a temporary unblock is indispensable to avoid stalling all development, it must be explicitly marked in the code as provisional and linked to the recorded pending issue.

### 4.3 What this prevents

This rule exists to prevent the most common scenario of divergence between code and documentation in SDD projects: the developer (or an AI assistant) finds an uncovered case, tries to be helpful, decides something reasonable on their own, and the specification is never updated — the code becomes the sole source of truth about that behavior, breaking the purpose of the entire Spec-Driven Development process.

---

## 5. Hierarchy and Conflict Resolution Between Documents

When two documents appear to contradict each other:

1. The **more specific document, closer to the implementation** (higher numbering) prevails over a more general document — e.g., doc 09 (AI Pipeline) prevails over doc 04 (Architecture) on pipeline implementation details, as long as it does not contradict an explicit decision in doc 04.
2. **Exception:** no document may contradict doc 01 (Vision and Scope) without this being treated as a review pending issue for doc 01 itself, escalated to the author — doc 01 is the foundation of everything (doc 01, §9).
3. A conflict found is never resolved silently by picking one of the two sides — it is treated as a pending issue (Section 4).

---

## 6. Rules for the Use of AI Assistants in Development

Since this project is built with the support of AI assistants (e.g., Claude Code) for both documentation and code, the rules in this document apply fully to that use:

1. An AI assistant **never implements a functionality that does not have an approved specification** — even if the request seems simple or obvious.
2. An AI assistant that finds a specification gap while generating documentation or code **must explicitly report it to the author**, following the same format already established in docs 03, 06, 07, and 09, instead of filling the gap on its own.
3. Structural changes proposed by an AI assistant to an already existing document (e.g., changing an architectural decision, removing a section) **are always confirmed with the author before being applied**.

---

## 7. Known Pending Issues Log (Convenience Index)

Convenience list pointing to pending issues already identified during the drafting of the documents so far. The full content of each one lives in its source document — this table exists only so they are not lost from sight.

| Pending Issue                                  | Source Document                        | Summary                                                                                                                                                                                     |
| ---------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Alt Text when the image is inaccessible        | doc 03 (§5), doc 06 (§7), doc 09 (§10) | Today, if the artwork's image cannot be processed, no Alt Text is persisted and the user receives no warning. Recommendation: generate a default warning text instead of omitting the field |
| Missing administrative privilege in the schema | doc 07 (§8, item 1)                    | `users` has no field to distinguish administrators from regular visitors, needed for the `/admin/*` endpoints                                                                               |
| Missing password reset token storage           | doc 07 (§8, item 2)                    | `POST /auth/password-reset/confirm` depends on a token table with expiration that does not yet exist in doc 05                                                                              |

> This table must be updated whenever a new pending issue is recorded in any document, and a row must be removed only when the corresponding pending issue is formally resolved in its source document.

---

## 8. Maintenance Note

This document is the constitution of this project's development process — its rules must be stable. Changes to it (addition, removal, or modification of any rule in Sections 2 through 6) require explicit confirmation from the author before being applied. Section 7 is the exception: being a convenience index, it must be kept continuously up to date as new pending issues arise or are resolved.
