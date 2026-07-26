# Use Cases — Art Archive AI

This document centralizes the project's **User Stories** and **Use Cases**, complementing the requirement documents: those specify atomic requirements (RF/RNF) with Gherkin scenarios for unit-level validation, each testing a single business rule, while this document describes complete interaction flows between actors and the system, from start to finish, grouping multiple requirements into a single end-to-end testable use case (integration level).

It is aligned with the current requirements structure (`documentation/specs/requeriments/02.1` through `02.5`), organized into four continuous blocks — Insight Card (RF-001–RF-010), Alt Text (RF-011–RF-013), Accessibility (RF-014–RF-025), Authentication (RF-026–RF-031) — plus non-functional requirements (RNF-001–RNF-008).

Following that same structure, the detailed User Stories and Use Cases are split across four companion documents. This document itself keeps only what's shared across all of them — conventions, the design principle, the actors — plus an index of every User Story and Use Case; their full description lives in the corresponding file below.

| Document                                                 | Block                              | Contains                   |
| -------------------------------------------------------- | ---------------------------------- | -------------------------- |
| [03.1-insight-card.md](03.1-insight-card.md)             | Context Information (Insight Card) | US-001–US-005, UC-01–UC-04 |
| [03.2-alt-text.md](03.2-alt-text.md)                     | Alt Text                           | US-006–US-007, UC-05       |
| [03.3-aria-accessibility.md](03.3-aria-accessibility.md) | Accessibility                      | US-008–US-018, UC-06–UC-14 |
| [03.4-authentication.md](03.4-authentication.md)         | Account & Session                  | US-019–US-024, UC-15–UC-20 |

## Conventions

- **UC-XX** — Use Case
- **US-XXX** — User Story
- Each Use Case has: Primary Actor, Secondary Actors, Preconditions, Main Flow, Alternative/Exception Flows, Postconditions, and Acceptance Criteria in Gherkin
- Each Use Case references the RF/RNF from document 02 that it covers
- User Stories and Use Cases are grouped by **feature**, not by user category — see the design principle below

---

## Design Principle — One User, Every Feature

The platform has a single human actor: **the User**. A User may be young or old, an art expert or a first-time visitor, may navigate with a mouse, a keyboard only, or a screen reader — none of that changes which features are available to them. Every requirement applies to every User equally; there is no "reduced" experience for a User who relies on assistive technology.

This document reflects that in two ways:

1. **Feature-level stories** ("read the historical context", "log in", "see the comparative analysis") are written for "a User", never for "a sighted User" or "a User without a disability" — the need described is identical regardless of how the User perceives the page.
2. **Interaction-modality stories** (screen reader announcements, keyboard operability, ARIA semantics) are written separately only because they describe a distinct _technical_ concern — how a feature is delivered — not because they belong to a separate class of user. A User who tabs through the page and a User who reads it with a screen reader are exercising the same features described elsewhere in this document; the Accessibility block (US-008–US-018, UC-06–UC-14) exists to make sure those delivery paths are independently testable, not to fork the product into two experiences.

---

## Actors

| Actor                             | Type            | Description                                                                                                                                                                                                                                                            |
| --------------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **User (Visitor)**                | Human           | Any person who accesses the platform to explore artworks. May use a mouse, a keyboard only, or a screen reader interchangeably — the platform must support all of them equally, since every feature is available to every User regardless of how they interact with it |
| **Authenticated User**            | Human           | A User (Visitor) who has created an account and holds a valid session; relevant specifically to flows that require being logged in                                                                                                                                     |
| **Art Archive System (Back-end)** | Internal system | Orchestrates the verification, generation, and persistence of AI content, and the authentication/session logic                                                                                                                                                         |
| **Multimodal LLM (Azure OpenAI)** | External system | Generates the historical context, comparative analysis, and Alt Text from the artwork's image and metadata, with open web-search capability                                                                                                                            |
| **Harvard Art Museums API**       | External system | Source of the artworks' metadata and images (integration inherited from the original MVP)                                                                                                                                                                              |
| **PostgreSQL (Database)**         | Infrastructure  | Single source of truth for generated content, user accounts, sessions, and password-reset tokens                                                                                                                                                                       |
| **Assistive Technology**          | Support tool    | Screen reader (NVDA, VoiceOver, JAWS) or other AT a User (Visitor) may use to interact with the platform — the same User, the same features, a different input/output modality, not a separate actor                                                                   |

---

## User Stories Index

### Block A — Context Information (Insight Card)

| ID     | Summary                                                                                               |
| ------ | ----------------------------------------------------------------------------------------------------- |
| US-001 | Read a historical context about the artwork and its artist                                            |
| US-002 | See a comparison to at least one other artist or artwork with a similar period, technique, or culture |
| US-003 | Load an already-generated context information almost instantly on return visits                       |
| US-004 | Be told clearly when no context information could be generated                                        |
| US-005 | See the sources the AI used to write the context information                                          |

### Block B — Alt Text

| ID     | Summary                                                      |
| ------ | ------------------------------------------------------------ |
| US-006 | Get a description of what the artwork's image actually shows |
| US-007 | Never see an empty, missing, or generic placeholder alt text |

### Block C — Accessibility

| ID     | Summary                                                                          |
| ------ | -------------------------------------------------------------------------------- |
| US-008 | Hear the "Context information" section announced once as a single labeled region |
| US-009 | Be automatically told when context information is loading or has failed          |
| US-010 | Hear sources announced as a proper list, or nothing when there are none          |
| US-011 | Jump between page regions and skip repeated navigation                           |
| US-012 | Understand what every icon-only button does                                      |
| US-013 | Operate every gallery tile, filter chip, and sort option from the keyboard       |
| US-014 | Use the image viewer and filter panel without losing keyboard context            |
| US-015 | Operate sort/filter dropdowns with the arrow keys                                |
| US-016 | Get understandable form labels and error messages on Login/Sign Up               |
| US-017 | Always see where keyboard focus is, on every page                                |
| US-018 | Know immediately when a search/filter returns nothing, or a page doesn't exist   |

### Block D — Account & Session

| ID     | Summary                                            |
| ------ | -------------------------------------------------- |
| US-019 | Log in with email and password                     |
| US-020 | Sign up with email, password, and name             |
| US-021 | Log out explicitly                                 |
| US-022 | Request a password reset via "Forgot Password"     |
| US-023 | Set a new password from a reset link               |
| US-024 | Stay logged in across reloads and browser restarts |

---

## Use Cases Index

### Block A — Context Information (Insight Card)

| ID    | Title                                                             |
| ----- | ----------------------------------------------------------------- |
| UC-01 | Generate Context Information on First Visit (Both Blocks Missing) |
| UC-02 | View an Already-Persisted Context Information (Cache)             |
| UC-03 | Regenerate Only the Missing Block                                 |
| UC-04 | Handle Total Failure of Context Information Generation            |

### Block B — Alt Text

| ID    | Title                                   |
| ----- | --------------------------------------- |
| UC-05 | Consume Alt Text of the Artwork's Image |

### Block C — Accessibility

| ID    | Title                                                               |
| ----- | ------------------------------------------------------------------- |
| UC-06 | Navigate the "Context Information" Region via Screen Reader         |
| UC-07 | Navigate the Platform via Landmarks and Skip Link                   |
| UC-08 | Operate Icon-Only Controls via Screen Reader                        |
| UC-09 | Operate Non-Native Interactive Elements via Keyboard                |
| UC-10 | Open and Operate a Modal or Overlay (Image Lightbox / Filter Panel) |
| UC-11 | Operate a Custom Sort/Filter Dropdown via Keyboard                  |
| UC-12 | Fill and Submit an Accessible Form (Login / Sign Up)                |
| UC-13 | Full Keyboard Traversal With Visible Focus                          |
| UC-14 | Encounter an Accessible Empty or 404 State                          |

### Block D — Account & Session

| ID    | Title                                                  |
| ----- | ------------------------------------------------------ |
| UC-15 | Log In With Email and Password                         |
| UC-16 | Create an Account (Sign Up)                            |
| UC-17 | Log Out                                                |
| UC-18 | Request a Password Reset (Forgot Password)             |
| UC-19 | Set a New Password From a Reset Link (Change Password) |
| UC-20 | Resume Session After Reload or Restart                 |

---

## Summary Traceability Matrix

| Use Case | User Stories                   | Functional / Non-Functional Requirements                         |
| -------- | ------------------------------ | ---------------------------------------------------------------- |
| UC-01    | US-001, US-002, US-005, US-009 | RF-001–RF-006, RF-008–RF-010 · RNF-002, RNF-003, RNF-005–RNF-007 |
| UC-02    | US-001, US-002, US-003         | RF-001, RF-005, RF-008 · RNF-001                                 |
| UC-03    | US-001, US-002                 | RF-001–RF-005                                                    |
| UC-04    | US-004, US-009                 | RF-005, RF-007 · RNF-008                                         |
| UC-05    | US-006, US-007                 | RF-011, RF-012, RF-013                                           |
| UC-06    | US-008, US-009, US-010         | RF-014–RF-017 · RNF-004                                          |
| UC-07    | US-011                         | RF-018 · RNF-004                                                 |
| UC-08    | US-012                         | RF-019 · RNF-004                                                 |
| UC-09    | US-013                         | RF-020 · RNF-004                                                 |
| UC-10    | US-014                         | RF-021 · RNF-004                                                 |
| UC-11    | US-015                         | RF-022 · RNF-004                                                 |
| UC-12    | US-016                         | RF-023 · RNF-004                                                 |
| UC-13    | US-013, US-017                 | RF-024 · RNF-004                                                 |
| UC-14    | US-018                         | RF-025 · RNF-004                                                 |
| UC-15    | US-019                         | RF-026                                                           |
| UC-16    | US-020                         | RF-027                                                           |
| UC-17    | US-021                         | RF-028                                                           |
| UC-18    | US-022                         | RF-029                                                           |
| UC-19    | US-023                         | RF-030                                                           |
| UC-20    | US-024                         | RF-031                                                           |
