# Interface Specification — API Contract — Art Archive AI

**Version:** 2.4
**Date:** 2026-10-30
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
>
> **Change Note (2026-10-27, v2.2):** two gaps surfaced while implementing doc 99 Phase 3 were resolved by author decision. (1) The per-block endpoints now return `502 HARVARD_API_ERROR` when Harvard fails while the artwork's existence is being checked — previously unspecified. (2) Framework-level errors (invalid parameters, unknown routes, wrong methods, unhandled exceptions) now use the standard envelope, adding `NOT_FOUND`, `METHOD_NOT_ALLOWED`, and `INTERNAL_ERROR` to the catalog and extending `VALIDATION_ERROR` beyond the auth endpoints (Section 6.1). Section 8's only pending issue is closed. Section 4 also records that Harvard signals a nonexistent artwork with HTTP `200` and an error body, not a `404`.
>
> **Change Note (2026-10-27, v2.3):** by author decision, a database that cannot be read on the per-block endpoints is handled as a missing block — the endpoint generates and returns a normal `200`, persisting nothing — instead of failing with `500 INTERNAL_ERROR` (Section 4; doc 06, §11).
>
> **Change Note (2026-10-30, v2.4) — the image comes from the browser.** Once deployed (doc 04, §8.2), the backend can no longer download artwork images: Harvard's image server answers its requests with `403` and an HTML page (observed on Render, 2026-10-30), as it does for Azure OpenAI (doc 09, §4) and Vercel's image optimizer. Browsers still load the same images. By author decision, each Insight Card block is now served by **two** endpoints instead of one: `GET` only **reads** the block — returning `null` when it is not persisted yet, and never contacting Harvard or Azure OpenAI — and a new `POST` **generates** it from the artwork's image, which the front-end downloads and sends in the request body (Section 4). Three decisions of the author, same date: (1) this read/generate split, so a persisted block is still served within RNF-001's 500ms without the browser fetching or sending any image; (2) the image is trusted after basic validation — an accepted risk, recorded in Section 4; (3) downloading the image from Harvard's image service is not a call to the Harvard API under doc 00 (§2, rule 3), which concerns the keyed data API (doc 04, §9, Decision 8). Sections 6, 7 and 9 are updated to match, and Section 8 records that the deferred Alt Text endpoint still assumes the old server-side download.

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

All three AI-generated blocks — historical context, comparative analysis, and Alt Text — are each served by their **own independent endpoints**, listed below. Since v2.4, each Insight Card block has a `GET` that reads it and a `POST` that generates it; the front-end sends the `POST` only when the `GET` returned `null` (doc 06, §5). The front-end fires the requests for the blocks in parallel on artwork visit; the front-end combines the historical-context and comparative-analysis responses into a single Insight Card loading/displayed/error state on the client side (RF-001, RF-005, RF-006, RF-007) — see doc 06 (§5) for the exact aggregation rule and doc 08 (§6) for the resulting UI states. Alt Text is not part of that aggregation (RF-013) — see its own sub-section below. None of the three endpoints knows about, or waits on, either of the other two.

### `GET /artworks/{artwork_id}/historical-context`

**Reads** the block — the "check" half of doc 06 (§2). Returns the persisted block, or `null` when it is not persisted yet, which tells the front-end to send the artwork's image to the `POST` below. This endpoint never contacts Harvard or Azure OpenAI, so it always answers within RNF-001's 500ms budget.

- **Authentication:** not required (RF-001 is accessible to any visitor)
- **Path params:** `artwork_id` (integer) — the artwork's ID in the Harvard Art Museums API

**Success response — 200 OK**

```json
{
  "artwork_id": 123456,
  "historical_context": "string, or null when the block is not persisted yet",
  "historical_context_sources": ["string — URL", "..."]
}
```

`historical_context` is `null`, with `historical_context_sources` empty, when no active row holds the block — including when the database cannot be read (doc 06, §2). A persisted block is never empty: an empty result is never persisted (doc 06, §2). The artwork's existence is not checked here: a nonexistent artwork reads as `null`, and the `POST` answers `404`.

**Error responses**

| Status | Code               | When it occurs                 | Reference                          |
| ------ | ------------------ | ------------------------------ | ---------------------------------- |
| 400    | `VALIDATION_ERROR` | `artwork_id` is not an integer | Section 6 (framework-level errors) |

---

### `POST /artworks/{artwork_id}/historical-context`

**Generates** the block from the artwork's image, sent by the front-end — the generation half of doc 06 (§2), reached only after the `GET` above returned `null`. The backend reads the database again first: if a concurrent visitor persisted the block in the meantime, that block is returned and the image is ignored. Otherwise it confirms the artwork exists in Harvard, takes the metadata from there, and triggers `generate_historical_context()` (doc 09) with the received image, persisting a non-empty result. The front-end shows the loading state (RF-006) throughout and waits for the response (up to the 60s window defined by RNF-002) — there is no polling endpoint or WebSocket.

- **Authentication:** not required (RF-001 is accessible to any visitor)
- **Path params:** `artwork_id` (integer) — the artwork's ID in the Harvard Art Museums API

**Request body**

```json
{ "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..." }
```

- `image` — the artwork's primary image as a `data:` URL with base64 content: the image the browser downloaded from the artwork's `primaryimageurl`, resized by Harvard's image service to at most 768px on its longest side (doc 06, §5). JPEG, PNG or WebP, at most **1.5 MB** once decoded. The declared type must match the image's own signature bytes.

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
>
> **Note (database unreadable, 2026-10-27):** if the database cannot be read for the initial check, the endpoint behaves as on a first visit — it generates and returns the block as a normal `200`, and persists nothing (doc 06, §2 and §11). A database outage never surfaces as an error from this endpoint.

**Error responses**

| Status | Code                 | When it occurs                                                                                                                       | Reference                          |
| ------ | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| 400    | `VALIDATION_ERROR`   | `artwork_id` is not an integer; the body is missing or malformed; `image` is not a base64 `data:` URL, is not JPEG/PNG/WebP, does not match its declared type, or exceeds 1.5 MB | Section 6 (framework-level errors) |
| 404    | `ARTWORK_NOT_FOUND`  | The `artwork_id` does not exist in the Harvard Art Museums API (verified before triggering the AI Pipeline)                          | doc 06 §2                          |
| 502    | `HARVARD_API_ERROR`  | The block is not persisted, and the Harvard Art Museums API fails while the artwork's existence is being checked (unreachable, timeout, error status, unexpected body) | doc 06 §2                          |
| 504    | `GENERATION_TIMEOUT` | This specific call did not return within the 60-second window defined by RNF-002                                                    | RNF-002                            |

Both `404` and `502` can only occur when the block is **not** yet persisted: an already-persisted block is served straight from the database, without consulting Harvard at all (doc 06 §7, RNF-001).

**Detecting a nonexistent artwork.** The Harvard Art Museums API does not answer a nonexistent object with a `404`: it returns HTTP `200` with the body `{"error": "Not found"}` (observed 2026-10-27, including for non-numeric and negative IDs). Absence is therefore read from the response body; a `404` status is treated the same way, in case that behaviour changes.

A `504` from this endpoint does not, by itself, mean the Insight Card shows an error — RF-007's timeout-specific message only appears once the front-end observes that **both** Insight Card blocks resolved without content (doc 06, §5).

**Trust in the received image — accepted risk (author decision, 2026-10-30).** The backend cannot check that the image belongs to the artwork: it cannot download the artwork's image itself (Change Note v2.4). A client could send another image and, as the first writer (doc 06, §6), persist a block that does not describe the artwork, served to every later visitor. Accepted for this cycle, with these limits:

- the metadata in the prompt (title, artists, date, culture…) always comes from Harvard, fetched by the backend — only the image is client-supplied;
- the image is validated as described above (type, signature, size);
- a wrong block is retired by setting `expired_at` on its row (doc 05, §8): the next visit reads it as missing and generates it again;
- per-client rate limiting, which also bounds the Azure OpenAI cost a single client can cause, is a doc 99 Phase 8 candidate.

---

### `GET /artworks/{artwork_id}/comparative-analysis`

Mirrors `GET /artworks/{artwork_id}/historical-context` above in every respect: reads the block, returning `comparative_analysis: null` when it is not persisted yet.

```json
{
  "artwork_id": 123456,
  "comparative_analysis": "string, or null when the block is not persisted yet",
  "comparative_analysis_sources": ["string — URL", "..."]
}
```

| Status | Code               | When it occurs                 | Reference                          |
| ------ | ------------------ | ------------------------------ | ---------------------------------- |
| 400    | `VALIDATION_ERROR` | `artwork_id` is not an integer | Section 6 (framework-level errors) |

---

### `POST /artworks/{artwork_id}/comparative-analysis`

Mirrors `POST /artworks/{artwork_id}/historical-context` above in every respect — same request body, same validation, same accepted risk — calling `generate_comparative_analysis()` (doc 09) instead.

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

| Status | Code                 | When it occurs                                                                                          | Reference                          |
| ------ | -------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| 400    | `VALIDATION_ERROR`   | `artwork_id` is not an integer, or the body or `image` is invalid (as for the historical-context `POST`) | Section 6 (framework-level errors) |
| 404    | `ARTWORK_NOT_FOUND`  | The `artwork_id` does not exist in the Harvard Art Museums API                                          | doc 06 §3                          |
| 502    | `HARVARD_API_ERROR`  | The block is not persisted, and the Harvard Art Museums API fails while the artwork's existence is being checked | doc 06 §3                          |
| 504    | `GENERATION_TIMEOUT` | This specific call did not return within the 60-second window defined by RNF-002                        | RNF-002                            |

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

| Code                       | HTTP Status | Endpoints where it appears                                                                                                                         |
| -------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HARVARD_API_ERROR`        | 502         | `GET /proxy/{path}`, `POST /artworks/{artwork_id}/historical-context`, `POST /artworks/{artwork_id}/comparative-analysis`                          |
| `ARTWORK_NOT_FOUND`        | 404         | `POST /artworks/{artwork_id}/historical-context`, `POST /artworks/{artwork_id}/comparative-analysis`, `GET /artworks/{artwork_id}/alt-text`        |
| `GENERATION_TIMEOUT`       | 504         | `POST /artworks/{artwork_id}/historical-context`, `POST /artworks/{artwork_id}/comparative-analysis`                                               |
| `EMAIL_ALREADY_EXISTS`     | 409         | `POST /auth/register`                                                                                                                              |
| `VALIDATION_ERROR`         | 400         | `POST /auth/register`, `POST /auth/login`, the Insight Card `POST` endpoints when the body or its `image` is invalid (Section 4), and any endpoint whose path or query parameters fail validation (e.g. a non-integer `artwork_id`) |
| `INVALID_CREDENTIALS`      | 401         | `POST /auth/login`                                                                                                                                 |
| `INVALID_OR_EXPIRED_TOKEN` | 400         | `POST /auth/password-reset/confirm`                                                                                                                |
| `NOT_FOUND`                | 404         | Any route that does not exist                                                                                                                      |
| `METHOD_NOT_ALLOWED`       | 405         | Any existing route called with a method it does not accept                                                                                         |
| `INTERNAL_ERROR`           | 500         | Any endpoint, on an unexpected failure. The message is generic; details go to the backend log only                                                 |

### 6.1 Framework-level errors (decided 2026-10-27)

Section 1 requires **every** error to use the standard envelope. Errors raised by the web framework itself, rather than by an endpoint, would otherwise escape it: FastAPI answers an invalid path parameter with `422` and a body of its own, and an unknown route with `{"detail": "Not Found"}`. By author decision, they are mapped onto the envelope as follows:

- **Invalid input** (a path or query parameter of the wrong type) → `400 VALIDATION_ERROR`, reusing the existing catalog code rather than introducing `422`. The rejected value is not echoed back in the message.
- **Other framework HTTP errors** → the HTTP status unchanged, with the reason phrase as the code: `NOT_FOUND`, `METHOD_NOT_ALLOWED`.
- **Unhandled exceptions** → `500 INTERNAL_ERROR`, with a generic message; the exception is logged on the backend and never exposed to the client. A failure to *read* the database on the per-block endpoints is not one of these: it is handled as a missing block (Section 4).

The same decision extends `HARVARD_API_ERROR` to the per-block endpoints (Section 4), where Harvard is consulted to confirm the artwork exists.

---

## 7. Endpoints Traceability at a Glance

| Endpoint                                          | Independence guarantee                                                                               |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `GET /artworks/{artwork_id}/historical-context`   | Read independently of the other two blocks (RF-001) — its own request, its own response |
| `POST /artworks/{artwork_id}/historical-context`  | Generated independently of the other two blocks (RF-001); sent only after its own `GET` returned `null` |
| `GET /artworks/{artwork_id}/comparative-analysis` | Read independently of the other two blocks (RF-001) — its own request, its own response |
| `POST /artworks/{artwork_id}/comparative-analysis` | Generated independently of the other two blocks (RF-001); sent only after its own `GET` returned `null` |
| `GET /artworks/{artwork_id}/alt-text`             | Fully decoupled from the endpoints above (RF-013) — separate request, separate timing            |

The blocks' requests are fired by the front-end in parallel, as independent requests, on every artwork visit (doc 04, §7.1). The two Insight Card `POST`s share the one image the front-end downloads, but neither request waits on the other (doc 06, §5). The front-end alone recombines the historical-context and comparative-analysis responses into the single Insight Card UI state (doc 06, §5; doc 08, §6); the backend does not aggregate them.

---

## 8. Identified Pending Issues

1. **Alt Text still assumes a server-side image download (recorded 2026-10-30).** `GET /artworks/{artwork_id}/alt-text` (Section 4) and its flow (doc 06, §4) were specified before v2.4: they generate inside a `GET`, from an image the backend downloads itself — which the deployed backend cannot do (Change Note v2.4). _Why it matters:_ when Alt Text is built (deferred this cycle, doc 99 §2.2), it would fail on every artwork in the deployed environment. _Suggested solution:_ the same read/generate split as the Insight Card blocks, with the image sent by the front-end — to be specified with the rest of Alt Text.

> **Resolved (2026-10-27):** _Artwork nonexistent in the Harvard API_ — this case, specified here as `404 ARTWORK_NOT_FOUND`, was never modeled as a node in doc 06's flowcharts. Doc 06 §2 and §3 now model it, together with the `502 HARVARD_API_ERROR` path for a Harvard failure during the same check (Section 6.1). Implemented in doc 99, Phase 3.

> **Change Note (2026-10-17):** the closing line previously read "resolving items 1 and 3", referring to a three-item list. Items 2 and 3 of that list — the missing `password_reset_tokens` table and the bundling of Alt Text into the Insight Card response — were resolved in doc 05 v2.1 and in this document's own v2.1 revision respectively, and were removed from the list without the closing line being updated. The phase reference, which pointed at a document that did not yet exist, is now resolved against doc 99 v1.0.

---

## 9. Traceability

| Endpoint                                          | Related Requirements                                                     | Related Use Cases   |
| ------------------------------------------------- | ------------------------------------------------------------------------ | ------------------- |
| `GET /proxy/{path}`                               | — (inherited from the MVP)                                               | —                   |
| `GET /artworks/{artwork_id}/historical-context`   | RF-001, RNF-001                                                          | UC-01, UC-02        |
| `POST /artworks/{artwork_id}/historical-context`  | RF-001, RF-002, RF-004, RF-005, RF-007, RF-009, RF-010, RNF-002          | UC-01, UC-03        |
| `GET /artworks/{artwork_id}/comparative-analysis` | RF-001, RNF-001                                                          | UC-01, UC-02        |
| `POST /artworks/{artwork_id}/comparative-analysis` | RF-001, RF-003, RF-004, RF-005, RF-007, RF-009, RF-010, RNF-002         | UC-01, UC-03        |
| `GET /artworks/{artwork_id}/alt-text`             | RF-011, RF-012, RF-013, RNF-001, RNF-002                                 | UC-01, UC-02        |
| `POST /auth/register`                             | RF-027                                                                   | UC-06               |
| `POST /auth/login`                                | RF-026                                                                   | UC-06               |
| `POST /auth/logout`                               | RF-028                                                                   | UC-06               |
| `POST /auth/password-reset/request`               | RF-029                                                                   | UC-06               |
| `POST /auth/password-reset/confirm`               | RF-030                                                                   | UC-06               |
| `GET /auth/session`                               | RF-031                                                                   | UC-06               |

> The complete matrix, connecting requirements to architecture components and test cases, will be formalized in document 16 — Traceability Matrix.
