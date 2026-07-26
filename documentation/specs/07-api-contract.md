# Interface Specification — API Contract — Art Archive AI

**Version:** 2.1
**Date:** 2026-07-26
**Status:** In Review
**Base Documents:** [02.1 — Insight Card](./requeriments/02.1-insight-card.md), [02.2 — Alt Text](./requeriments/02.2-alt-text.md), [02.4 — Authentication](./requeriments/02.4-authentication.md), [02.5 — Non-Functional](./requeriments/02.5-non-functional.md), [04 — System Architecture](./04-architecture.md), [05 — Database](./05-database.md), [06 — Persistence Flow](./06-persistence-flow.md)

---

## 1. General Conventions

| Aspect                    | Definition                                                                                                                                                                                      |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Base URL**              | Defined by `NEXT_PUBLIC_API_URL` in the front-end (doc 04, §3) — points to the single backend service                                                                                           |
| **Format**                | `application/json` in all requests and responses, except where indicated                                                                                                                        |
| **Authentication**        | `httpOnly` session cookie (`SESSION_COOKIE_NAME`, already used by `src/middleware.ts`), issued by the login endpoint. Endpoints that require authentication return `401` without a valid cookie |
| **CORS**                  | Enabled for the front-end origin, inherited from the current behavior of the Flask proxy (`flask-cors`)                                                                                         |
| **Standard error format** | Every error returns the body below, with the specific `code` documented per endpoint                                                                                                            |

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human-readable error description"
  }
}
```

> **Change Note (2026-07-26):** revised to align with docs 02.1/02.2/02.4, which superseded the original `02-requirements.md` this contract was first written against. Three changes:
>
> 1. **`GET /artworks/{artwork_id}/insight-card`** (Section 4) now returns the historical-context and comparative-analysis blocks **independently**, each with its own `sources` array (RF-010), instead of a single all-or-nothing payload that also used to include Alt Text.
> 2. **Alt Text now has its own dedicated endpoint** (Section 5), per RF-013 — it is no longer bundled into the Insight Card response.
> 3. **`POST /auth/login`** (Section 5) no longer accepts a `google_token` option — RF-026 establishes email/password as the sole authentication mechanism. This closes the inconsistency doc 02.4's own closing note had already flagged against the previous version of this document.
>
> Requirement IDs throughout this document have also been remapped from the original flat `02-requirements.md` numbering to the current split numbering (docs 02.1–02.5) — the numbers no longer align 1:1 with the previous revision.
>
> **Change Note (2026-07-26, v2.1):** the single `GET /artworks/{artwork_id}/insight-card` endpoint is replaced by **two independent endpoints**, one per Insight Card block: `GET /artworks/{artwork_id}/historical-context` and `GET /artworks/{artwork_id}/comparative-analysis`. This clarifies that the front-end fires **three fully independent requests** on artwork visit — one per block, including Alt Text — never a single request that bundles two blocks together (RF-001, RF-013). The historical-context and comparative-analysis blocks are still presented as one combined Insight Card region in the UI (RF-005, RF-006, RF-007), but that aggregation is now performed by the **front-end**, once both of its independent responses have settled — see doc 06 (§5) and doc 08 (§6).

---

## 2. Naming Alignment with Previous Documents

Docs 04 (§7) and 06 (§2/§3) use `{artwork_id}` as the placeholder for the artwork identifier, matching the column name in doc 05. This document formalizes `{artwork_id}` as the definitive name of the route parameter.

---

## 3. Endpoints — Harvard Proxy (Inherited from the MVP)

### `GET /proxy/{path}`

Forwards the request to the Harvard Art Museums API, preserving the contract currently consumed by the front-end (`proxy/object/{id}`, `proxy/object/{id}/people`, `proxy/person/`, etc. — see doc 04, §4). It introduces no changes in this expansion; documented here only to keep the complete API contract in a single place.

- **Authentication:** not required
- **Query params:** forwarded in full to the Harvard API, with the API key attached by the backend (never by the front-end — RNF-005)
- **Response:** forwards the Harvard API's JSON body, with the `info.next` and `info.prev` fields removed (behavior inherited from `proxy/proxy.py`)

| Status                  | When it occurs                                           |
| ----------------------- | -------------------------------------------------------- |
| 200                     | Request forwarded successfully                           |
| 502 `HARVARD_API_ERROR` | The Harvard API returned an error or a non-JSON response |

---

## 4. Endpoints — Insight Card and Alt Text (Persistence on Demand)

All three AI-generated blocks — historical context, comparative analysis, and Alt Text — are each served by their **own independent endpoint**, listed below. The front-end fires all three requests in parallel on artwork visit; the front-end combines the historical-context and comparative-analysis responses into a single Insight Card loading/displayed/error state on the client side (RF-001, RF-005, RF-006, RF-007) — see doc 06 (§5) for the exact aggregation rule and doc 08 (§6) for the resulting UI states. Alt Text is not part of that aggregation (RF-013) — see its own sub-section below. None of the three endpoints knows about, or waits on, either of the other two.

### `GET /artworks/{artwork_id}/historical-context`

Implements the per-block verification and generation logic specified in doc 06 (§2). The front-end displays a loading state (RF-006) immediately upon firing the request and waits for the response (up to the 60s window defined by RNF-002). Internally, the backend triggers `generate_historical_context()` (doc 09) only if the block is not yet persisted — there is no second polling endpoint or WebSocket.

- **Authentication:** not required (RF-001 is accessible to any visitor)
- **Path params:** `artwork_id` (integer) — the artwork's ID in the Harvard Art Museums API

**Success response — 200 OK**

```json
{
  "artwork_id": 123456,
  "historical_context": "string — empty if not available (RF-002, scenario 3)",
  "historical_context_sources": ["string — URL", "..."]
}
```

`historical_context` may be empty, with `historical_context_sources` empty in that case (RF-005, RF-010) — for insufficient information (RF-002, scenario 3), no appropriate source (RF-010, scenario 10.2), or a non-timeout technical failure (provider error, malformed response), all of which are treated identically at this endpoint: a `200` with empty content, never a `5xx`. This is a deliberate departure from the previous version of this contract, which used a `502 GENERATION_FAILED` for any generation failure: under RF-007, a non-timeout failure is never surfaced as an HTTP error, only as the block's absence.

> **Note (RF-004, scenario 2):** if generation succeeds but persistence to the database fails, this endpoint still returns the generated content as part of a `200` — the persistence failure is logged on the backend and never exposed to the client (doc 06, §2).

**Error responses**

| Status | Code                 | When it occurs                                                                                              | Reference                                       |
| ------ | -------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| 404    | `ARTWORK_NOT_FOUND`  | The `artwork_id` does not exist in the Harvard Art Museums API (verified before triggering the AI Pipeline) | Edge case not covered by doc 06 — see Section 9 |
| 504    | `GENERATION_TIMEOUT` | This specific call did not return within the 60-second window defined by RNF-002                            | RNF-002                                         |

A `504` from this endpoint does not, by itself, mean the Insight Card shows an error — RF-007's timeout-specific message only appears once the front-end observes that **both** this endpoint and `GET /artworks/{artwork_id}/comparative-analysis` resolved without content (doc 06, §5).

---

### `GET /artworks/{artwork_id}/comparative-analysis`

Mirrors `GET /artworks/{artwork_id}/historical-context` above in every respect, calling `generate_comparative_analysis()` (doc 09) instead.

- **Authentication:** not required
- **Path params:** `artwork_id` (integer)

**Success response — 200 OK**

```json
{
  "artwork_id": 123456,
  "comparative_analysis": "string — empty if not available (RF-003, scenario 3.2)",
  "comparative_analysis_sources": ["string — URL", "..."]
}
```

**Error responses**

| Status | Code                 | When it occurs                                                                   | Reference                                       |
| ------ | -------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------- |
| 404    | `ARTWORK_NOT_FOUND`  | The `artwork_id` does not exist in the Harvard Art Museums API                   | Edge case not covered by doc 06 — see Section 9 |
| 504    | `GENERATION_TIMEOUT` | This specific call did not return within the 60-second window defined by RNF-002 | RNF-002                                         |

---

### `GET /artworks/{artwork_id}/alt-text`

Implements the independent Alt Text flow specified in doc 06 (§4). Triggered by the front-end when it renders the artwork's image and no Alt Text is yet applied to the `alt` attribute (RF-012) — entirely decoupled from the two Insight Card requests above (RF-013): all three can be in flight at the same time, and none waits for another.

- **Authentication:** not required
- **Path params:** `artwork_id` (integer)

**Success response — 200 OK** (always returned once the underlying artwork exists — see error table)

```json
{
  "artwork_id": 123456,
  "alt_text": "string — never empty; either the AI-generated description prefixed with the standard disclosure sentence, or the standard fallback message"
}
```

Per RF-011 (scenario 3) and RF-012, a generation failure of any kind (timeout, provider error, malformed response, inaccessible image) is represented as **content**, not as an HTTP error: the response is still `200`, with `alt_text` set to the standard fallback message _"Was not possible to generate an alt text for this image."_ This value is not persisted (doc 06, §3) — the next visit retries generation.

**Error responses**

| Status | Code                | When it occurs                                                 |
| ------ | ------------------- | -------------------------------------------------------------- |
| 404    | `ARTWORK_NOT_FOUND` | The `artwork_id` does not exist in the Harvard Art Museums API |

---

## 5. Endpoints — Authentication

These implement, from scratch, on top of PostgreSQL (doc 05), the authentication features required by doc 02.4 — login, logout, password recovery, and session persistence, using **email and password as the sole mechanism** (RF-026). No third-party identity provider (e.g., Google OAuth) is involved at any step.

### `POST /auth/register`

- **Authentication:** not required

```json
// Request
{
  "email": "user@example.com",
  "password": "plain-text-password",
  "name": "User Name"
}
```

```json
// Response — 201 Created
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name"
}
```

| Status | Code                   | When it occurs                                                                                      | Requirement |
| ------ | ---------------------- | --------------------------------------------------------------------------------------------------- | ----------- |
| 409    | `EMAIL_ALREADY_EXISTS` | A user with this email already exists (RF-027, scenario 2) — the existing account is left unchanged | RF-027      |
| 400    | `VALIDATION_ERROR`     | Missing fields or password outside the minimum policy                                               | RF-027      |

---

### `POST /auth/login`

Accepts **only** email and password — no alternate login option.

```json
// Request
{ "email": "user@example.com", "password": "plain-text-password" }
```

```json
// Response — 200 OK
{
  "user": { "id": "uuid", "email": "user@example.com", "name": "User Name" },
  "expires_at": "2026-07-27T14:32:00Z"
}
```

The response also sets the `httpOnly` session cookie (`Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Lax`), consumed by `src/middleware.ts`. The response body does not repeat the token — it only exists in the cookie.

| Status | Code                  | When it occurs                                                                                                              | Requirement |
| ------ | --------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------- |
| 401    | `INVALID_CREDENTIALS` | The email does not match any account, or the password is incorrect — the message never indicates which (RF-026, scenario 2) | RF-026      |
| 400    | `VALIDATION_ERROR`    | Request body is missing `email` or `password`                                                                               | RF-026      |

---

### `POST /auth/logout`

- **Authentication:** requires a valid session (cookie)
- **Request:** no body — the session is identified by the cookie
- **Effect:** sets `sessions.revoked_at = now()` for the current session (doc 05, §5.2); the revoked session can no longer be used to authenticate subsequent requests (RF-028)

| Status             | When it occurs                               |
| ------------------ | -------------------------------------------- |
| 204 No Content     | Logout completed successfully                |
| 401 `UNAUTHORIZED` | No valid session associated with the request |

---

### `POST /auth/password-reset/request`

```json
// Request
{ "email": "user@example.com" }
```

```json
// Response — 200 OK (always, regardless of whether the email exists)
{ "message": "If the provided email exists, a reset link has been sent." }
```

The response is always `200` even if the email does not exist, so as not to expose which emails are registered (RF-029). On success, a row is created in `password_reset_tokens` (doc 05, §4) with a fresh, hashed, expiring token.

---

### `POST /auth/password-reset/confirm`

```json
// Request
{ "token": "token-received-by-email", "new_password": "new-password" }
```

```json
// Response — 200 OK
{ "message": "Password changed successfully." }
```

| Status | Code                       | When it occurs                                                                                                   | Requirement |
| ------ | -------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------- |
| 400    | `INVALID_OR_EXPIRED_TOKEN` | Token is nonexistent, already used (`used_at` set), or past `expires_at` in `password_reset_tokens` (doc 05, §4) | RF-030      |

---

### `GET /auth/session`

- **Authentication:** requires a valid session (cookie)
- Used by `useUserSession` (front-end) to validate the current session across reloads and browser restarts (RF-031)

```json
// Response — 200 OK
{
  "user": { "id": "uuid", "email": "user@example.com", "name": "User Name" },
  "expires_at": "2026-07-27T14:32:00Z"
}
```

| Status | Code           | When it occurs                       |
| ------ | -------------- | ------------------------------------ |
| 401    | `UNAUTHORIZED` | Session missing, expired, or revoked |

---

## 6. Error Catalog

| Code                       | HTTP Status | Endpoints where it appears                                                                                                                |
| -------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `HARVARD_API_ERROR`        | 502         | `GET /proxy/{path}`                                                                                                                       |
| `ARTWORK_NOT_FOUND`        | 404         | `GET /artworks/{artwork_id}/historical-context`, `GET /artworks/{artwork_id}/comparative-analysis`, `GET /artworks/{artwork_id}/alt-text` |
| `GENERATION_TIMEOUT`       | 504         | `GET /artworks/{artwork_id}/historical-context`, `GET /artworks/{artwork_id}/comparative-analysis`                                        |
| `EMAIL_ALREADY_EXISTS`     | 409         | `POST /auth/register`                                                                                                                     |
| `VALIDATION_ERROR`         | 400         | `POST /auth/register`, `POST /auth/login`                                                                                                 |
| `INVALID_CREDENTIALS`      | 401         | `POST /auth/login`                                                                                                                        |
| `INVALID_OR_EXPIRED_TOKEN` | 400         | `POST /auth/password-reset/confirm`                                                                                                       |

---

## 7. Endpoints Traceability at a Glance

| Endpoint                                          | Independence guarantee                                                                               |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `GET /artworks/{artwork_id}/historical-context`   | Checked/generated independently of the other two blocks (RF-001) — its own request, its own response |
| `GET /artworks/{artwork_id}/comparative-analysis` | Checked/generated independently of the other two blocks (RF-001) — its own request, its own response |
| `GET /artworks/{artwork_id}/alt-text`             | Fully decoupled from the two endpoints above (RF-013) — separate request, separate timing            |

The three endpoints above are fired by the front-end in parallel, as three independent requests, on every artwork visit (doc 04, §7.1). The front-end alone recombines the historical-context and comparative-analysis responses into the single Insight Card UI state (doc 06, §5; doc 08, §6); the backend does not aggregate them.

---

## 8. Identified Pending Issues

1. **Artwork nonexistent in the Harvard API:** neither doc 06 flow explicitly models an `artwork_id` that does not exist in the Harvard Art Museums API — this document adds this case as `404 ARTWORK_NOT_FOUND` on all three per-block endpoints, verified before triggering any AI Pipeline call. Still not formalized as a node in doc 06's flowcharts — recommend adding it there before implementation.

I recommend resolving items 1 and 3 before moving forward with implementation (doc 99, Phase 2 and Phase 8).

---

## 9. Traceability

| Endpoint                                          | Related Requirements                                                     | Related Use Cases   |
| ------------------------------------------------- | ------------------------------------------------------------------------ | ------------------- |
| `GET /proxy/{path}`                               | — (inherited from the MVP)                                               | —                   |
| `GET /artworks/{artwork_id}/historical-context`   | RF-001, RF-002, RF-004, RF-005, RF-007, RF-009, RF-010, RNF-001, RNF-002 | UC-01, UC-02, UC-03 |
| `GET /artworks/{artwork_id}/comparative-analysis` | RF-001, RF-003, RF-004, RF-005, RF-007, RF-009, RF-010, RNF-001, RNF-002 | UC-01, UC-02, UC-03 |
| `GET /artworks/{artwork_id}/alt-text`             | RF-011, RF-012, RF-013, RNF-001, RNF-002                                 | UC-01, UC-02        |
| `POST /auth/register`                             | RF-027                                                                   | UC-06               |
| `POST /auth/login`                                | RF-026                                                                   | UC-06               |
| `POST /auth/logout`                               | RF-028                                                                   | UC-06               |
| `POST /auth/password-reset/request`               | RF-029                                                                   | UC-06               |
| `POST /auth/password-reset/confirm`               | RF-030                                                                   | UC-06               |
| `GET /auth/session`                               | RF-031                                                                   | UC-06               |

> The complete matrix, connecting requirements to architecture components and test cases, will be formalized in document 16 — Traceability Matrix.
