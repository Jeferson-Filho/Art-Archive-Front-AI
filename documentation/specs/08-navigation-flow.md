# Navigation and Flow — Art Archive AI

**Version:** 1.0
**Date:** 2026-07-03
**Status:** Under review
**Base documents:** [02 — Requirements](./02-requirements.md), [03 — Use Cases](./03-use-cases.md), [06 — Persistence Flow](./06-persistence-flow.md), [07 — API Contract](./07-api-contract-en.md)

---

## 1. Purpose

Map the screens and transitions of the user experience on the expanded platform. Unlike the original MVP navigability diagram (`documentation/Navigability Diagrams/`), which includes planned screens that were never implemented, this document starts from the **actual state of the current code** (routes in `src/app/`) and overlays the new screens and states introduced by this expansion.

---

## 2. Reconciliation with the Original MVP Navigability Diagram

| Screen (original diagram)       | Route in current code                                          | Status                                                                           |
| ------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 2.1 — Home (Grid)               | `src/app/home/`                                                | Implemented                                                                      |
| 2.3 — Home (Search Result)      | `src/app/home/` (same component, internal filter/search state) | Implemented as a state, not as a separate route                                  |
| 2.4 — Loading Screen            | `src/app/home/` (internal state)                               | Implemented as a state                                                           |
| 2.5 — Artwork Details           | `src/app/object/[objectId]/`                                   | Implemented                                                                      |
| 2.6 — 404                       | `src/app/not-found.tsx`                                        | Implemented                                                                      |
| 3.1 — Sign in                   | `src/app/login/`                                               | UI implemented; authentication logic (Firebase) is currently inert/commented out |
| 3.2 — Sign up                   | `src/app/signUp/`                                              | UI implemented; authentication logic inert                                       |
| 3.3 — Forgot password           | —                                                              | **Never implemented** — only planned in the original diagram                     |
| 3.4 — Change password           | —                                                              | **Never implemented** — only planned                                             |
| 4.2 — Modal Save to Archive Box | —                                                              | **Never implemented**                                                            |
| 4.3 — User Space                | —                                                              | **Never implemented**                                                            |
| 4.4 / 4.5 — Archive Box         | —                                                              | **Never implemented**                                                            |

This reconciliation is the same finding already recorded in doc 05 (Decision 6): the "saved preferences" functionality (Archive Box) exists only in old diagrams, not in the code.

---

## 3. Scope of This Expansion in Navigation

**New in this expansion:**

- States of the **Insight Card** within the Artwork Details screen (loading, displayed, error) — RF-004, RF-005, RF-006, doc 06.
- Complete authentication flow via the project's own backend, including the **Forgot Password** and **Change Password** screens, planned since the original MVP but never built — now necessary to fulfill the password-recovery functional parity required by RF-014 and formalized as endpoints in doc 07 (§5).
- **Administrative Panel** (list of processed artworks and detail of generated content) — doc 04 (§4) and doc 07 (§6).

**Out of scope for this expansion** (see Section 8): User Space, Archive Box, and the save-artwork modal — no FR of this expansion covers the construction of these screens (doc 01, §5.2).

---

## 4. General Navigability Diagram

```mermaid
flowchart TD
    Visitor(["Visitor accesses the site"]) --> Home["2.1 — Home (Artwork Grid)"]

    Home -->|"Searches or applies a filter"| SearchResult["2.3 — Home (Search Result)"]
    SearchResult -->|"Clicks on an artwork"| Detail["2.5 — Artwork Details"]
    Home -->|"Clicks on an artwork"| Detail
    Home -->|"Invalid route"| NotFound["2.6 — 404"]
    NotFound -->|"Clicks on Home"| Home

    Home -->|"Clicks on Sign In"| Login["3.1 — Login"]
    Login -->|"Clicks on Create Account"| SignUp["3.2 — Sign Up"]
    Login -->|"Clicks on Forgot Password"| Forgot["3.3 — Forgot Password"]
    Forgot -->|"Link sent by email"| ChangePass["3.4 — Change Password"]
    ChangePass -->|"Password changed"| Login
    Login -->|"Successful login"| Home
    SignUp -->|"Successful sign-up"| Home

    Detail --> InsightLoading["Insight Card: Loading"]
    InsightLoading -->|"Generation completed"| InsightReady["Insight Card: Displayed"]
    InsightLoading -->|"Generation failed"| InsightError["Insight Card: Error"]

    Login -->|"User with admin privilege accesses /admin"| AdminList["Admin — List of Processed Artworks"]
    AdminList -->|"Selects an artwork"| AdminDetail["Admin — Detail of Generated Content"]

    Home -.->|"Out of scope"| UserSpace["User Space"]
    UserSpace -.-> ArchiveBox["Archive Box"]
    Detail -.->|"Out of scope"| SaveModal["Modal: Save Artwork"]

    classDef implemented fill:#d4edda,stroke:#28a745,color:#000;
    classDef newScreen fill:#cfe2ff,stroke:#0d6efd,color:#000;
    classDef outOfScope fill:#e9ecef,stroke:#6c757d,color:#666,stroke-dasharray: 5 5;

    class Home,SearchResult,Detail,NotFound,Login,SignUp implemented;
    class Forgot,ChangePass,InsightLoading,InsightReady,InsightError,AdminList,AdminDetail newScreen;
    class UserSpace,ArchiveBox,SaveModal outOfScope;
```

**Legend:** green = already implemented in the MVP · blue = new in this expansion · dashed gray = out of scope (reference only).

---

## 5. Detailed Flow — Authentication

The screen flow (Login → Sign Up → Forgot Password → Change Password) remains structurally the same as planned in the original MVP diagram. What changes in this expansion is what happens **behind** each screen: calls now go to the endpoints in doc 07 (§5) instead of Firebase Auth.

| Transition                                  | Endpoint triggered                  | Requirement     |
| ------------------------------------------- | ----------------------------------- | --------------- |
| Login → Home (success)                      | `POST /auth/login`                  | RF-013          |
| Sign Up → Home (success)                    | `POST /auth/register`               | RF-014 (parity) |
| Forgot Password → confirmation-email notice | `POST /auth/password-reset/request` | RF-014 (parity) |
| Email link → Change Password → Login        | `POST /auth/password-reset/confirm` | RF-014 (parity) |

---

## 6. Detailed Flow — Insight Card States

The Insight Card does not introduce a new route — it is a region with three possible states within the Artwork Details screen (2.5), consuming `GET /artworks/{artwork_id}/insight-card` (doc 07, §4).

```mermaid
stateDiagram-v2
    [*] --> Loading: Page loads, content is not in local cache
    Loading --> Displayed: 200 response received
    Loading --> Error: 404/502/504 response received
    Displayed --> [*]
    Error --> [*]
```

| State     | Description                                                                     | Requirement    |
| --------- | ------------------------------------------------------------------------------- | -------------- |
| Loading   | Displayed while the request to the backend is in progress (client-side, RF-005) | RF-005         |
| Displayed | Full content (contextualization + comparison) rendered                          | RF-004         |
| Error     | Error message in the card area; the rest of the page remains functional         | RF-006, RF-019 |

The three states must be correctly announced by assistive technology via `aria-live` (RF-011) — see doc 03, UC-05.

---

## 7. Detailed Flow — Administrative Panel (New)

```mermaid
flowchart LR
    Login -->|"Login with admin privilege"| AdminList["Admin — List of Processed Artworks<br/>GET /admin/artworks"]
    AdminList -->|"Selects an artwork"| AdminDetail["Admin — Content Detail<br/>GET /admin/artworks/{id}"]
    AdminDetail -->|"Regenerate (optional)"| AdminDetail
```

> **Pending dependency:** access to `/admin/*` requires the distinction of administrative privilege (`is_admin`), which is not yet defined in the schema — a pending issue already recorded in doc 07 (§8, item 1). Navigation to this section must be blocked until this definition is resolved.

---

## 8. Out of Scope for This Expansion

The **User Space**, **Archive Box**, and **Save Artwork Modal** screens appear in the Section 4 diagram only as a reference for future navigation (dashed lines). They are not built in this expansion because:

- No FR in doc 02 covers the implementation of these screens.
- Doc 01 (§5.2) explicitly excludes functionalities from the original MVP that were not delivered.
- Doc 05 (Decision 6) already models `saved_artworks` in a minimal way for exactly this reason — the data has a place to exist, but the interface to manage it is not part of this semester.

---

## 9. Navigation Acceptance Criteria

```gherkin
Feature: Navigation for password recovery

  Scenario: User requests a password reset
    Given the user is on the Login screen
    When they click on "Forgot Password"
    Then the "Forgot Password" screen is displayed
    And, upon entering a valid email, a confirmation notice is displayed

  Scenario: User completes the password change
    Given the user has accessed the reset link received by email
    When they enter and confirm the new password on the "Change Password" screen
    Then the user is redirected to the Login screen
```

```gherkin
Feature: Insight Card navigation

  Scenario: Transition from loading to displayed
    Given the user accesses the Artwork Details screen
    And the Insight Card is in the "Loading" state
    When the request to the backend returns successfully
    Then the state changes to "Displayed", without reloading the page
```

---

## 10. Traceability

| Navigation Element                                                          | Related Requirements                                           | Related Use Cases   |
| --------------------------------------------------------------------------- | -------------------------------------------------------------- | ------------------- |
| Home, Artwork Details, 404 (inherited)                                      | —                                                              | —                   |
| Login, Sign Up, Forgot/Change Password                                      | RF-013, RF-014                                                 | UC-06               |
| Insight Card states                                                         | RF-004, RF-005, RF-006, RF-011                                 | UC-01, UC-03, UC-05 |
| Administrative Panel                                                        | — (Block 7 of doc 99)                                          | —                   |
| Sitewide accessibility (Home, Search, Artwork Details, Login, Sign Up, 404) | RF-020, RF-021, RF-022, RF-023, RF-024, RF-025, RF-026, RF-027 | UC-05               |

> The complete matrix, connecting requirements to architecture components and test cases, will be formalized in document 16 — Traceability Matrix.
